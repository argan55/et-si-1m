import json
import statistics
from collections import Counter

import numpy as np
import pytest
from fastapi.testclient import TestClient

from api.main import app
from engine import mirror, new_life, replay, step
from engine.data import COUNTRIES, DATA, EVENTS, MARKET
from engine.game import apply_effects, available, flags, usd


def bot_turns(seed, country=None, strategy="random"):
    """Joue une vie entière ; renvoie (état, décisions) pour pouvoir la rejouer."""
    rng = np.random.default_rng(seed + 999)
    s, turns = new_life(seed, country), []
    while not s["done"]:
        t = {"actions": [], "choice": int(rng.integers(2)) if s["pending"] else None}
        free = available(s)
        if strategy == "etf" and s["year"] == 0:
            t["actions"] = [{"type": "invest", "amount": free * 0.99}]
        elif strategy == "random":
            r = rng.random()
            options = [
                {"type": "invest", "amount": free * 0.5},
                {"type": "travel", "kind": "small"},
                {"type": "travel", "kind": "big"},
                {"type": "buy_home", "use": "rental", "size": 1, "down": 0.2},
                {"type": "repay", "target": "debt", "amount": s["debt"]},
                {"type": "study", "years": 1},
                {"type": "start_business", "amount": free * 0.2},
                {"type": "sell_business"},
                {"type": "give", "amount": free * 0.05},
            ]
            if r < 0.4:
                t["actions"] = [options[int(rng.integers(len(options)))]]
        try:
            step(s, t["actions"], t["choice"])
        except ValueError:  # action refusée : on joue l'année sans
            t["actions"] = []
            step(s, [], t["choice"])
        turns.append(t)
    return s, turns


def test_full_game_reaches_mirror():
    for seed in range(60):
        s, _ = bot_turns(seed)
        assert s["done"] and s["age"] == s["death_age"]
        m = mirror(s)
        assert len(m["trajectory"]) == s["death_age"] - s["start_age"]
        assert -1 <= m["vivre_batir"] <= 1 and -1 <= m["securite_aventure"] <= 1
        assert all(np.isfinite(y["net_worth"]) for y in s["history"])


@pytest.mark.parametrize("code", ["CA", "BR", "FR", "HK", "US", "MX"])
def test_every_country_plays_to_the_end(code):
    for seed in range(15):
        s, _ = bot_turns(seed, code)
        assert s["done"] and all(np.isfinite(y["net_worth"]) for y in s["history"])
        assert mirror(s)["years"] == s["death_age"] - s["start_age"]


def test_same_seed_same_life():
    s1, turns = bot_turns(42)
    s2 = replay(42, turns)
    assert json.dumps(s1["history"], sort_keys=True) == json.dumps(s2["history"], sort_keys=True)
    assert new_life(7) == new_life(7)
    assert new_life(7) != new_life(8)


def test_decisions_do_not_shift_future_randomness():
    a, b = new_life(5, "CA"), new_life(5, "CA")
    step(a, [{"type": "travel", "kind": "small"}], None)
    step(b, [], None)
    assert a["history"][0]["market_year"] == b["history"][0]["market_year"]


def test_canada_vs_brazil_differ():
    finals = {
        code: statistics.median(bot_turns(seed, code, "etf")[0]["history"][-1]["net_worth_ppp"] for seed in range(100))
        for code in ("CA", "BR")
    }
    hi, lo = max(finals.values()), min(finals.values())
    assert hi > 1.3 * lo, finals


def test_bricks_interact():
    # études : pas de salaire pendant, salaire plus haut après
    s = new_life(3, "CA")
    s["age"] = 30
    before = s["salary"]
    step(s, [{"type": "study", "years": 1}], s["pending"] and 1)
    assert s["history"][-1]["income"] == 0 and s["salary"] > before * 1.25
    # rembourser sa dette : elle disparaît
    s = new_life(3, "BR")
    s["debt"] = 10000.0
    step(s, [{"type": "repay", "target": "debt", "amount": 10000}], None)
    assert s["debt"] == 0
    # entreprise : revenu = rendement du capital ; rachat à 3 fois la mise
    s = new_life(4, "CA")
    step(s, [{"type": "start_business", "amount": usd(s, 100000)}], None)
    if s["business"]:
        assert flags(s)["business"] and not flags(s)["working"]
        cash = s["cash"]
        apply_effects(s, {"buyout": 3}, {})
        assert s["business"] is None and s["cash"] == pytest.approx(cash + 3 * usd(new_life(4, "CA"), 100000), rel=0.01)
    # don : comptabilisé
    s = new_life(5)
    step(s, [{"type": "give", "amount": 1000}], None)
    assert s["stats"]["given"] >= 1000


