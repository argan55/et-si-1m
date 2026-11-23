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

# Historique annuel par pays : une année tirée rejoue ensemble bourse, inflation, taux, change et immobilier.
MARKET = {}
with open(DATA / "market_history.csv", newline="") as f:
    for r in csv.DictReader(f):
        MARKET.setdefault(r["country"], []).append(
            {k: (int(v) if k == "year" else v if k == "country" else float(v)) for k, v in r.items()}
        )
