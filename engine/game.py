"""Une vie, année par année.

Tous les montants sont en monnaie locale et en termes réels (prix de l'année de départ).
Chaque année de jeu rejoue une année historique du pays : bourse locale, inflation, taux,
change et immobilier ensemble (data/market_history.csv).
Déterministe : tout l'aléa vient de (seed, flux, année), donc les décisions du joueur
ne décalent jamais les tirages des années suivantes.
"""
import copy
import math
from statistics import NormalDist

import numpy as np

from .data import COUNTRIES, EVENT_BY_ID, EVENTS, MARKET, RULES

# flux d'aléa indépendants
_LIFE, _EVENT, _MARKET, _BUSINESS = range(4)
COUNTERS = {"aventure", "abroad", "angel", "cosigned", "autres"}
_FLOORED = {"angel", "cosigned", "abroad"}  # compteurs d'état, jamais négatifs
_BY_RETURN = {code: sorted(rows, key=lambda r: r["stocks_real"]) for code, rows in MARKET.items()}


def _rng(seed, stream, year=0):
    return np.random.default_rng([seed, stream, year])


def salary_sigma(c):
    """Dispersion log-normale des salaires déduite du coefficient de Gini du pays."""
    return math.sqrt(2) * NormalDist().inv_cdf((c["gini"] + 1) / 2)


PROFILE_LIMITS = {"age": (18, 90), "salary": (0, 1e9), "debt": (0, 1e10), "amount": (1, 1e11), "children": (0, 10)}


def _check_profile(p):
    """Mode réaliste : le profil saisi par le joueur (montants en monnaie locale)."""
    if p.get("country") not in COUNTRIES:
        raise ValueError("Pays inconnu.")
    for k, (lo, hi) in PROFILE_LIMITS.items():
        v = float(p[k])
        if not (math.isfinite(v) and lo <= v <= hi):
            raise ValueError(f"Valeur hors limites : {k}.")
    if not isinstance(p.get("partner"), bool):
        raise ValueError("Valeur invalide : partner.")
    return p


def new_life(seed, country=None, profile=None):
    if country is not None and country not in COUNTRIES:
        raise ValueError(f"Pays inconnu : {country}")
    if profile is not None:
        country = _check_profile(profile)["country"]
    rng = _rng(seed, _LIFE)
    drawn = str(rng.choice(sorted(COUNTRIES)))  # toujours tiré, pour garder la même suite d'aléa
    code = country or drawn
    c = COUNTRIES[code]
    origin = str(rng.choice(sorted(RULES["origins"])))
    o = RULES["origins"][origin]
    age = int(rng.integers(o["age_min"], o["age_max"] + 1))
    raw_death = round(rng.normal(c["life_expectancy"], RULES["life_sd"]))
    death = int(min(max(raw_death, age + RULES["min_years"]), RULES["max_age"]))
    salary = float(c["salary_median"] * math.exp(rng.normal(0, salary_sigma(c))) * o["salary_mult"])
    partner = bool(rng.random() < c["partner_prob"])
    span = RULES["children_full_age"] - RULES["children_from_age"]
    kids = int(rng.poisson(c["fertility"] * min(max((age - RULES["children_from_age"]) / span, 0), 1)))
    has_debt = rng.random() < c["debt_prob"]
    debt = float(salary * c["debt_to_salary"] * rng.lognormal(0, RULES["debt_sigma"])) if has_debt else 0.0
    cash = RULES["prize_usd"] * c["fx_per_usd"]
    if profile is not None:
        origin, age = "realiste", int(profile["age"])
        salary, debt, cash = float(profile["salary"]), float(profile["debt"]), float(profile["amount"])
        partner, kids = profile["partner"], int(profile["children"])
        # seul l'âge au décès reste tiré au sort (même tirage qu'en mode jeu, recalé sur l'âge saisi)
        death = int(min(max(raw_death, age + RULES["min_years"]), RULES["max_age"]))
    return {
        "seed": seed, "country": code, "origin": origin, "profile": profile,
        "start_age": age, "age": age, "death_age": death, "year": 0,
        "salary": salary, "lifestyle": salary, "partner": partner, "children": kids,
        "cash": cash, "etf": 0.0, "homes": [],
        "debt": debt, "debt_years": RULES["debt_years"],
        "fx": 1.0,  # indice réel du dollar US en monnaie locale (1 = au départ)
        "spend_mult": 1.0,  # train de vie réduit après une faillite personnelle
        "business": None, "studying": 0, "studied": False,
        "level": "decouverte", "target": None,  # niveau Avancé : part cible en ETF, rééquilibrée chaque année
        "pending": None, "done": False, "log": [],
        "stats": {"travel_spent": 0.0, "experience": 0.0, "trips": 0, "trips_abroad": 0, "given": 0.0, "refunded": 0.0, "gifts": 0,
                  "invested": 0.0, "repaid": 0.0, "bankruptcies": 0, **{k: 0 for k in COUNTERS}},
        "history": [],
    }


