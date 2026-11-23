"""Une vie, année par année.

Tous les montants sont en monnaie locale et en termes réels (prix de l'année de départ).
Déterministe : tout l'aléa vient de (seed, flux, année), donc les décisions du joueur
ne décalent jamais les tirages des années suivantes.
"""
import copy
import math

import numpy as np

from .data import COUNTRIES, EVENT_BY_ID, EVENTS, RETURNS, RULES

_BY_RETURN = sorted(range(len(RETURNS)), key=lambda i: RETURNS[i]["stocks"])
# flux d'aléa indépendants
_LIFE, _EVENT, _INFL, _MARKET, _HOMES = range(5)


def _rng(seed, stream, year=0):
    return np.random.default_rng([seed, stream, year])


def new_life(seed, country=None):
    if country is not None and country not in COUNTRIES:
        raise ValueError(f"Pays inconnu : {country}")
    rng = _rng(seed, _LIFE)
    drawn = str(rng.choice(sorted(COUNTRIES)))  # toujours tiré, pour garder la même suite d'aléa
    code = country or drawn
    c = COUNTRIES[code]
    origin = str(rng.choice(sorted(RULES["origins"])))
    o = RULES["origins"][origin]
    age = int(rng.integers(o["age_min"], o["age_max"] + 1))
    death = round(rng.normal(c["life_expectancy"], RULES["life_sd"]))
    death = int(min(max(death, age + RULES["min_years"]), RULES["max_age"]))
    salary = float(c["salary_median_net"] * math.exp(rng.normal(0, c["salary_sigma"])) * o["salary_mult"])
    partner = bool(rng.random() < c["partner_prob"])
    kids = int(rng.choice(len(c["children_weights"]), p=c["children_weights"]))
    has_debt = rng.random() < c["debt_prob"]
    debt = float(salary * c["debt_to_salary"] * rng.lognormal(0, RULES["debt_sigma"])) if has_debt else 0.0
    return {
        "seed": seed, "country": code, "origin": origin,
        "start_age": age, "age": age, "death_age": death, "year": 0,
        "salary": salary, "lifestyle": salary, "partner": partner, "children": kids if age >= 25 else 0,
        "cash": RULES["prize_usd"] * c["fx_per_usd"], "etf": 0.0, "homes": [],
        "debt": debt, "debt_years": RULES["debt_years"],
        "pending": None, "done": False, "log": [],
        "stats": {"travel_spent": 0.0, "trips": 0, "given": 0.0, "invested": 0.0, "aventure": 0, "abroad": 0},
        "history": [],
    }


def working(s):
    return s["age"] < COUNTRIES[s["country"]]["retirement_age"]


def spending(s):
    c = COUNTRIES[s["country"]]
    eq = (1 + RULES["child_equiv"] * s["children"]) * (RULES["partner_equiv"] if s["partner"] else 1)
    x = c["spend_ratio"] * s["lifestyle"] * eq
    if any(h["use"] == "residence" for h in s["homes"]):
        x *= 1 - c["rent_share"]
    return x


def emergency_fund(s):
    return spending(s) * RULES["emergency_months"] / 12


def available(s):
    return s["cash"] - emergency_fund(s)


def net_worth(s):
    return s["cash"] + s["etf"] + sum(h["value"] - h["mortgage"] for h in s["homes"]) - s["debt"]


def _money(x, c):
    return f"{x:,.0f} {c['currency']}".replace(",", " ")


def _need(s, amount):
    if amount > available(s) + 1e-6:
        raise ValueError("Pas assez de liquidités disponibles (le fonds d'urgence est réservé).")


