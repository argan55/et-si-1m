"""Construit data/market_history.csv à partir des séries brutes téléchargées (voir data/SOURCES.md).

Usage : python tools/build_market_history.py <dossier des téléchargements>
Le dossier doit contenir : msci_CA.json, msci_BR.json, msci_BR_usd.json, ptax.json, cpi_ca.json, ipca.json, CPIAUCSL.csv,
IR3TIB01CAA156N.csv, IRSTCI01BRA156N.csv, EXCAUS.csv, EXBZUS.csv, QCAR628BIS.csv, QBRR628BIS.csv.
Toutes les variations sont de décembre à décembre (Q4 à Q4 pour l'immobilier), en termes réels.
"""
import csv
import json
import sys
from pathlib import Path

FIRST, LAST = 2002, 2025
src = Path(sys.argv[1])
out = Path(__file__).resolve().parent.parent / "data" / "market_history.csv"


def fred(name):
    """{(année, mois): valeur} d'un CSV FRED."""
    with open(src / name) as f:
        r = csv.reader(f)
        next(r)
        return {(int(d[:4]), int(d[5:7])): float(v) for d, v in r if v not in ("", ".")}


def december(series, year):
    return series[(year, 12)]


def msci(name):
    levels = json.loads((src / name).read_text())["indexes"]["INDEX_LEVELS"]
    return {(x["calc_date"] // 10000, x["calc_date"] // 100 % 100): x["level_eod"] for x in levels}


def statcan(name):
    pts = json.loads((src / name).read_text())[0]["object"]["vectorDataPoint"]
    return {(int(p["refPer"][:4]), int(p["refPer"][5:7])): p["value"] for p in pts}


def ipca_index(name):
    """Indice cumulé à partir des variations mensuelles de l'IPCA (%)."""
    idx, level = {}, 100.0
    for p in json.loads((src / name).read_text()):
        level *= 1 + float(p["valor"]) / 100
        idx[(int(p["data"][6:]), int(p["data"][3:5]))] = level
    return idx


def yearly_avg(series, year):
    vals = [v for (y, _), v in series.items() if y == year]
    return sum(vals) / len(vals)


def growth(series, year, month=12):
    return series[(year, month)] / series[(year - 1, month)] - 1


def ptax_year_end(name):
    """Dernier cours PTAX (BRL par USD) de chaque mois de décembre."""
    out = {}
    for p in json.loads((src / name).read_text()):
        if p["data"][3:5] == "12":
            out[(int(p["data"][6:]), 12)] = float(p["valor"])
    return out


def patch_msci_brazil(local):
    """La série MSCI Brazil en BRL change d'échelle d'août 2011 à janvier 2012.
    Pour 2011 et 2012, on reconstruit le niveau en BRL : niveau USD × PTAX de fin d'année."""
    usd, ptax = msci("msci_BR_usd.json"), ptax_year_end("ptax.json")
    rebuilt = {(y, 12): usd[(y, 12)] * ptax[(y, 12)] for y in (2010, 2011, 2012)}
    scale = local[(2010, 12)] / rebuilt[(2010, 12)]
    local[(2011, 12)] = rebuilt[(2011, 12)] * scale
    local[(2012, 12)] = rebuilt[(2012, 12)] * scale
    assert abs(local[(2013, 12)] / local[(2012, 12)] - 1) < 0.5, "rupture d'échelle non corrigée"
    return local


us_cpi = fred("CPIAUCSL.csv")
countries = {
    "CA": dict(stocks=msci("msci_CA.json"), cpi=statcan("cpi_ca.json"), rate=fred("IR3TIB01CAA156N.csv"),
               fx=fred("EXCAUS.csv"), home=fred("QCAR628BIS.csv")),
    "BR": dict(stocks=patch_msci_brazil(msci("msci_BR.json")), cpi=ipca_index("ipca.json"), rate=fred("IRSTCI01BRA156N.csv"),
               fx=fred("EXBZUS.csv"), home=fred("QBRR628BIS.csv")),
}

rows = []
for code, s in countries.items():
    for y in range(FIRST, LAST + 1):
        infl = growth(s["cpi"], y)
        us_infl = growth(us_cpi, y)
        real = lambda nominal: (1 + nominal) / (1 + infl) - 1  # noqa: E731
        rows.append({
            "country": code, "year": y,
            "stocks_real": (1 + growth(s["stocks"], y)) / (1 + infl) - 1,
            "inflation": infl,
            "cash_real": real(yearly_avg(s["rate"], y) / 100),
            # > 0 : le dollar US coûte plus cher, en termes réels, dans la monnaie locale
            "fx_real": (1 + growth(s["fx"], y)) * (1 + us_infl) / (1 + infl) - 1,
            # indice BRI déjà réel, T4 sur T4 (les dates trimestrielles FRED sont au 1er mois du trimestre)
            "home_real": growth(s["home"], y, 10),
        })

with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    for r in rows:
        w.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in r.items()})
print(f"{len(rows)} lignes -> {out}")
