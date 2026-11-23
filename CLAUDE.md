# Jeu 1 M$ : « 1 M$, une vie »

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
