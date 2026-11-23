# 1 M$, une vie

Un jeu de simulation dans le navigateur. Vous recevez 1 M$ au cours d'une vie tirée au sort, et vous décidez chaque année quoi en faire. À la fin, un miroir montre la trajectoire de votre patrimoine et votre « style ».

Le message du jeu : **1 M$ ne vaut pas la même chose pour tout le monde**.

> Jeu à but pédagogique. **Ce n'est pas un conseil financier.**

État actuel : **V0 jouable** (Canada et Brésil ; briques investir, immobilier et voyager ; 15 événements ; miroir simplifié).

## Lancer le jeu en local

Prérequis : Python 3.12 et Node 20 ou plus récent.

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt    # sous Linux/macOS : .venv/bin/pip
.venv/Scripts/python -m uvicorn api.main:app --port 8000

cd web
npm install
npm run dev        # http://localhost:5173
```

Pour lancer les tests : `.venv/Scripts/python -m pytest`

Pour partager une vie, utilisez l'URL avec sa graine : `?seed=42`. Pour imposer un pays : `?seed=42&pays=CA`.

## Architecture

| Dossier | Rôle |
|---|---|
| `engine/` | Moteur en Python pur, déterministe, indépendant de l'API (réutilisable par le futur simulateur) |
| `api/` | FastAPI **sans état** : le client envoie la graine et la liste de ses décisions, le serveur rejoue la vie |
| `web/` | Interface React (Vite) |
| `data/` | Toutes les hypothèses chiffrées, avec leurs sources |
| `tests/` | pytest : déterminisme, partie complète, écart Canada/Brésil, sources présentes |

Principes du moteur :
- Montants en monnaie locale et **en termes réels**.
- Affichage aussi **en pouvoir d'achat (PPA)**.
- Rendements boursiers **tirés au hasard parmi les années réelles de 1928 à 2025** (bootstrap).
- L'aléa de chaque année dépend seulement de la graine et du numéro de l'année : une décision ne modifie jamais les tirages des années suivantes.

## Sources des données

- **Rendements** (`data/returns.csv`) : A. Damodaran, NYU Stern, *Historical Returns on Stocks, Bonds and Bills* (`histretSP.xls`). Rendements réels du S&P 500 (dividendes inclus) et des bons du Trésor, de 1928 à 2025.
- **Pays** (`data/countries.json`) : chaque champ a sa source dans la clé `sources`. On y trouve :
  - Banque mondiale : PPA, change, inflation, Gini ;
  - Statistique Canada et IBGE : salaires, espérance de vie, ménages ;
  - Banque du Canada et Banco Central do Brasil : taux ;
  - ACI/CREA et FipeZap : immobilier ;
  - OCDE : pensions, salaires ;
  - BRI : prix réels de l'immobilier.
  
  Les valeurs marquées ≈ sont des ordres de grandeur à affiner.
- **Règles de jeu** (`data/rules.json`) : ce sont des choix de conception, chacun documenté.
- **Événements** (`data/events.json`) : écrits à la main. Les poids sont des règles de jeu, pas des probabilités statistiques.

## Captures d'écran

*À ajouter.*
