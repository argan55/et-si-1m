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