def usd(s, amount):
    """Coût local, au change réel du moment, d'une dépense fixée en dollars US."""
    return amount * COUNTRIES[s["country"]]["fx_per_usd"] * s["fx"]


def retired(s):
    return s["age"] >= COUNTRIES[s["country"]]["retirement_age"]


def working(s):
    return not retired(s) and not s["business"] and not s["studying"]


def income(s):
    c = COUNTRIES[s["country"]]
    if s["studying"]:
        return 0.0
    if s["business"]:
        return s["business"]["value"] * RULES["business_yield"]
    return s["salary"] if not retired(s) else c["pension_ratio"] * s["lifestyle"]


def spending(s):
    c = COUNTRIES[s["country"]]
    kids = s["children"] if s["age"] < RULES["children_leave_age"] else 0  # les enfants finissent par partir
    eq = (1 + RULES["child_equiv"] * kids) * (RULES["partner_equiv"] if s["partner"] else 1)
    x = c["spend_ratio"] * s["lifestyle"] * eq * s["spend_mult"]
    if any(h["use"] == "residence" for h in s["homes"]):
        x *= 1 - c["rent_share"]
    return x


def emergency_fund(s):
    return spending(s) * RULES["emergency_months"] / 12


def available(s):
    return s["cash"] - emergency_fund(s)


def net_worth(s):
    return (s["cash"] + s["etf"] + sum(h["value"] - h["mortgage"] for h in s["homes"])
            + (s["business"]["value"] if s["business"] else 0) - s["debt"])


def _money(x, c):
    return f"{x:,.0f} {c['currency']}".replace(",", " ")


def _amount(a):
    amt = float(a["amount"])
    if not math.isfinite(amt) or amt <= 0:
        raise ValueError("Montant invalide.")
    return amt


def _need(s, amount):
    if amount > available(s) + 1e-6:
        raise ValueError("Pas assez de liquidités disponibles (le fonds d'urgence est réservé).")


def _spend(s, amount):
    _need(s, amount)
    s["cash"] -= amount


