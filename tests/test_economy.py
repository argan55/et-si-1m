"""Morceau 1a : les séries économiques sont exposées sans changer le moteur."""
import pytest
from fastapi.testclient import TestClient

from api.main import app
from test_engine import bot_turns

# Patrimoine final et somme des patrimoines annuels, calculés avec le moteur d'avant l'ajout (commit a715d81).
GOLDEN = {
    "BR-1": (8716057.16, 126346309.37), "BR-2": (170644976.73, 1909115678.96), "BR-3": (420081958.95, 1983429487.71),
    "CA-1": (1214239.85, 28111178.05), "CA-2": (22622154.39, 232652910.98), "CA-3": (33611159.88, 371443553.51),
    "FR-1": (679035.89, 18286164.54), "FR-2": (8580980.97, 106547748.24), "FR-3": (19036966.41, 186778677.11),
    "HK-1": (31700731.35, 311380520.52), "HK-2": (368160462.56, 3361474961.37), "HK-3": (392125721.47, 6104384244.7),
    "MX-1": (25657802.99, 440402252.71), "MX-2": (121520720.28, 1586968672.19), "MX-3": (632234468.05, 4025006992.18),
    "US-1": (410645.93, 17237623.69), "US-2": (7355925.82, 81581224.45), "US-3": (6140695.44, 70923744.68),
}


@pytest.mark.parametrize("key", GOLDEN)
def test_same_seed_same_wealth(key):
    country, seed = key.split("-")
    s, _ = bot_turns(int(seed), country)
    h = [y["net_worth"] for y in s["history"]]
    assert (h[-1], sum(h)) == pytest.approx(GOLDEN[key], abs=0.01)  # valeurs arrondies au centime


@pytest.mark.parametrize("country", ["BR", "CA", "HK"])
def test_breakdown_adds_up(country):
    """1c : la somme des parts (décisions, événement, bourse, immobilier, épargne, reste) = variation du patrimoine."""
    from engine import new_life
    from engine.game import net_worth
    s, _ = bot_turns(4, country)
    prev = net_worth(new_life(4, country))
    for y in s["history"]:
        assert sum(y["breakdown"].values()) == pytest.approx(y["net_worth"] - prev, abs=1e-3)
        assert set(y["breakdown"]) == {"decisions", "event", "stocks", "property", "savings", "rest"}
        prev = y["net_worth"]


def test_economy_in_history_and_api():
    s, turns = bot_turns(1, "BR")
    y = s["history"][0]
    assert set(y["economy"]) == {"stocks_real", "inflation", "cash_real", "fx_real", "home_real"}
    assert set(y["shocks"]) == {"rate_add", "inflation_add", "fx_add", "home_add"}
    assert y["economy"]["stocks_real"] == y["market_return"]
    r = TestClient(app).post("/api/play", json={"seed": 1, "country": "BR", "turns": turns[:5]})
    assert r.status_code == 200
    h = r.json()["history"]
    assert len(h) == 5 and h[0]["economy"] == y["economy"] and h[0]["shocks"] == y["shocks"]