def _act(s, a, c):
    t = a.get("type")
    if t == "invest":
        amt = float(a["amount"])
        if not math.isfinite(amt) or amt == 0:
            raise ValueError("Montant invalide.")
        if amt > 0:
            _need(s, amt)
            s["stats"]["invested"] += amt
        elif -amt > s["etf"] + 1e-6:
            raise ValueError("Vous ne détenez pas autant de parts d'ETF.")
        s["cash"] -= amt
        s["etf"] += amt
        s["log"].append(f"{'Achat' if amt > 0 else 'Vente'} d'ETF : {_money(abs(amt), c)}")
    elif t == "buy_home":
        use = a["use"]
        if use not in ("residence", "rental"):
            raise ValueError("Usage inconnu.")
        if use == "residence" and any(h["use"] == "residence" for h in s["homes"]):
            raise ValueError("Vous avez déjà une résidence principale.")
        size, down = float(a.get("size", 1)), float(a.get("down", RULES["min_down"]))
        if not (0.5 <= size <= 2) or not (RULES["min_down"] <= down <= 1):
            raise ValueError("Taille ou mise de fonds invalide.")
        price = c["home_price"] * size
        _need(s, price * (down + c["buy_costs"]))
        s["cash"] -= price * (down + c["buy_costs"])
        s["homes"].append({"use": use, "value": price, "mortgage": price * (1 - down), "years_left": c["mortgage_years"]})
        s["stats"]["invested"] += price * down
        s["log"].append(f"Achat d'un bien ({'résidence' if use == 'residence' else 'locatif'}) : {_money(price, c)}")
    elif t == "sell_home":
        h = s["homes"][int(a["index"])]
        s["homes"].remove(h)
        s["cash"] += h["value"] * (1 - c["sell_costs"]) - h["mortgage"]
        s["log"].append(f"Vente d'un bien : {_money(h['value'], c)}")
    elif t == "travel":
        if a["kind"] not in ("small", "big"):
            raise ValueError("Type de voyage inconnu.")
        cost = c["trip_" + a["kind"]]
        _need(s, cost)
        s["cash"] -= cost
        s["stats"]["trips"] += 1
        s["stats"]["travel_spent"] += cost
        s["log"].append(f"Voyage : {_money(cost, c)}")
    else:
        raise ValueError(f"Action inconnue : {t}")


def _eligible(s, e):
    flags = {
        "working": working(s), "retired": not working(s),
        "partner": s["partner"], "no_partner": not s["partner"],
        "home": bool(s["homes"]), "rental": any(h["use"] == "rental" for h in s["homes"]),
        "etf": s["etf"] > 0,
    }
    return all(flags[r] for r in e.get("requires", [])) and e.get("age_min", 0) <= s["age"] <= e.get("age_max", 999)


def _draw_event(s):
    cands = [e for e in EVENTS if _eligible(s, e)]
    w = [
        e["weight"] * e.get("country_weight", {}).get(s["country"], 1)
        * (max(RULES["age_factor_min"], s["age"] / RULES["age_factor_ref"]) if e.get("age_factor") else 1)
        for e in cands
    ] + [RULES["no_event_weight"]]
    i = int(_rng(s["seed"], _EVENT, s["year"]).choice(len(w), p=np.array(w) / sum(w)))
    return cands[i] if i < len(cands) else None


def apply_effects(s, eff, yr):
    ref = s["salary"] if working(s) else s["lifestyle"]
    for k, v in eff.items():
        if k == "salary_mult":
            s["salary"] *= v
        elif k in ("income_mult", "rent_mult"):
            yr[k] *= v
        elif k in ("inflation_add", "rate_add"):
            yr[k] += v
        elif k == "market":
            yr["market"] = v
        elif k == "cash_salary":
            s["cash"] += v * ref
        elif k == "liquid_pct":
            s["cash"] = s["cash"] * (1 + v) if s["cash"] > 0 else s["cash"]
            s["etf"] *= 1 + v
        elif k == "home_pct":
            s["cash"] += v * sum(h["value"] for h in s["homes"])
        elif k == "partner":
            s["partner"] = v
        elif k == "children_add":
            s["children"] += v
        elif k == "give_salary":
            s["cash"] -= v * ref
            s["stats"]["given"] += v * ref
        elif k in ("aventure", "abroad"):
            s["stats"][k] += v
        else:
            raise KeyError(f"effet inconnu : {k}")


def _amortize(balance, rate, years, infl):
    """Une annuité à taux nominal ; renvoie (paiement, solde réel restant)."""
    pay = balance * (1 + rate) if years <= 1 else balance * rate / (1 - (1 + rate) ** -years)
    rest = (balance * (1 + rate) - pay) / (1 + infl)
    return pay, rest if rest > 1 else 0.0


def _cover_shortfall(s, c):
    """Découvert : on vend des ETF, puis des biens (locatif d'abord), puis on s'endette."""
    if s["cash"] >= 0:
        return
    take = min(s["etf"], -s["cash"])
    if take > 0:
        s["etf"] -= take
        s["cash"] += take
        s["log"].append("Des ETF ont été vendus pour couvrir les dépenses.")
    while s["cash"] < 0 and s["homes"]:
        i = next((i for i, h in enumerate(s["homes"]) if h["use"] == "rental"), len(s["homes"]) - 1)
        h = s["homes"].pop(i)
        s["cash"] += h["value"] * (1 - c["sell_costs"]) - h["mortgage"]
        s["log"].append("Un bien a été vendu pour couvrir les dépenses.")
    if s["cash"] < 0:
        s["debt"] -= s["cash"]
        s["debt_years"] = RULES["debt_years"]
        s["cash"] = 0.0
        s["log"].append("Vous avez dû vous endetter.")


