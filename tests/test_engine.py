import json
import statistics

import numpy as np
import pytest
from fastapi.testclient import TestClient

from api.main import app
from engine import mirror, new_life, replay, step
from engine.data import COUNTRIES, DATA, EVENTS, RETURNS
from engine.game import available


def bot_turns(seed, country=None, strategy="random"):
    """Joue une vie entière ; renvoie (état, décisions) pour pouvoir la rejouer."""
    rng = np.random.default_rng(seed + 999)
    s, turns = new_life(seed, country), []
    while not s["done"]:
        t = {"actions": [], "choice": int(rng.integers(2)) if s["pending"] else None}
        if strategy == "etf" and s["year"] == 0:
            t["actions"] = [{"type": "invest", "amount": available(s) * 0.99}]
        elif strategy == "random":
            r = rng.random()
            if r < 0.15 and available(s) > 0:
                t["actions"] = [{"type": "invest", "amount": available(s) * 0.5}]
            elif r < 0.2:
                t["actions"] = [{"type": "travel", "kind": "small"}]
            elif r < 0.23:
                t["actions"] = [{"type": "buy_home", "use": "rental", "size": 1, "down": 0.2}]
        try:
            step(s, t["actions"], t["choice"])
        except ValueError:  # action refusée (pas assez de liquidités) : on joue l'année sans
            t["actions"] = []
            step(s, [], t["choice"])
        turns.append(t)
    return s, turns


def test_full_game_reaches_mirror():
    for seed in range(30):
        s, _ = bot_turns(seed)
        assert s["done"] and s["age"] == s["death_age"]
        m = mirror(s)
        assert len(m["trajectory"]) == s["death_age"] - s["start_age"]
        assert -1 <= m["vivre_batir"] <= 1 and -1 <= m["securite_aventure"] <= 1
        assert all(np.isfinite(y["net_worth"]) for y in s["history"])


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


def test_every_number_has_a_source():
    data = json.loads((DATA / "countries.json").read_text(encoding="utf-8"))
    for c in data["countries"].values():
        for k, v in c.items():
            if not isinstance(v, str):
                assert k in data["sources"], k
    rules = json.loads((DATA / "rules.json").read_text(encoding="utf-8"))
    assert set(rules["rules"]) <= set(rules["sources"])
    assert len(RETURNS) > 90 and len(EVENTS) >= 15
    assert set(COUNTRIES) == {"CA", "BR"}


def test_api_play():
    client = TestClient(app)
    r = client.post("/api/play", json={"seed": 3, "turns": [{"actions": []}] * 3})
    assert r.status_code in (200, 400)  # 400 si un choix d'événement était attendu
    r = client.post("/api/play", json={"seed": 3})
    assert r.status_code == 200 and r.json()["age"] == r.json()["start_age"]
    assert client.post("/api/play", json={"seed": -1}).status_code == 422
    assert client.post("/api/play", json={"seed": 1, "country": "XX"}).status_code == 400
    _, turns = bot_turns(11)
    r = client.post("/api/play", json={"seed": 11, "turns": turns})
    assert r.status_code == 200 and r.json()["mirror"]["years"] == len(turns)