def test_refund_never_exceeds_gifts():
    s = new_life(6, "CA")
    step(s, [{"type": "give", "amount": 1}], None)
    yr = {"income_mult": 1, "rent_mult": 1, "inflation_add": 0, "rate_add": 0, "fx_add": 0, "home_add": 0, "market": None}
    cash = s["cash"]
    for _ in range(5):
        apply_effects(s, {"refund_given": 0.3}, yr)
    assert s["cash"] - cash == pytest.approx(1) and not flags(s)["owed"]


def test_business_failure_rate_matches_survival():
    fails, years = 0, 0
    for seed in range(300):
        s = new_life(seed, "BR")
        s["age"] = 30
        step(s, [{"type": "start_business", "amount": usd(s, 60000)}], None)
        for _ in range(5):
            if s["done"] or not s["business"]:
                break
            step(s, [], s["pending"] and 1)
            years += 1
        fails += s["business"] is None
    # survie à 5 ans ≈ 37,9 % au Brésil (les rachats comptent aussi comme sorties)
    assert 0.45 < fails / 300 < 0.8


def test_invalid_actions_rejected():
    s = new_life(1, "CA")
    with pytest.raises(ValueError):
        step(s, [{"type": "invest", "amount": s["cash"] * 10}], None)
    with pytest.raises(ValueError):
        step(new_life(1), [{"type": "travel", "kind": "small"}] * 3, None)
    with pytest.raises(ValueError):
        replay(1, [{"actions": [{"type": "sell_home", "index": 0}]}])
    with pytest.raises(ValueError):
        replay(1, [{"actions": [{"type": "invest", "amount": float("nan")}]}])
    with pytest.raises(ValueError):
        replay(1, [{"actions": [{"type": "give", "amount": -5}]}])
    with pytest.raises(ValueError):
        replay(1, [{"actions": [{"type": "start_business", "amount": 10}]}])
    before = new_life(1, "CA")
    s = new_life(1, "CA")
    with pytest.raises(ValueError):  # atomique : l'état n'a pas bougé
        step(s, [{"type": "give", "amount": 1}, {"type": "invest", "amount": 1e12}], None)
    assert s == before


def test_every_number_has_a_source():
    data = json.loads((DATA / "countries.json").read_text(encoding="utf-8"))
    for c in data["countries"].values():
        for k, v in c.items():
            if not isinstance(v, str):
                assert k in data["sources"], k
    rules = json.loads((DATA / "rules.json").read_text(encoding="utf-8"))
    assert set(rules["rules"]) <= set(rules["sources"])
    assert set(COUNTRIES) == {"CA", "BR", "FR", "HK", "US", "MX"} == set(MARKET)
    assert all(len(rows) >= 20 for rows in MARKET.values())
    families = Counter(e["family"] for e in EVENTS)
    assert len(EVENTS) >= 40 and all(n >= 10 for n in families.values()), families


def test_every_event_effect_is_known():
    s = new_life(9, "CA")
    s["business"] = {"value": 1.0, "invested": 1.0}
    for e in EVENTS:
        for eff in [e.get("effects", {})] + [o["effects"] for o in e.get("choices", [])] + list(e.get("effects_by_country", {}).values()):
            apply_effects(json.loads(json.dumps(s)), eff, {"income_mult": 1, "rent_mult": 1, "inflation_add": 0,
                                                           "rate_add": 0, "fx_add": 0, "home_add": 0, "market": None})
        for f in e.get("requires", []) + e.get("excludes", []) + list(e.get("weight_if", {})):
            assert f in flags(s), (e["id"], f)


def test_api_play():
    client = TestClient(app)
    r = client.post("/api/play", json={"seed": 3})
    assert r.status_code == 200 and r.json()["age"] == r.json()["start_age"]
    assert client.post("/api/play", json={"seed": -1}).status_code == 422
    assert client.post("/api/play", json={"seed": 1, "country": "XX"}).status_code == 400
    _, turns = bot_turns(11)
    r = client.post("/api/play", json={"seed": 11, "turns": turns})
    assert r.status_code == 200 and r.json()["mirror"]["years"] == len(turns)