def _finances(s, yr, c):
    seed, y = s["seed"], s["year"]
    infl = float(_rng(seed, _INFL, y).normal(c["inflation_mean"], c["inflation_sd"])) + yr["inflation_add"]
    n = RULES["extreme_years"]
    pool = {"worst": _BY_RETURN[:n], "best": _BY_RETURN[-n:]}.get(yr["market"], _BY_RETURN)
    market = RETURNS[pool[int(_rng(seed, _MARKET, y).integers(len(pool)))]]

    income = (s["salary"] if working(s) else c["pension_ratio"] * s["lifestyle"]) * yr["income_mult"]
    spend = spending(s)
    flow = income - spend
    hr = _rng(seed, _HOMES, y)
    for h in s["homes"]:
        flow -= h["value"] * c["home_costs"]
        if h["use"] == "rental":
            flow += h["value"] * c["rent_yield"] * yr["rent_mult"]
        if h["mortgage"] > 0:
            pay, h["mortgage"] = _amortize(h["mortgage"], c["mortgage_rate"] + yr["rate_add"], h["years_left"], infl)
            h["years_left"] = max(1, h["years_left"] - 1)
            flow -= pay
        h["value"] *= 1 + float(hr.normal(c["home_growth_mean"], c["home_growth_sd"]))
    if s["debt"] > 0:
        pay, s["debt"] = _amortize(s["debt"], c["debt_rate"], s["debt_years"], infl)
        s["debt_years"] = max(1, s["debt_years"] - 1)
        flow -= pay

    if s["cash"] > 0:
        s["cash"] *= (1 + c["cash_rate"] + yr["rate_add"]) / (1 + infl)
    s["etf"] *= 1 + market["stocks"]
    s["cash"] += flow
    _cover_shortfall(s, c)
    if working(s):
        s["salary"] *= 1 + c["salary_growth_real"]
        s["lifestyle"] = s["salary"]
    return {"inflation": infl, "market_year": market["year"], "market_return": market["stocks"], "income": income, "spend": spend}


def step(s, actions=(), choice=None):
    """Une année. Atomique : si une décision est refusée, l'état reste inchangé."""
    backup = copy.deepcopy(s)
    try:
        return _step(s, actions, choice)
    except Exception:
        s.clear()
        s.update(backup)
        raise


def _step(s, actions, choice):
    if s["done"]:
        raise ValueError("Cette vie est terminée.")
    c = COUNTRIES[s["country"]]
    yr = {"income_mult": 1.0, "rent_mult": 1.0, "inflation_add": 0.0, "rate_add": 0.0, "market": None}
    s["log"] = []
    if s["pending"]:
        opts = EVENT_BY_ID[s["pending"]]["choices"]
        if choice is None or not 0 <= int(choice) < len(opts):
            raise ValueError("Un choix est attendu pour l'événement en cours.")
        apply_effects(s, opts[int(choice)]["effects"], yr)
        s["log"].append(f"Votre choix : {opts[int(choice)]['label']}")
        s["pending"] = None
    elif choice is not None:
        raise ValueError("Aucun choix n'est attendu.")
    if len(actions) > RULES["max_actions"]:
        raise ValueError(f"Au plus {RULES['max_actions']} décisions par an.")
    for a in actions:
        _act(s, a, c)

    ev = _draw_event(s)
    if ev and "choices" in ev:
        s["pending"] = ev["id"]
    elif ev:
        apply_effects(s, ev.get("effects_by_country", {}).get(s["country"], ev["effects"]), yr)

    fin = _finances(s, yr, c)
    nw = net_worth(s)
    rentals = sum(h["value"] - h["mortgage"] for h in s["homes"] if h["use"] == "rental")
    s["history"].append({
        "age": s["age"], "net_worth": nw, "net_worth_ppp": nw / c["ppp_per_intl_usd"],
        "cash": s["cash"], "etf": s["etf"], "property": sum(h["value"] - h["mortgage"] for h in s["homes"]),
        "debt": s["debt"], "risky": s["etf"] + rentals, "event": ev["id"] if ev else None,
        "log": s["log"], **fin,
    })
    s["age"] += 1
    s["year"] += 1
    if s["age"] >= s["death_age"]:
        s["done"] = True
        s["pending"] = None
    return s


def replay(seed, turns, country=None):
    """Rejoue une vie à partir de sa graine et de la liste de ses décisions."""
    s = new_life(seed, country)
    for t in turns:
        try:
            step(s, t.get("actions", []), t.get("choice"))
        except (KeyError, TypeError, IndexError, AttributeError) as e:
            raise ValueError(f"Décision invalide : {e}") from e
    return s
