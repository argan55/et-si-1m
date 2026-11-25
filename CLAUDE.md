# Jeu 1 M$ : « Et si… ? » (sous-titre : « 1 M$, une vie »)

Jeu de simulation dans le navigateur, inspiré des mécaniques de *1 in 8 Billion* (1in8b.life) : le joueur reçoit 1 M$ au cours d'une vie tirée au sort et décide année par année quoi en faire. Message du jeu : **1 M$ ne vaut pas la même chose pour tout le monde**. Ne pas reprendre le nom ni le design du jeu d'origine. Ce n'est pas un conseil financier (l'indiquer dans l'interface).

Le code est écrit par Claude Code. Réponds en français. L'interface est en français, avec l'anglais prévu en V2.

## Spec — V1

- **Objectif** : un jeu court (10 à 15 min), rejouable et facile à partager, servant de projet de portfolio GitHub avec une démo en ligne.
- **Déroulé d'une partie** :
  1. **Tirage** : pays, âge, salaire, dettes et situation familiale tirés de distributions réalistes par pays ; origine du 1 M$ tirée parmi loterie, héritage et vente d'entreprise (l'origine influence l'âge et le contexte).
  2. **Tours annuels** : chaque année, 1 ou 2 décisions parmi les briques disponibles, puis un événement aléatoire, puis la mise à jour des finances.
  3. **Fin** : à la mort du personnage (espérance de vie selon le pays, avec un aléa).
  4. **Miroir de fin** : trajectoire du patrimoine, années de liberté financière, argent donné, expériences vécues, et un « style » sur 4 axes, présenté sans jugement.
- **Deux modes** : *jeu* (vie tirée au sort, 1 M$ fixe) et *réaliste* (le joueur saisit son profil et le montant).
- **Briques** : investir (ETF), immobilier (résidence ou locatif, avec hypothèque), rembourser ses dettes, voyager, étudier à l'étranger, entreprendre, donner. Un fonds d'urgence est géré par défaut. Les briques interagissent : les loyers sont un revenu, les études font monter le salaire, une entreprise peut échouer ou être revendue.
- **Pays** : Canada, France, Hong Kong, États-Unis, Brésil, Mexique.
- **Événements** : environ 40, écrits à la main, répartis en 4 familles :
  - marchés : krach, année record, inflation, hausse des taux ;
  - travail : promotion, perte d'emploi, offre à l'étranger ;
  - vie perso : rencontre, enfant, séparation, santé ;
  - entourage : un proche demande de l'argent, héritage, arnaque.
  Chaque événement a des probabilités qui dépendent de l'âge, du pays et des choix passés.
- **Axes du miroir** : Vivre ↔ Bâtir, Moi ↔ Les autres, Sécurité ↔ Aventure, Racines ↔ Ailleurs.
- **Moteur** :
  - Rendements tirés au sort parmi des années historiques réelles (bootstrap), pas une moyenne lissée.
  - Inflation et taux propres à chaque pays.
  - Montants convertis en pouvoir d'achat local (PPA).
  - Pas de fiscalité en V1.
  - Le moteur est déterministe avec une graine (seed), pour pouvoir rejouer et partager une même vie.

### Étapes
1. **Étape 1, V0 jouable** : Canada + Brésil ; briques investir, immobilier, voyager ; une quinzaine d'événements ; miroir simplifié.
2. **Étape 2** : les 7 briques et les 40 événements.
3. **Étape 3** : les 6 pays, le mode réaliste, le miroir complet, le déploiement en ligne.

### Hors périmètre (V2)
- Version simulateur sans jeu (répartition unique, scénarios types + manuel, Monte Carlo, comparaison côte à côte). Elle réutilisera le même moteur : garder le moteur indépendant de l'API et de l'interface.
- Fiscalité Québec/Canada
- Récit des années rédigé par un LLM
- Générateur aléatoire de scénarios
- Interface en anglais
- Briques « arrêter de travailler » et « sécurité » avancée (assurances)
- Pays à revenu faible (Inde, Nigeria)