def _act(s, a, c):
    t = a.get("type")
    st = s["stats"]
    if t == "rebalance":
        if s["level"] != "avance":
            raise ValueError("La répartition automatique est réservée au niveau Avancé.")
        share = a.get("etf_share")
        if share is None:
            s["target"] = None
            s["log"].append("Répartition automatique arrêtée.")
        else:
            share = float(share)
            if not (math.isfinite(share) and 0 <= share <= 1):
                raise ValueError("Part en ETF invalide (entre 0 et 1).")
            s["target"] = share
            s["log"].append(f"Répartition cible : {round(share * 100)} % en ETF, le reste en liquidités.")
    elif t == "invest":
        amt = float(a["amount"])
        if not math.isfinite(amt) or amt == 0:
            raise ValueError("Montant invalide.")
        if amt > 0:
            _need(s, amt)
            st["invested"] += amt
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
        _spend(s, price * (down + c["buy_costs"]))
        s["homes"].append({"use": use, "value": price, "mortgage": price * (1 - down), "years_left": c["mortgage_years"]})
        st["invested"] += price * down
        s["log"].append(f"Achat d'un bien ({'résidence' if use == 'residence' else 'locatif'}) : {_money(price, c)}")
    elif t == "sell_home":
        h = s["homes"][int(a["index"])]
        s["homes"].remove(h)
        s["cash"] += h["value"] * (1 - c["sell_costs"]) - h["mortgage"]
        s["log"].append(f"Vente d'un bien : {_money(h['value'], c)}")
    elif t == "travel":
        if a["kind"] not in ("small", "big"):
            raise ValueError("Type de voyage inconnu.")
        cost = c["trip_small"] if a["kind"] == "small" else usd(s, RULES["trip_big_usd"])
        _spend(s, cost)
        st["trips"] += 1
        st["trips_abroad"] += a["kind"] == "big"
        st["travel_spent"] += cost
        s["log"].append(f"Voyage : {_money(cost, c)}")
    elif t == "repay":
        amt = _amount(a)
        if a["target"] == "debt":
            if amt > s["debt"] + 1e-6:
                raise ValueError("C'est plus que votre dette.")
            s["debt"] -= amt
        else:
            h = s["homes"][int(a["target"])]
            if amt > h["mortgage"] + 1e-6:
                raise ValueError("C'est plus que le solde de l'hypothèque.")
            h["mortgage"] -= amt
        _spend(s, amt)
        st["repaid"] += amt
        s["log"].append(f"Remboursement anticipé : {_money(amt, c)}")
    elif t == "study":
        years = int(a["years"])
        if years not in (1, 2):
            raise ValueError("Durée d'études invalide.")
        if s["studied"] or s["business"] or retired(s) or s["age"] > RULES["study_max_age"]:
            raise ValueError("Les études à l'étranger ne sont plus possibles dans votre situation.")
        cost = usd(s, RULES["study_tuition_usd"]) * years
        _spend(s, cost)
        s["studying"], s["studied"] = years, True
        st["abroad"] += 1
        s["log"].append(f"Départ pour {years} an(s) d'études à l'étranger : {_money(cost, c)}")
    elif t == "start_business":
        amt = _amount(a)
        if s["business"] or s["studying"]:
            raise ValueError("Impossible de lancer une entreprise maintenant.")
        if amt < usd(s, RULES["business_min_usd"]):
            raise ValueError(f"Il faut au moins {_money(usd(s, RULES['business_min_usd']), c)} pour se lancer.")
        _spend(s, amt)
        s["business"] = {"value": amt, "invested": amt, "years": 0}
        st["invested"] += amt
        st["aventure"] += 1
        s["log"].append(f"Création d'entreprise : {_money(amt, c)}")
    elif t == "sell_business":
        if not s["business"]:
            raise ValueError("Vous n'avez pas d'entreprise.")
        s["cash"] += s["business"]["value"]
        s["log"].append(f"Vente de l'entreprise : {_money(s['business']['value'], c)}")
        s["business"] = None
    elif t == "give":
        amt = _amount(a)
        _spend(s, amt)
        st["given"] += amt
        st["gifts"] += 1
        st["autres"] += 1
        s["log"].append(f"Don : {_money(amt, c)}")
    else:
        raise ValueError(f"Action inconnue : {t}")


