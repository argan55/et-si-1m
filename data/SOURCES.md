# Sources des données

Chaque nombre utilisé par le moteur vient d'un fichier de ce dossier. La source de chaque champ est indiquée à côté de lui (clé `sources` des fichiers JSON). Ce document résume les sources et liste les valeurs qui restent des estimations.

## `market_history.csv` : historique annuel 2002-2025, Canada et Brésil

Une ligne par pays et par année. Chaque année de jeu rejoue **une année réelle complète** du pays (bootstrap conjoint) : bourse, inflation, taux, change et immobilier bougent ensemble, comme dans la réalité.

| Colonne | Définition | Source |
|---|---|---|
| `stocks_real` | Rendement réel des actions locales, dividendes compris, de décembre à décembre | MSCI Canada et MSCI Brazil, *Gross Total Return* en monnaie locale (API publique MSCI, codes 912400 et 907600) |
| `inflation` | Inflation de décembre à décembre | Statistique Canada, IPC (vecteur v41690973) ; IBGE/BCB, IPCA mensuel (SGS 433) |
| `cash_real` | Rendement réel de l'épargne liquide (taux court moyen de l'année) | OCDE via FRED : IR3TIB01CAA156N (Canada, 3 mois interbancaire), IRSTCI01BRA156N (Brésil, taux au jour le jour ≈ Selic/CDI) |
| `fx_real` | Variation réelle du dollar US en monnaie locale (> 0 : le dollar coûte plus cher) | FRED EXCAUS / EXBZUS (décembre), IPC américain FRED CPIAUCSL |
| `home_real` | Variation réelle des prix résidentiels, T4 sur T4 | BRI via FRED : QCAR628BIS, QBRR628BIS |

**Pourquoi 2002-2025** : c'est la fenêtre commune aux deux pays. MSCI ne fournit pas de niveaux mensuels avant décembre 2000, et l'indice immobilier de la BRI pour le Brésil commence en 2001. La fenêtre est la même pour les deux pays, pour ne pas fausser la comparaison.

**Correction** : la série MSCI Brazil en BRL change d'échelle d'août 2011 à janvier 2012. Pour 2011 et 2012, le niveau est reconstruit à partir de la version en USD multipliée par le cours PTAX de fin d'année (Banco Central do Brasil, SGS 1).

Pour régénérer le fichier : `python tools/build_market_history.py <dossier>`, à partir des séries brutes téléchargées (la liste est en tête du script).

## `countries.json`, `rules.json`, `events.json`

Chaque champ a sa source dans la clé `sources` du fichier. Principales références :

- **Banque mondiale** : PPA de la consommation privée, espérance de vie, Gini, fécondité.
- **Statistique Canada** : salaires médians (déclarants T1), part du logement dans les dépenses, couples, voyages.
- **IBGE** : revenu moyen du travail (PNAD Contínua), part du logement (POF), voyages (PNAD Turismo), survie des entreprises.
- **Banco Central do Brasil** : taux du crédit aux familles, taux hypothécaire (SGS 20772), endettement (SGS 29265).
- **Banque du Canada** : taux hypothécaire affiché à 5 ans (V80691335).
- **ACI/CREA**, **FipeZap** : prix des logements, rendement locatif brésilien.
- **Equifax Canada**, **CNC (Peic)** : endettement des ménages.
- **OCDE**, *Regards sur l'éducation 2026* : prime salariale d'une maîtrise.
- **ISDE/Statistique Canada**, **IBGE** : survie des entreprises à 5 ans.

## Valeurs encore estimées (≈)

Je n'ai pas trouvé de source précise pour ces valeurs. Elles sont marquées « ≈ » dans les fichiers :

| Valeur | Pays | Pourquoi |
|---|---|---|
| `pension_ratio` (taux de remplacement de la retraite) | CA, BR | OCDE *Pensions at a Glance* inaccessible aux téléchargements automatisés |
| `salary_growth_real` | CA, BR | Pas de série trouvée pour le Brésil ; ordre de grandeur OCDE pour le Canada |
| `spend_ratio` (part du revenu dépensée) | CA, BR | Règle de jeu calée sur des taux d'épargne de 5 à 10 % |
| `partner_prob` | BR | Pas de chiffre du Censo 2022 trouvé |
| `debt_prob` | CA | Part des ménages avec une dette hors hypothèque non trouvée (Enquête sur la sécurité financière) |
| `debt_rate` | CA | Taux moyen du crédit à la consommation non trouvé |
| `rent_yield` | CA | Rendement locatif brut : source payante (Global Property Guide) |
| `home_costs`, `buy_costs`, `sell_costs` | CA, BR | Taxes foncières, droits de mutation, courtage : ordres de grandeur |
| `study_tuition_usd` | commun | Source secondaire (GoStudyIn citant NCES), pas le rapport *Open Doors* |
| `business_yield` | commun | Règle de jeu |
| `trip_big_usd` | BR | Donnée canadienne appliquée au Brésil en dollars US |

Autres limites connues :
- le taux hypothécaire canadien est le **taux affiché**, qui surestime le taux réellement négocié ;
- les revenus sont **bruts**, puisqu'il n'y a pas de fiscalité en V1.
