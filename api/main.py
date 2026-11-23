"""API sans état : le client envoie la graine et toutes ses décisions, le serveur rejoue la vie."""
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from engine import mirror, replay
from engine.data import COUNTRIES, EVENT_BY_ID, RULES
from engine.game import PROFILE_LIMITS, available, emergency_fund, net_worth, retired, spending, usd, working

app = FastAPI(title="Et si… ? (1 M$, une vie)")

# Origines autorisées (site statique hébergé ailleurs), séparées par des virgules. Vide en local : le proxy Vite suffit.
_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]
if _origins:
    app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


class Turn(BaseModel):
    actions: list[dict] = Field(default=[], max_length=RULES["max_actions"])
    choice: int | None = None


class Profile(BaseModel):
    """Mode réaliste. Montants en monnaie locale ; mêmes bornes que le moteur (PROFILE_LIMITS)."""
    country: str
    age: int = Field(ge=PROFILE_LIMITS["age"][0], le=PROFILE_LIMITS["age"][1])
    salary: float = Field(ge=PROFILE_LIMITS["salary"][0], le=PROFILE_LIMITS["salary"][1])
    debt: float = Field(ge=PROFILE_LIMITS["debt"][0], le=PROFILE_LIMITS["debt"][1])
    amount: float = Field(ge=PROFILE_LIMITS["amount"][0], le=PROFILE_LIMITS["amount"][1])
    partner: bool = False
    children: int = Field(default=0, ge=PROFILE_LIMITS["children"][0], le=PROFILE_LIMITS["children"][1])


class Play(BaseModel):
    seed: int = Field(ge=0, lt=2**32)
    country: str | None = None
    profile: Profile | None = None
    turns: list[Turn] = Field(default=[], max_length=RULES["max_age"])


def _event(eid):
    if not eid:
        return None
    e = EVENT_BY_ID[eid]
    return {"id": eid, "family": e["family"], "text": e["text"], "choices": [o["label"] for o in e.get("choices", [])]}


def view(s):
    c = COUNTRIES[s["country"]]
    last = s["history"][-1] if s["history"] else None
    return {
        "country": {"code": s["country"], "name": c["name"], "where": c["where"], "currency": c["currency"],
                    "ppp": c["ppp_per_intl_usd"], "fx": c["fx_per_usd"], "life_expectancy": c["life_expectancy"],
                    "home_price": c["home_price"], "buy_costs": c["buy_costs"]},
        # prix du moment, en monnaie locale (ce qui se paie en dollars suit le change)
        "prices": {"trip_small": c["trip_small"], "trip_big": usd(s, RULES["trip_big_usd"]),
                   "study_year": usd(s, RULES["study_tuition_usd"]), "business_min": usd(s, RULES["business_min_usd"]),
                   "study_premium": RULES["study_premium"], "study_max_age": RULES["study_max_age"],
                   "business_yield": RULES["business_yield"]},
        "given": s["stats"]["given"],
        "fx_index": s["fx"],
        "business": s["business"], "studying": s["studying"], "studied": s["studied"], "retired": retired(s),
        "mode": "realiste" if s["profile"] else "jeu",
        "origin": RULES["realistic_label"] if s["profile"] else RULES["origins"][s["origin"]]["label"],
        "prize_usd": RULES["prize_usd"],
        "prize_local": s["profile"]["amount"] if s["profile"] else RULES["prize_usd"] * c["fx_per_usd"],
        "age": s["age"], "start_age": s["start_age"], "done": s["done"],
        "working": working(s), "salary": s["salary"], "lifestyle": s["lifestyle"],
        "partner": s["partner"], "children": s["children"],
        "cash": s["cash"], "etf": s["etf"], "debt": s["debt"], "homes": s["homes"],
        "net_worth": net_worth(s), "net_worth_ppp": net_worth(s) / c["ppp_per_intl_usd"],
        "spending": spending(s), "emergency_fund": emergency_fund(s), "available": available(s),
        "last_year": last and {**{k: last[k] for k in ("age", "inflation", "market_year", "market_return", "income", "spend", "log")},
                               "event": _event(last["event"])},
        "pending": _event(s["pending"]),
        "history": [{"age": y["age"], "net_worth_ppp": y["net_worth_ppp"]} for y in s["history"]],
        "mirror": mirror(s) if s["done"] else None,
    }


@app.get("/api/countries")
def countries():
    """Pour le formulaire du mode réaliste : pays, monnaie et valeurs par défaut."""
    return [
        {"code": k, "name": c["name"], "currency": c["currency"], "salary_median": c["salary_median"],
         "prize_local": RULES["prize_usd"] * c["fx_per_usd"]}
        for k, c in COUNTRIES.items()
    ]


@app.post("/api/play")
def play(p: Play):
    if p.country is not None and p.country not in COUNTRIES:
        raise HTTPException(400, "Pays inconnu.")
    try:
        s = replay(p.seed, [t.model_dump() for t in p.turns], p.country, p.profile.model_dump() if p.profile else None)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return view(s)