def flags(s):
    st = s["stats"]
    return {
        "working": working(s), "retired": retired(s),
        "partner": s["partner"], "no_partner": not s["partner"], "children": s["children"] > 0,
        "home": bool(s["homes"]), "rental": any(h["use"] == "rental" for h in s["homes"]),
        "etf": s["etf"] > 0, "business": bool(s["business"]), "studied": s["studied"],
        "business_mature": bool(s["business"]) and s["business"]["years"] >= RULES["buyout_min_years"],
        "gave": st["given"] > 0, "owed": st["given"] - st["refunded"] > 1, "has_debt": s["debt"] > 0,
        "abroad": st["abroad"] > 0, "angel": st["angel"] > 0, "cosigned": st["cosigned"] > 0,
    }


def _weight(s, e, f):
    if not all(f[r] for r in e.get("requires", [])) or any(f[r] for r in e.get("excludes", [])):
        return 0.0
    if not e.get("age_min", 0) <= s["age"] <= e.get("age_max", 999):
        return 0.0
    w = e["weight"] * e.get("country_weight", {}).get(s["country"], 1)
    for flag, mult in e.get("weight_if", {}).items():
        w *= mult if f[flag] else 1
    if e.get("age_factor"):
        w *= max(RULES["age_factor_min"], s["age"] / RULES["age_factor_ref"])
    return w


def _draw_event(s):
    f = flags(s)
    w = [_weight(s, e, f) for e in EVENTS] + [RULES["no_event_weight"]]
    i = int(_rng(s["seed"], _EVENT, s["year"]).choice(len(w), p=np.array(w) / sum(w)))
    return EVENTS[i] if i < len(EVENTS) else None


def apply_effects(s, eff, yr):
    c = COUNTRIES[s["country"]]
    st = s["stats"]
    ref = s["salary"] if working(s) else s["lifestyle"]
    for k, v in eff.items():
        if k == "salary_mult":
            s["salary"] *= v
        elif k in ("income_mult", "rent_mult"):
            yr[k] *= v
        elif k in ("inflation_add", "rate_add"):
            yr[k] += v
        elif k == "fx_shock":
            yr["fx_add"] += v
        elif k == "home_shock":
            yr["home_add"] += v
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
            st["given"] += v * ref
        elif k == "refund_given":
            # on ne récupère jamais plus que ce qu'on a donné et pas encore récupéré
            amt = min(v * ref, st["given"] - st["refunded"])
            s["cash"] += amt
            st["refunded"] += amt
        elif k in ("experience_salary", "experience_usd"):
            amt = v * ref if k == "experience_salary" else usd(s, v)
            s["cash"] -= amt
            st["experience"] += amt
        elif k == "debt_salary":
            s["debt"] += v * ref
            s["debt_years"] = RULES["debt_years"]
        elif k == "business_mult":
            if s["business"]:
                s["business"]["value"] *= v
        elif k == "buyout":
            if s["business"]:
                price = s["business"]["value"] * v
                s["cash"] += price
                s["log"].append(f"Entreprise vendue : {_money(price, c)}")
                s["business"] = None
        elif k == "count":
            for name, n in v.items():
                if name not in COUNTERS:
                    raise KeyError(f"compteur inconnu : {name}")
                st[name] = max(0, st[name] + n) if name in _FLOORED else st[name] + n
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


def _bankruptcy(s):
    """Faillite personnelle : au-delà de N années de train de vie, la dette est effacée,
    tout le patrimoine restant est perdu et les dépenses sont ramenées au niveau du revenu."""
    # les biens couvrent la dette : pas de faillite (sinon un salaire à 0 rendrait la moindre dette fatale)
    if s["debt"] <= RULES["bankruptcy_income_years"] * s["lifestyle"] or net_worth(s) >= 0:
        return
    s["debt"], s["cash"], s["etf"], s["homes"], s["business"] = 0.0, 0.0, 0.0, [], None
    s["stats"]["bankruptcies"] += 1
    spend = spending(s)
    if spend > 0:
        # pendant les études le revenu est nul : on se cale sur le salaire, sinon les dépenses tombent à 0 pour toujours
        s["spend_mult"] *= min(1.0, (income(s) or s["salary"]) / spend)
    s["log"].append("Faillite personnelle : vos dettes sont effacées, mais vous repartez de zéro avec un train de vie réduit.")


