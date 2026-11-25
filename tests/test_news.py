"""Niveau Avancé : actualités qui agissent sur l'économie de l'année. Découverte n'en a jamais."""
import json

import pytest
from fastapi.testclient import TestClient

from api.main import app
from engine import new_life, step
from engine.data import COUNTRIES, NEWS
from engine.game import news_of_year

NEWS_BY_ID = {n["id"]: n for n in NEWS["news"]}


def life(seed, country, level="avance", years=40):
    s = new_life(seed, country)
    s["level"] = level
    while not s["done"] and s["year"] < years:
        step(s, [], 0 if s["pending"] else None)
    return s


def test_decouverte_has_no_news():
    s = life(3, "FR", level="decouverte")
    assert all(y["news"] is None for y in s["history"])
    assert all(y["shocks"]["stocks_add"] == 0 for y in s["history"])


def test_same_seed_same_news_and_life():
    a, b = life(5, "BR"), life(5, "BR")
    assert json.dumps(a["history"], sort_keys=True) == json.dumps(b["history"], sort_keys=True)


def test_frequency_rumors_and_ranges():
    years = news = rumors = happened = 0
    for country in COUNTRIES:
        for seed in range(15):
            for y in life(seed, country)["history"]:
                years += 1
                n = y["news"]
                if not n:
                    continue
                news += 1
                src = NEWS_BY_ID[n["id"]]
                assert country in src.get("countries", COUNTRIES)
                assert n["ranges"] == src.get("effects_by_country", {}).get(country, src["effects"])
                for k, v in n["effects"].items():
                    lo, hi = n["ranges"][k]
                    assert lo <= v <= hi
                if n["kind"] == "rumeur":
                    rumors += 1
                    happened += n["happens"] or n.get("overridden", False)  # réalisée, même si un krach l'a éclipsée
                else:
                    assert n["happens"] or n.get("overridden")
                if n["happens"]:  # les chocs de l'actualité sont bien appliqués (seuls ou avec ceux d'un événement)
                    for k, v in n["effects"].items():
                        assert y["shocks"][k] == pytest.approx(v, abs=0.06)
    assert news / years == pytest.approx(NEWS["rules"]["news_prob"], abs=0.05)
    assert happened / rumors == pytest.approx(NEWS["rules"]["rumor_prob"], abs=0.08)


def test_news_drawn_without_touching_other_randomness():
    """Le tirage des actualités n'appelle aucun autre flux : l'année historique rejouée est la même qu'en Découverte."""
    a, d = life(8, "CA"), life(8, "CA", level="decouverte")
    assert [y["market_year"] for y in a["history"]] == [y["market_year"] for y in d["history"]]


def test_api_hides_the_future():
    c = TestClient(app)
    for seed in range(30):
        v = c.post("/api/play", json={"seed": seed, "country": "CA", "level": "avance"}).json()
        if v["news"]:
            break
    assert set(v["news"]) == {"id", "kind", "text", "ranges"}  # ni « happens » ni la taille tirée
    assert news_of_year({**new_life(seed, "CA"), "level": "avance"})["text"] == v["news"]["text"]
    v2 = c.post("/api/play", json={"seed": seed, "country": "CA", "level": "avance", "turns": [{"actions": []}]}).json()
    assert v2["last_year"]["news"]["text"] == v["news"]["text"] and "happens" in v2["last_year"]["news"]
    assert c.post("/api/play", json={"seed": seed, "country": "CA"}).json()["news"] is None
    h = v2["history"][-1]
    assert v2["last_year"]["market_return"] == pytest.approx(h["economy"]["stocks_real"] + h["shocks"]["stocks_add"])
