"""Chargement des données sourcées (data/). Aucune hypothèse chiffrée ne vit dans le code."""
import csv
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def _json(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


COUNTRIES = _json("countries.json")["countries"]
RULES = _json("rules.json")["rules"]
EVENTS = _json("events.json")["events"]
EVENT_BY_ID = {e["id"]: e for e in EVENTS}

with open(DATA / "returns.csv", newline="") as f:
    RETURNS = [{"year": int(r["year"]), "stocks": float(r["stocks_real"])} for r in csv.DictReader(f)]