### Critères de réussite
- Une partie complète se joue du tirage au miroir sans erreur, en 10 à 15 minutes.
- Avec la même graine, on obtient exactement la même vie.
- Le même 1 M$ donne des patrimoines finaux nettement différents entre le Canada et le Brésil, sur 100 parties simulées.
- Toutes les hypothèses chiffrées (rendements, prix immobiliers, coûts de voyage et d'études, salaires) se trouvent dans des fichiers de données sourcés, pas dans le code.
- Tests du moteur avec pytest ; README avec captures d'écran et sources des données.

### Stack
- **Moteur et API** : Python, FastAPI, pandas/numpy, pytest.
- **Interface** : React (Vite).
- **Données** : CSV/JSON versionnés. Sources : Banque mondiale (PPA, revenus, espérance de vie, inflation), historiques de rendements boursiers, sources publiques pour l'immobilier et les études.

### Limites
- **Toujours** : les tests passent avant un commit ; chaque hypothèse chiffrée a une source.
- Mets à jour la section « État » à la fin de chaque étape (fait, tests, prochaine étape).
- **Demander d'abord** : nouvelle dépendance importante, publication du dépôt ou de la démo, changement de stack.
- **Jamais** : de clé d'API dans le code ; copier des textes, le nom ou le design de 1 in 8 Billion.

### Hypothèses
- Les pays de la V0 (Canada + Brésil), ses briques (investir, immobilier, voyager) et le 4e axe (Racines ↔ Ailleurs, qui remplace Maintenant ↔ Plus tard, trop proche de Vivre ↔ Bâtir) ont été choisis par Claude, sans réponse de l'utilisateur.

## État
_À mettre à jour à la fin de chaque étape._
- 2026-11-23 : nom retenu : **« Et si… ? »**, sous-titre « 1 M$, une vie » (README, titre de la page alignés ; vérifier le titre dans `web/src`).
- 2026-11-23 : spec V1 écrite.
- 2026-11-23 : **étape 1 (V0 jouable) terminée.**
  - Contenu : Canada + Brésil ; briques investir, immobilier, voyager ; 15 événements (dont 3 à choix) ; miroir simplifié (2 axes : Vivre ↔ Bâtir, Sécurité ↔ Aventure).
  - Validation : 7 tests pytest passent. Une partie complète a été jouée dans le navigateur. Médiane du patrimoine final en PPA (tout en ETF, 100 parties) : Canada ≈ 4,9 M$, Brésil ≈ 7,3 M$.
  - Choix techniques :
    - API sans état (graine + décisions → le serveur rejoue la vie) ;
    - moteur en termes réels ;
    - aléa indexé par (graine, flux, année) ;
    - `step` atomique ;
    - données pays regroupées dans `data/countries.json` (immobilier et voyage inclus) ; règles de jeu dans `data/rules.json`.
  - Python 3.12 installé via winget ; environnement dans `.venv`.
  - Pas encore de dépôt git.
  - Limites connues :
    - les valeurs marquées ≈ dans les données sont à vérifier ;
    - recharger la page fait perdre la partie en cours ;
    - un ETF unique (S&P 500 réel) pour les deux pays : on suppose que la PPA tient dans le temps ;
    - captures d'écran du README à faire.
  - Prochaine étape : étape 2 (7 briques, 40 événements).
- 2026-11-23 : **étape 2 terminée**, commitée par l'utilisateur (`71e8049` V0, `d75d0f7` étape 2).
  - Marchés : un ETF local par pays.
    - Fichier `data/market_history.csv`, construit par `tools/build_market_history.py`.
    - Contenu : MSCI en monnaie locale dividendes compris, inflation, taux court, change réel et immobilier réel (BRI), fenêtre commune 2002-2025.
    - Chaque année de jeu rejoue une année historique complète du pays (bootstrap conjoint).
    - La série MSCI Brazil en BRL a une rupture d'échelle en 2011-2012, corrigée via USD × PTAX.
  - Écart Canada/Brésil : il tient (tout en ETF, 100 vies : Canada ≈ 7,6 M$ PPA, Brésil ≈ 13,1 M$). Il vient presque entièrement du pouvoir d'achat de départ (1 M$ US = 1,11 M$ PPA au Canada contre 2,17 M$ au Brésil). Avec un ETF local, les deux pays multiplient l'argent à peu près autant. Au Brésil, les liquidités rapportent environ 5 % réel par an, sans risque.
  - Briques ajoutées : rembourser ses dettes (consommation ou hypothèque), étudier à l'étranger (frais en dollars US qui suivent le change, pas de salaire pendant, +29,5 % de salaire ensuite), entreprendre (le bénéfice remplace le salaire, faillite selon la survie à 5 ans du pays, rachat, vente), donner.
  - Événements : 43 (10 marchés, 10 travail, 10 vie perso, 13 entourage). Leurs poids dépendent de l'âge, du pays et des choix passés (`requires`, `excludes`, `weight_if`).
  - Interface : les 7 briques ; la partie (graine + décisions) est sauvegardée dans le localStorage ; un lien `?seed=` vers une autre graine l'emporte sur la sauvegarde.
  - Données : les valeurs ≈ ont été remplacées par des valeurs sourcées quand elles existaient. Celles qui restent sont listées dans `data/SOURCES.md` (pension, croissance des salaires, part dépensée, quelques valeurs canadiennes ou brésiliennes, frais immobiliers, frais d'études).
  - Balance-check (`tools/simulate.py`, 10 stratégies × 100 vies × 2 pays) : aucune stratégie ne gagne à tous les coups ; la meilleure ne finit première que dans 24 à 34 % des vies. Deux problèmes corrigés :
    - le remboursement d'un don est plafonné à la somme donnée (donner 1 $ suffisait à débloquer des remboursements sans limite) ;
    - les enfants ne sont plus à charge après les 60 ans du parent (la ruine avec la stratégie liquidités au Canada passe de 23 % à 5 %).
  - Validation : 11 tests pytest passent ; une partie a été jouée dans le navigateur avec une entreprise, un rechargement de page et la reprise, jusqu'au miroir.
  - Limites connues :
    - taux hypothécaire canadien = taux affiché (surestimé) ;
    - revenus bruts (pas de fiscalité en V1) ;
    - les rachats d'entreprise sont fréquents (environ 2 par vie d'entrepreneur) ;
    - rembourser ses dettes change peu de chose, parce que les dettes tirées sont petites face à 1 M$.
  - Prochaine étape : étape 3 (6 pays, mode réaliste, miroir complet avec Moi ↔ Les autres et Racines ↔ Ailleurs — les compteurs `autres` et `abroad` existent déjà —, déploiement).
- 2026-11-23 : **étape 3a terminée** (6 commits, de `955b540` à `f7e8e21`, plus celui-ci).
  - Pays : France, Hong Kong, États-Unis et Mexique ajoutés, avec la même méthode (MSCI local dividendes compris, inflation, taux court, change, immobilier BRI).
    - Fenêtre 2002-2025, sauf le Mexique : 2006-2025, car l'indice BRI commence en 2005.
    - Inflation de Hong Kong et du Mexique = moyenne annuelle (Banque mondiale) ; décembre à décembre ailleurs.
    - Codes MSCI : pays développés « 9 » + code ISO, pays émergents « 8 » + code ISO (Mexique 848400).
    - La rupture d'échelle MSCI 2011-2012 touche aussi le Mexique ; la correction (USD × change de fin d'année) est généralisée.
    - Les valeurs non trouvées pour les nouveaux pays sont marquées ≈ et listées dans `data/SOURCES.md`.
  - Mode réaliste : écran d'accueil, formulaire (pays, âge, salaire, dettes, montant, couple, enfants), profil validé dans le moteur et l'API, encodé dans l'URL et la sauvegarde. Seul l'âge au décès reste tiré au sort.
  - Miroir à 4 axes :
    - Moi ↔ Les autres : dons face aux dépenses pour soi, avec un an de train de vie comme plancher, plus le compteur `autres` ;
    - Racines ↔ Ailleurs : départs et voyages à l'étranger ;
    - Vivre ↔ Bâtir : passé à une échelle logarithmique (il était collé à « Bâtir »).
  - Rachats d'entreprise : seulement après 3 ans, prix = 2 fois la valeur actuelle ; environ 0,3 offre par entreprise (0,5 au Canada et en France) contre environ 2 avant.
  - Taux hypothécaire canadien : taux effectif (Banque du Canada V122667786, 4,37 %) au lieu du taux affiché (6,23 %).
  - Balance-check, 9 stratégies × 100 vies × 6 pays :
    - aucun pays n'est dominé sur tous les critères ;
    - Canada limite : « tout en ETF » premier dans 53 % des vies, mais moins bon en années de liberté ; c'est dû aux vraies données, signalé sans être corrigé ;
    - faille critique corrigée : la dette forcée se réamortissait sans fin (un cas à -1,1 Md$). Nouvelle règle de faillite personnelle au-delà de 3 années de train de vie ; pire cas : -0,88 M$ PPA.
  - README : 6 captures dans `docs/screenshots/`.
  - Validation : 20 tests pytest passent. Les deux modes ont été joués dans le navigateur jusqu'au miroir, avec un rechargement de page en cours de partie.
  - Limites connues :
    - à Hong Kong, 10 à 16 % de faillites, surtout à la retraite : la pension est estimée (≈ 30 % du salaire) et le Gini est celui des revenus des ménages avant transferts ;
    - le Brésil et le Mexique saturent les années de liberté financière (98 à 100 %) ;
    - la brique « rembourser ses dettes » pèse peu ;
    - beaucoup de paramètres des nouveaux pays restent estimés (≈).
  - Prochaine étape : étape 3b (déploiement en ligne, à valider : publication de la démo).
