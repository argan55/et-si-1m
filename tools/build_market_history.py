"""Construit data/market_history.csv à partir des séries brutes téléchargées (voir data/SOURCES.md).

Usage : python tools/build_market_history.py <dossier des téléchargements>
Le dossier doit contenir les fichiers nommés dans COUNTRIES ci-dessous, plus CPIAUCSL.csv
(IPC américain) et, pour la correction de 2011-2012, msci_BR_usd.json, ptax.json, msci_MX_usd.json, DEXMXUS.csv.
Variations de décembre à décembre (T4 à T4 pour l'immobilier), en termes réels.
Exception : pour Hong Kong et le Mexique, l'inflation est la moyenne annuelle (Banque mondiale),
faute de série mensuelle à jour accessible sans clé d'API.
"""
import csv
import json
import sys
from pathlib import Path

LAST = 2025
src = Path(sys.argv[1])
out = Path(__file__).resolve().parent.parent / "data" / "market_history.csv"


def fred(name):
    """{(année, mois): valeur} d'un CSV FRED."""
    with open(src / name) as f:
        r = csv.reader(f)
        next(r)
        return {(int(d[:4]), int(d[5:7])): float(v) for d, v in r if v not in ("", ".")}


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


def hibor(name):
    recs = json.loads((src / name).read_text())["result"]["records"]
    return {(int(r["end_of_month"][:4]), int(r["end_of_month"][5:7])): r["ir_3m"] for r in recs if r["ir_3m"] is not None}


def annual_pct_as_index(series):
    """Inflation annuelle en % (Banque mondiale) -> indice fictif au mois de décembre."""
    idx, level = {}, 100.0
    for (y, _), v in sorted(series.items()):
        level *= 1 + v / 100
        idx[(y, 12)] = level
        idx[(y - 1, 12)] = idx.get((y - 1, 12), level / (1 + v / 100))
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


def fred_year_end(name):
    """Dernière valeur quotidienne disponible de chaque mois de décembre (CSV FRED quotidien)."""
    out = {}
    with open(src / name) as f:
        r = csv.reader(f)
        next(r)
        for d, v in r:
            if d[5:7] == "12" and v not in ("", "."):
                out[(int(d[:4]), 12)] = float(v)  # les lignes sont triées : la dernière gagne
    return out


def patch_msci_2011(local, usd_file, fx_year_end):
    """Les séries MSCI en monnaie locale du Brésil et du Mexique changent d'échelle d'août 2011
    à janvier 2012. Pour 2011 et 2012, on reconstruit le niveau local : niveau USD × change de fin d'année."""
    usd = msci(usd_file)
    rebuilt = {(y, 12): usd[(y, 12)] * fx_year_end[(y, 12)] for y in (2010, 2011, 2012)}
    scale = local[(2010, 12)] / rebuilt[(2010, 12)]
    local[(2011, 12)] = rebuilt[(2011, 12)] * scale
    local[(2012, 12)] = rebuilt[(2012, 12)] * scale
    assert abs(local[(2013, 12)] / local[(2012, 12)] - 1) < 0.5, "rupture d'échelle non corrigée"
    return local


def invert(series):
    return {k: 1 / v for k, v in series.items()}


us_cpi = fred("CPIAUCSL.csv")
# fx : unités de monnaie locale pour 1 dollar US (None : le pays est en dollars US)
COUNTRIES = {
    "CA": dict(first=2002, stocks=msci("msci_CA.json"), cpi=statcan("cpi_ca.json"),
               rate=fred("IR3TIB01CAA156N.csv"), fx=fred("EXCAUS.csv"), home=fred("QCAR628BIS.csv")),
    "BR": dict(first=2002, stocks=patch_msci_2011(msci("msci_BR.json"), "msci_BR_usd.json", ptax_year_end("ptax.json")),
               cpi=ipca_index("ipca.json"),
               rate=fred("IRSTCI01BRA156N.csv"), fx=fred("EXBZUS.csv"), home=fred("QBRR628BIS.csv")),
    "FR": dict(first=2002, stocks=msci("msci_FR.json"), cpi=fred("CP0000FRM086NEST.csv"),
               rate=fred("IR3TIB01FRA156N.csv"), fx=invert(fred("EXUSEU.csv")), home=fred("QFRR628BIS.csv")),
    "HK": dict(first=2002, stocks=msci("msci_HK.json"), cpi=annual_pct_as_index(fred("FPCPITOTLZGHKG.csv")),
               rate=hibor("hibor.json"), fx=fred("EXHKUS.csv"), home=fred("QHKR628BIS.csv")),
    "US": dict(first=2002, stocks=msci("msci_US.json"), cpi=us_cpi,
               rate=fred("TB3MS.csv"), fx=None, home=fred("QUSR628BIS.csv")),
    # l'indice immobilier de la BRI pour le Mexique commence en 2005
    "MX": dict(first=2006, stocks=patch_msci_2011(msci("msci_MX.json"), "msci_MX_usd.json", fred_year_end("DEXMXUS.csv")), cpi=annual_pct_as_index(fred("FPCPITOTLZGMEX.csv")),
               rate=fred("IR3TIB01MXA156N.csv"), fx=fred("EXMXUS.csv"), home=fred("QMXR628BIS.csv")),
}

rows = []
for code, s in COUNTRIES.items():
    for y in range(s["first"], LAST + 1):
        infl = growth(s["cpi"], y)
        us_infl = growth(us_cpi, y)
        fx_nominal = growth(s["fx"], y) if s["fx"] else 0.0
        rows.append({
            "country": code, "year": y,
            "stocks_real": (1 + growth(s["stocks"], y)) / (1 + infl) - 1,
            "inflation": infl,
            "cash_real": (1 + yearly_avg(s["rate"], y) / 100) / (1 + infl) - 1,
            # > 0 : le dollar US coûte plus cher, en termes réels, dans la monnaie locale
            "fx_real": (1 + fx_nominal) * (1 + us_infl) / (1 + infl) - 1 if s["fx"] else 0.0,
            # indice BRI déjà réel, T4 sur T4 (les dates trimestrielles FRED sont au 1er mois du trimestre)
            "home_real": growth(s["home"], y, 10),
        })

with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    for r in rows:
        w.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in r.items()})
print(f"{len(rows)} lignes -> {out}")
