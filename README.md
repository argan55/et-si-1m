# 1 M$, une vie

Un jeu de simulation dans le navigateur. Vous recevez 1 M$ au cours d'une vie tirée au sort, et vous décidez chaque année quoi en faire. À la fin, un miroir montre la trajectoire de votre patrimoine et votre « style ».

Le message du jeu : **1 M$ ne vaut pas la même chose pour tout le monde**.

> Jeu à but pédagogique. **Ce n'est pas un conseil financier.**

État actuel : **étape 2**.
- Pays : Canada et Brésil.
- 7 briques : investir, immobilier, voyager, rembourser ses dettes, étudier à l'étranger, entreprendre, donner.
- 43 événements, et un miroir simplifié.
- La partie en cours est sauvegardée dans le navigateur.

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
| `tests/` | pytest : déterminisme, partie complète, écart Canada/Brésil, briques, sources présentes |
| `tools/` | Construction de l'historique de marché, simulateur de stratégies (`python tools/simulate.py 100`) |

Principes du moteur :
- Montants en monnaie locale et **en termes réels**.
- Affichage aussi **en pouvoir d'achat (PPA)**.
- Chaque année de jeu **rejoue une année réelle du pays (2002-2025)** : bourse locale, inflation, taux, change et immobilier ensemble.
- L'aléa de chaque année dépend seulement de la graine et du numéro de l'année : une décision ne modifie jamais les tirages des années suivantes.

## Sources des données

Toutes les sources sont dans [data/SOURCES.md](data/SOURCES.md), avec la liste des valeurs qui restent des estimations. Les principales :
- **Marchés** : MSCI (actions locales, dividendes compris), Statistique Canada et IBGE (inflation), OCDE/FRED (taux, change), BRI (immobilier).
- **Pays** : Banque mondiale, Statistique Canada, IBGE, Banque du Canada, Banco Central do Brasil, ACI/CREA, FipeZap, Equifax, CNC, OCDE.
- **Règles de jeu et événements** : ce sont des choix de conception, chacun documenté dans son fichier.

## Captures d'écran

*À ajouter.*