- 2026-11-23 (Cline) : **préparation étape 3b faite** (non publiée).
  - Nom : **« Et si… ? »** avec le sous-titre « 1 M$, une vie » (titre `web/index.html`, en-tête `web/src/App.jsx`, README).
  - `render.yaml` : deux services Render (API `et-si-api` Python, site statique `et-si` React/Vite).
  - CORS via `ALLOWED_ORIGINS` dans `api/main.py` (origines autorisées séparées par virgules, proxy Vite en local).
  - `VITE_API_URL` dans `web/src/App.jsx` (adresse de l'API en production, vide en local).
  - README : section « Déploiement » avec `render.yaml`, CORS, `VITE_API_URL` et section « Limites connues ».
  - Rien n'est publié (pas de service Render créé, pas de démo en ligne).
- 2026-11-23 (Cline) : **tâche 2 terminée** - Message réveil serveur.
  - Build Vite : succès ( `dist/` généré).
  - Tests pytest : 20 tests passent.
  - Commit `0cd8df1` : "Message de réveil du serveur" (2 fichiers modifiés : `web/src/App.jsx`, `web/src/style.css`).
- 2026-11-24 : **correction du réveil serveur** (suite de `0cd8df1`).
  - Seule une réponse 4xx de l'API fait recommencer la vie. Une panne (5xx, réseau, délai de 90 s) garde la partie et propose « Réessayer ».
  - « Réessayer » en cours de partie relance `advance()` avec la décision qui a échoué et les années restantes ; les boutons sont bloqués pendant la tentative ; le message disparaît en cas de succès.
  - « Rejouer cette vie » passe par le même chargement.
  - Bandeau de réveil en couleur d'accent, plus en rouge d'erreur.
  - Validation : 20 tests pytest passent, build Vite OK ; testé dans le navigateur en coupant l'API (en cours d'année, puis après un rechargement de la page).
  - Pas testé dans le navigateur : le cas 4xx (sauvegarde illisible) et le délai de 90 s.
  - Prochaine étape : étape 3b, publication de la démo sur Render (à valider).

