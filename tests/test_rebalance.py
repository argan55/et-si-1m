"""Niveau Avancé : répartition cible ETF / liquidités et 3 décisions par an. Découverte reste inchangé."""
import pytest
from fastapi.testclient import TestClient

from api.main import app
from engine import replay, step
from engine.data import RULES
from engine.game import available

TARGET = {"type": "rebalance", "etf_share": 0.6}


def share(s):
    total = max(available(s), 0) + s["etf"]
    return s["etf"] / total


def test_target_is_kept_each_year():
    s = replay(11, [{"actions": [TARGET]}], "CA", level="avance")
    for _ in range(8):
        step(s, [], 0 if s["pending"] else None)
        assert s["target"] == 0.6
    # le rééquilibrage a lieu avant le marché de l'année : la part ne dérive que d'une année de marché
    assert share(s) == pytest.approx(0.6, abs=0.15)
    assert any("Rééquilibrage" in line for y in s["history"][1:] for line in y["log"])


def test_rebalance_stop():
    s = replay(11, [{"actions": [TARGET]}, {"actions": [{"type": "rebalance", "etf_share": None}]}], "CA", level="avance")
    assert s["target"] is None


def test_rebalance_refused_in_decouverte():
    with pytest.raises(ValueError):
        replay(11, [{"actions": [TARGET]}], "CA")


def test_action_limit_depends_on_level():
    three = [{"type": "travel", "kind": "small"}] * 3
    with pytest.raises(ValueError):
        replay(11, [{"actions": three}], "CA")
    s = replay(11, [{"actions": three}], "CA", level="avance")
    assert s["stats"]["trips"] == 3
    assert RULES["max_actions_avance"] == 3


@pytest.mark.parametrize("bad", [-0.1, 1.5, float("nan")])
def test_bad_share(bad):
    with pytest.raises(ValueError):
        replay(11, [{"actions": [{"type": "rebalance", "etf_share": bad}]}], "CA", level="avance")


def test_api_level():
    c = TestClient(app)
    r = c.post("/api/play", json={"seed": 11, "country": "CA", "level": "avance", "turns": [{"actions": [TARGET]}]})
    assert r.status_code == 200
    v = r.json()
    assert (v["level"], v["max_actions"], v["target"]) == ("avance", 3, 0.6)
    assert c.post("/api/play", json={"seed": 11, "country": "CA", "turns": [{"actions": [TARGET]}]}).status_code == 400
    assert c.post("/api/play", json={"seed": 11, "level": "expert"}).status_code == 422