def _market_year(s, yr):
    rows = _BY_RETURN[s["country"]]
    n = RULES["extreme_years"]
    pool = {"worst": rows[:n], "best": rows[-n:]}.get(yr["market"], rows)
    return pool[int(_rng(s["seed"], _MARKET, s["year"]).integers(len(pool)))]


def _finances(s, yr, c):
    m = _market_year(s, yr)
    infl = m["inflation"] + yr["inflation_add"]
    inc = income(s) * yr["income_mult"]
    spend = spending(s)
    flow = inc - spend
    homes0 = sum(h["value"] for h in s["homes"])
    for h in s["homes"]:
        flow -= h["value"] * c["home_costs"]
        if h["use"] == "rental":
            flow += h["value"] * c["rent_yield"] * yr["rent_mult"]
        if h["mortgage"] > 0:
            pay, h["mortgage"] = _amortize(h["mortgage"], c["mortgage_rate"] + yr["rate_add"], h["years_left"], infl)
            h["years_left"] = max(1, h["years_left"] - 1)
            flow -= pay
        h["value"] *= 1 + m["home_real"] + yr["home_add"]
    if s["debt"] > 0:
        pay, s["debt"] = _amortize(s["debt"], c["debt_rate"], s["debt_years"], infl)
        s["debt_years"] = max(1, s["debt_years"] - 1)
        flow -= pay

    gains = {"property": sum(h["value"] for h in s["homes"]) - homes0}
    cash0, etf0 = s["cash"], s["etf"]
    if s["cash"] > 0:
        # rendement réel historique de l'épargne, corrigé des chocs de taux et d'inflation de l'année
        s["cash"] *= (1 + m["cash_real"] + yr["rate_add"]) * (1 + m["inflation"]) / (1 + infl)
    s["etf"] *= 1 + m["stocks_real"]
    gains["savings"], gains["stocks"] = s["cash"] - cash0, s["etf"] - etf0
    s["fx"] *= 1 + m["fx_real"] + yr["fx_add"]
    s["cash"] += flow

    if s["business"]:
        s["business"]["years"] += 1
        fail = 1 - c["business_survival_5y"] ** (1 / 5)
        if _rng(s["seed"], _BUSINESS, s["year"]).random() < fail:
            s["log"].append("Votre entreprise fait faillite. Vous retrouvez un emploi salarié.")
            s["business"] = None
            s["salary"] *= RULES["business_fail_salary_mult"]
    if s["studying"]:
        s["studying"] -= 1
        if not s["studying"]:
            s["salary"] *= 1 + RULES["study_premium"]
            s["log"].append("Diplôme en poche : votre salaire augmente.")
    _cover_shortfall(s, c)
    _bankruptcy(s)
    if working(s):
        s["salary"] *= 1 + c["salary_growth_real"]
        s["lifestyle"] = s["salary"]
    return {"inflation": infl, "market_year": m["year"], "market_return": m["stocks_real"],
            "income": inc, "spend": spend,
            # année historique rejouée (avant chocs) et chocs d'événements de l'année, pour l'affichage
            "economy": {k: m[k] for k in ("stocks_real", "inflation", "cash_real", "fx_real", "home_real")},
            "shocks": {k: yr[k] for k in ("rate_add", "inflation_add", "fx_add", "home_add")},
            "gains": gains}


def step(s, actions=(), choice=None):
    """Une année. Atomique : si une décision est refusée, l'état reste inchangé."""
    backup = copy.deepcopy(s)
    try:
        return _step(s, actions, choice)
    except Exception:
        s.clear()
        s.update(backup)
        raise


def max_actions(s):
    return RULES["max_actions_avance"] if s["level"] == "avance" else RULES["max_actions"]