- 2026-11-24 : tests de `_amount` (`tests/test_amount.py`, 3 tests). Délégation Cline en échec (`cline_timeout`, aucun fichier écrit, branche abandonnée), tests écrits par Claude. 46 tests pytest passent. `tests/test_amortize.py` reste non commité.
- 2026-11-24 : nouvel essai Cline sur la même tâche : réussi en 12 s (3 tests corrects, branche abandonnée car doublon). Le délai précédent n'était pas reproductible. Dans `--verify`, écrire `.venv\Scripts\python.exe` avec des barres obliques inverses (la commande tourne dans cmd.exe).
- 2026-11-24 : graphique du patrimoine (`9249450`) en bas à gauche pendant la partie et dans le miroir : composition empilée, points de décision, traits d'événements par famille, ligne du montant de départ, infobulle par année. Pas encore vu avec la nouvelle API (relancer uvicorn avec `--reload`).
- 2026-11-24, branche `avance-economie` (version avancée, morceau 1, voir la note vault) : 1a (`ad8c677`) expose par année l'économie rejouée (`economy`) et les chocs (`shocks`) dans `history` et l'API, test des patrimoines de référence par graine (65 tests) ; 1b panneau « Économie de votre vie » replié par défaut sous le graphique du patrimoine (5 petits graphiques en barres alignés sur l'âge, événements, infobulles), vérifié dans le navigateur. Prochaine étape : 1c (décomposition de la variation du patrimoine).
- 2026-11-24 : deux niveaux dans un seul jeu (branche `avance-economie`) : choix « Découverte » ou « Avancé » sur l'accueil. Le moteur est commun ; le niveau ne change que l'affichage (Avancé = panneau « Économie », ouvert). Niveau gardé dans la sauvegarde et dans l'URL (`niveau=avance`). Le jeu de base est figé par le tag `v1-decouverte` (sur `main`, `a715d81`).
- 2026-11-24 : correctif sur `main` (`47a4fef`) : abandonner une vie tire une nouvelle graine (fusionné dans `avance-economie`). 1c fait : chaque année de `history` a un `breakdown` (décisions, événement, bourse, immobilier, intérêts de l'épargne, reste = revenus, dépenses, dettes, entreprise), mesuré sans changer le moteur (test : la somme des parts = variation du patrimoine ; patrimoines de référence inchangés ; 68 tests). Panneau « L'économie de votre vie » simplifié (tableau « Ce qui a fait bouger votre patrimoine », à cet âge et depuis le début ; 5 petits graphiques avec une phrase d'explication chacun) ; graphiques plus lisibles en jeu (largeur `W=420`, texte plus grand). Vérifié dans le navigateur.

<!-- delegation-kit:start -->
## Delegation setup for this project (jeu-1m, "Et si… ?")

Stack: Python simulation engine (FastAPI) + React front end. Follow the global delegation policy.
First time only: read pyproject/requirements and package.json, then correct the commands and globs below to the real ones.

This project has its own `.venv` and `node_modules` inside the project folder, so EVERY delegation here uses `--isolation branch` (a worktree would lack them and Cline would get stuck).

Verification commands (adjust if different):
- Backend: `.venv\Scripts\python.exe -m pytest -q` (use the project's venv interpreter, not the system `python`)
- Frontend: `npm run build` (add `npm test` if tests exist)

Good candidates for Cline / simple-executor:
- unit tests for existing engine functions (`--allow "tests/*.py"` or the real tests folder)
- hand-written game events as data entries, following an existing example event
- UI strings / English translations (`--allow` the i18n files only)
- small, presentational React components with a given props interface

Keep for yourself (Claude): simulation engine design, balance issues (Hong Kong, Brazil-Mexico), event-engine logic, API contracts between FastAPI and React, deployment on Render.
<!-- delegation-kit:end -->
