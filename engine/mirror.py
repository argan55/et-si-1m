"""Miroir de fin : des faits et quatre axes, sans jugement. Chaque axe va de -1 à +1."""
import math

from .data import COUNTRIES, RULES


def _clip(x):
    return max(-1.0, min(1.0, x))


def _log_balance(a, b, neutral, span):
    """Position de b face à a sur une échelle logarithmique : 0 quand b = neutral × a,
    ±1 à un facteur 10**span de là. -1 si seul a existe, +1 si seul b existe, 0 si aucun."""
    if not a and not b:
        return 0.0
    if not a or not b:
        return 1.0 if b else -1.0
    return _clip((math.log10(b / a) - math.log10(neutral)) / span)


def mirror(s):
    c = COUNTRIES[s["country"]]
    h, st = s["history"], s["stats"]
    lived = st["travel_spent"] + st["experience"]
    built = st["invested"] + st["repaid"]
    shares = [
        y["risky"] / total
        for y in h
        if (total := y["cash"] + y["etf"] + y["property"] + y["business"]) > 0
    ]
    risk = sum(shares) / len(shares) if shares else 0.0
    w = RULES["choice_axis_weight"]
    return {
        "trajectory": [{"age": y["age"], "net_worth_ppp": y["net_worth_ppp"]} for y in h],
        "final_net_worth": h[-1]["net_worth"] if h else 0.0,
        "final_net_worth_ppp": h[-1]["net_worth_ppp"] if h else 0.0,
        "peak_net_worth_ppp": max((y["net_worth_ppp"] for y in h), default=0.0),
        "freedom_years": sum(1 for y in h if y["net_worth"] >= RULES["freedom_multiple"] * y["spend"]),
        "years": len(h),
        "trips": st["trips"],
        "trips_abroad": st["trips_abroad"],
        "given": st["given"],
        "given_ppp": st["given"] / c["ppp_per_intl_usd"],
        "studied": s["studied"],
        # -1 = Vivre, +1 = Bâtir : ce qui a été construit face à ce qui a été vécu (voyages, fêtes) ;
        # échelle logarithmique, car on investit des centaines de milliers et on voyage par milliers
        "vivre_batir": _log_balance(lived, built, RULES["axis_build_neutral_ratio"], RULES["axis_build_span"]),
        # -1 = Sécurité, +1 = Aventure : part moyenne du patrimoine en actifs risqués, et les paris acceptés
        "securite_aventure": _clip(2 * risk - 1 + w * st["aventure"]),
        # -1 = Moi, +1 = Les autres : argent donné contre argent dépensé pour soi, et l'aide accordée ou refusée
        # un an de train de vie sert de plancher, pour qu'un petit montant ne fasse pas basculer l'axe
        "moi_autres": _clip((st["given"] - lived) / (st["given"] + lived + s["lifestyle"]) + w * st["autres"]),
        # -1 = Racines, +1 = Ailleurs : départs (études, poste, tour du monde) et voyages à l'étranger
        "racines_ailleurs": _clip(-1 + RULES["axis_abroad_weight"] * st["abroad"]
                                  + RULES["axis_trip_weight"] * st["trips_abroad"]),
    }