def _rebalance(s, c):
    """Niveau Avancé : ramène la part en ETF (sur ETF + liquidités hors fonds d'urgence) vers la cible."""
    if s["target"] is None:
        return
    free = max(available(s), 0.0)
    total = free + s["etf"]
    d = min(s["target"] * total - s["etf"], free)
    if total <= 0 or abs(d) < RULES["rebalance_min_share"] * total:
        return
    s["cash"] -= d
    s["etf"] += d
    if d > 0:
        s["stats"]["invested"] += d
    s["log"].append(f"Rééquilibrage : {'achat' if d > 0 else 'vente'} d'ETF pour {_money(abs(d), c)}")


def _step(s, actions, choice):
    if s["done"]:
        raise ValueError("Cette vie est terminée.")
    c = COUNTRIES[s["country"]]
    yr = {"income_mult": 1.0, "rent_mult": 1.0, "inflation_add": 0.0, "rate_add": 0.0,
          "fx_add": 0.0, "home_add": 0.0, "market": None}
    s["log"] = []
    nw0 = net_worth(s)  # pour la décomposition de la variation du patrimoine (affichage seulement)
    if s["pending"]:
        opts = EVENT_BY_ID[s["pending"]]["choices"]
        if choice is None or not 0 <= int(choice) < len(opts):
            raise ValueError("Un choix est attendu pour l'événement en cours.")
        apply_effects(s, opts[int(choice)]["effects"], yr)
        s["log"].append(f"Votre choix : {opts[int(choice)]['label']}")
        s["pending"] = None
    elif choice is not None:
        raise ValueError("Aucun choix n'est attendu.")
    if len(actions) > max_actions(s):
        raise ValueError(f"Au plus {max_actions(s)} décisions par an.")
    for a in actions:
        _act(s, a, c)
    _rebalance(s, c)

    nw1 = net_worth(s)
    ev = _draw_event(s)
    if ev and "choices" in ev:
        s["pending"] = ev["id"]
    elif ev:
        apply_effects(s, ev.get("effects_by_country", {}).get(s["country"], ev["effects"]), yr)

    nw2 = net_worth(s)
    fin = _finances(s, yr, c)
    nw = net_worth(s)
    g = fin.pop("gains")
    fin["breakdown"] = {"decisions": nw1 - nw0, "event": nw2 - nw1, **g, "rest": nw - nw2 - sum(g.values())}
    rentals = sum(h["value"] - h["mortgage"] for h in s["homes"] if h["use"] == "rental")
    biz = s["business"]["value"] if s["business"] else 0.0
    s["history"].append({
        "age": s["age"], "net_worth": nw, "net_worth_ppp": nw / c["ppp_per_intl_usd"],
        "cash": s["cash"], "etf": s["etf"], "property": sum(h["value"] - h["mortgage"] for h in s["homes"]),
        "business": biz, "debt": s["debt"], "risky": s["etf"] + rentals + biz,
        "event": ev["id"] if ev else None, "log": s["log"], "decided": bool(actions) or choice is not None, **fin,
    })
    s["age"] += 1
    s["year"] += 1
    if s["age"] >= s["death_age"]:
        s["done"] = True
        s["pending"] = None
    return s


def replay(seed, turns, country=None, profile=None, level="decouverte"):
    """Rejoue une vie à partir de sa graine (et de son profil en mode réaliste) et de ses décisions."""
    if level not in ("decouverte", "avance"):
        raise ValueError("Niveau inconnu.")
    try:
        s = new_life(seed, country, profile)
        s["level"] = level
    except (KeyError, TypeError) as e:
        raise ValueError(f"Profil invalide : {e}") from e
    for t in turns:
        try:
            step(s, t.get("actions", []), t.get("choice"))
        except (KeyError, TypeError, IndexError, AttributeError) as e:
            raise ValueError(f"Décision invalide : {e}") from e
    return s
