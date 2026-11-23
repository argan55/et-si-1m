"""Miroir de fin (version simplifiée V0) : des faits et deux axes, sans jugement."""
from .data import COUNTRIES, RULES


def _clip(x):
    return max(-1.0, min(1.0, x))


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
    return {
        "trajectory": [{"age": y["age"], "net_worth_ppp": y["net_worth_ppp"]} for y in h],
        "final_net_worth": h[-1]["net_worth"] if h else 0.0,
        "final_net_worth_ppp": h[-1]["net_worth_ppp"] if h else 0.0,
        "peak_net_worth_ppp": max((y["net_worth_ppp"] for y in h), default=0.0),
        "freedom_years": sum(1 for y in h if y["net_worth"] >= RULES["freedom_multiple"] * y["spend"]),
        "years": len(h),
        "trips": st["trips"],
        "given": st["given"],
        "given_ppp": st["given"] / c["ppp_per_intl_usd"],
        # -1 = Vivre, +1 = Bâtir
        "vivre_batir": (built - lived) / (built + lived) if built + lived else 0.0,
        # -1 = Sécurité, +1 = Aventure
        "securite_aventure": _clip(2 * risk - 1 + RULES["choice_axis_weight"] * st["aventure"]),
        # pour le miroir complet (étape 3)
        "studied": s["studied"], "abroad": st["abroad"], "autres": st["autres"],
    }
