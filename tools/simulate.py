"""Compare des stratégies types sur N vies par pays (patrimoine final en PPA, années de liberté).

Usage : python tools/simulate.py [N]
Les choix d'événements prennent toujours la dernière option (en général « refuser »).
"""
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import copy  # noqa: E402

from engine import mirror, new_life, step  # noqa: E402
from engine.data import COUNTRIES, EVENT_BY_ID  # noqa: E402
from engine.game import _act, available, usd  # noqa: E402


def probe_choices(s):
    return EVENT_BY_ID[s["pending"]]["choices"] if s["pending"] else []


ALL_ETF = lambda s: {"type": "invest", "amount": available(s) * 0.99}  # noqa: E731
STRATEGIES = {
    "rien (liquidités)": lambda s: [],
    "tout en ETF": lambda s: [ALL_ETF] if s["year"] == 0 else [],
    "dettes puis ETF": lambda s: ([{"type": "repay", "target": "debt", "amount": s["debt"]}] if s["debt"] else []) + [ALL_ETF] if s["year"] == 0 else [],
    "résidence + ETF": lambda s: [{"type": "buy_home", "use": "residence", "size": 1, "down": 1}, ALL_ETF] if s["year"] == 0 else [],
    "2 locatifs (20 %)": lambda s: [{"type": "buy_home", "use": "rental", "size": 1, "down": 0.2}] * 2 if s["year"] == 0 else [],
    "entreprise + ETF": lambda s: [{"type": "start_business", "amount": usd(s, 200000)}, ALL_ETF] if s["year"] == 0 else [],
    "études + ETF": lambda s: [{"type": "study", "years": 2}, ALL_ETF] if s["year"] == 0 else [],
    "grand voyage chaque année": lambda s: [{"type": "invest", "amount": available(s) * 0.8}] if s["year"] == 0 else (
        [{"type": "invest", "amount": -min(s["etf"], usd(s, 3000))}] if s["etf"] > 0 else []) + [{"type": "travel", "kind": "big"}],
    "donner la moitié + ETF": lambda s: [{"type": "give", "amount": s["cash"] * 0.5}, ALL_ETF] if s["year"] == 0 else [],
}


def play(seed, country, strategy):
    s = new_life(seed, country)
    while not s["done"]:
        choice = len(probe_choices(s)) - 1 if s["pending"] else None
        planned = STRATEGIES[strategy](s)
        actions = []
        after = copy.deepcopy(s)  # état après les actions déjà retenues cette année
        for a in planned:  # on garde les actions acceptées, dans l'ordre
            a = a(after) if callable(a) else a
            try:
                step(copy.deepcopy(s), actions + [a], choice)
                _act(after, a, COUNTRIES[s["country"]])
                actions.append(a)
            except ValueError:
                pass
        step(s, actions, choice)
    return s


def summary(n=100, countries=tuple(COUNTRIES)):
    out = {}
    for code in countries:
        for name in STRATEGIES:
            lives = [play(seed, code, name) for seed in range(n)]
            finals = sorted(s["history"][-1]["net_worth_ppp"] for s in lives)
            out[(code, name)] = {
                "median": statistics.median(finals), "p10": finals[n // 10], "p90": finals[n * 9 // 10],
                "freedom": statistics.mean(mirror(s)["freedom_years"] / mirror(s)["years"] for s in lives),
                # une faillite remet le patrimoine à 0 : on la compte même si la vie finit au-dessus de 0
                "broke": sum(s["stats"]["bankruptcies"] > 0 or s["history"][-1]["net_worth"] < 0 for s in lives) / n,
            }
    return out


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    res = summary(n)
    print(f"{'pays':4} {'stratégie':28} {'médiane':>10} {'p10':>10} {'p90':>10} {'liberté':>8} {'ruine':>6}  (M$ PPA)")
    for (code, name), r in res.items():
        print(f"{code:4} {name:28} {r['median']/1e6:10.2f} {r['p10']/1e6:10.2f} {r['p90']/1e6:10.2f} {r['freedom']:8.0%} {r['broke']:6.0%}")
