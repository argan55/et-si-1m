# Sources des données

Chaque nombre utilisé par le moteur vient d'un fichier de ce dossier. La source de chaque champ est indiquée à côté de lui (clé `sources` des fichiers JSON). Ce document résume les sources et liste les valeurs qui restent des estimations.

## `market_history.csv` : historique annuel par pays

Une ligne par pays et par année. Chaque année de jeu rejoue **une année réelle complète** du pays (bootstrap conjoint) : bourse, inflation, taux, change et immobilier bougent ensemble, comme dans la réalité.

| Colonne | Définition | Sources |
|---|---|---|
| `stocks_real` | Rendement réel des actions locales, dividendes compris, de décembre à décembre | MSCI *Gross Total Return* en monnaie locale (API publique MSCI) : Canada 912400, Brazil 907600, France 925000, Hong Kong 934400, USA 984000, Mexico 848400 |
| `inflation` | Inflation de décembre à décembre | Statistique Canada, IPC (v41690973) ; IBGE/BCB, IPCA (SGS 433) ; Eurostat, IPCH France (FRED CP0000FRM086NEST) ; BLS, CPI (FRED CPIAUCSL). **Hong Kong et Mexique : moyenne annuelle** (Banque mondiale, FP.CPI.TOTL.ZG), faute de série mensuelle à jour sans clé d'API |
| `cash_real` | Rendement réel de l'épargne liquide (taux court moyen de l'année) | OCDE via FRED : 3 mois interbancaire (Canada, France, Mexique), taux au jour le jour (Brésil, ≈ Selic/CDI) ; bons du Trésor à 3 mois (États-Unis, TB3MS) ; HIBOR 3 mois (HKMA) |
| `fx_real` | Variation réelle du dollar US en monnaie locale (> 0 : le dollar coûte plus cher) | FRED EXCAUS, EXBZUS, EXUSEU, EXHKUS, EXMXUS (décembre) ; IPC américain (CPIAUCSL). États-Unis : 0 par définition |
| `home_real` | Variation réelle des prix résidentiels, T4 sur T4 | BRI via FRED : QCAR628BIS, QBRR628BIS, QFRR628BIS, QHKR628BIS, QUSR628BIS, QMXR628BIS |

**Fenêtre 2002-2025**, la même pour tous les pays sauf le Mexique : MSCI ne fournit pas de niveaux mensuels avant décembre 2000, et l'indice immobilier de la BRI pour le Brésil commence en 2001.

**Mexique : 2006-2025** (20 ans), parce que l'indice immobilier de la BRI pour le Mexique ne commence qu'en 2005.

**Correction de 2011-2012** : les séries MSCI en monnaie locale du Brésil et du Mexique changent d'échelle d'août 2011 à janvier 2012. Pour ces deux années, le niveau est reconstruit à partir de la version en USD multipliée par le change de fin d'année : PTAX (Banco Central do Brasil, SGS 1) et FRED DEXMXUS.

Pour régénérer le fichier : `python tools/build_market_history.py <dossier>`, à partir des séries brutes téléchargées (la liste est en tête du script).

## `countries.json`, `rules.json`, `events.json`

Chaque champ a sa source dans la clé `sources` du fichier. Principales références :

- **Banque mondiale** : PPA de la consommation privée, espérance de vie, Gini, fécondité, change.
- **Instituts statistiques** : salaires (Statistique Canada, IBGE, INSEE, C&SD, BLS, INEGI), part du logement, couples, voyages.
- **Banques centrales** : taux hypothécaires et taux du crédit (Banque du Canada, Banco Central do Brasil, Banque de France, HKMA, Banco de México), endettement.
- **Prix des logements** : ACI/CREA, FipeZap, RVD, NAR, SHF.
- **Freddie Mac** (PMMS) : taux hypothécaire américain.
- **Equifax Canada**, **CNC (Peic)** : endettement des ménages.
- **OCDE**, *Regards sur l'éducation 2026* : prime salariale d'une maîtrise.
- **ISDE/Statistique Canada**, **IBGE**, **BLS** : survie des entreprises à 5 ans.

## Valeurs encore estimées (≈)

Je n'ai pas trouvé de source précise pour ces valeurs. Elles sont marquées « ≈ » dans les fichiers :

| Valeur | Pays | Pourquoi |
|---|---|---|
| `pension_ratio` (taux de remplacement de la retraite) | tous sauf HK | OCDE *Pensions at a Glance* inaccessible aux téléchargements automatisés |
| `salary_growth_real` | tous | Ordre de grandeur OCDE pour CA, FR, US ; rien trouvé pour BR, HK, MX |
| `spend_ratio` (part du revenu dépensée) | tous | Règle de jeu calée sur des taux d'épargne de 5 à 10 % |
| `rent_share` | FR, HK, MX | Enquêtes budgets (INSEE BdF, C&SD HES, INEGI ENIGH) non consultées |
| `partner_prob` | BR, FR, HK, US, MX | Seul le Canada a un chiffre trouvé |
| `debt_prob`, `debt_to_salary`, `debt_rate` | CA (en partie), FR, HK, US, MX | Seul le Brésil est sourcé en entier |
| `rent_yield` | CA, FR, HK, US, MX | Source payante (Global Property Guide) ; seul le Brésil est sourcé |
| `home_price` | FR | Les médianes des Notaires ne sont publiées qu'en image |
| `mortgage_rate` | HK | Dérivé du HIBOR + marge usuelle, pas de moyenne officielle publiée |
| `home_costs`, `buy_costs`, `sell_costs` | tous | Taxes foncières, droits de mutation, courtage : ordres de grandeur |
| `trip_small` | FR, HK, US, MX | Seuls le Canada et le Brésil sont sourcés |
| `business_survival_5y` | FR, HK, MX | US via une source secondaire ; MX extrapolé depuis la survie à 2 ans |
| `retirement_age` | FR | 64 ans (réforme 2023), dont l'application a été débattue |
| `study_tuition_usd` | commun | Source secondaire (GoStudyIn citant NCES), pas le rapport *Open Doors* |
| `business_yield` | commun | Règle de jeu |
| `trip_big_usd` | tous sauf CA | Donnée canadienne appliquée aux autres pays en dollars US |

Autres limites connues :
- les revenus sont **bruts**, puisqu'il n'y a pas de fiscalité en V1 ;
- le Gini de Hong Kong (0,473) est celui du C&SD après impôts et transferts sociaux (recensement 2016), sur le revenu des ménages et non par personne : il reste un peu plus élevé que s'il était calculé comme celui de la Banque mondiale.

## Retraite à Hong Kong

Le moteur représente la retraite par un seul chiffre : la pension vaut `pension_ratio` × le dernier train de vie. Pour Hong Kong, ce chiffre vient de l'OCDE et résume le régime obligatoire :

| Élément | Valeur | Source | Dans le moteur |
|---|---|---|---|
| Taux de remplacement brut, régimes obligatoires, salaire moyen | 41,5 % (homme), 39,0 % (femme) | OCDE, *Pensions at a Glance Asia/Pacific 2024* | `pension_ratio` = 0,415 |
| MPF : cotisations obligatoires | 5 % salarié + 5 % employeur | [MPFA, Mandatory contributions](https://www.mpfa.org.hk/en/mpf-system/mandatory-contributions) | inclus dans le taux OCDE |
| MPF : revenu pris en compte | de 7 100 à 30 000 HK$/mois (85 200 à 360 000 HK$/an) ; retrait à 65 ans | MPFA | inclus dans le taux OCDE |
| Old Age Allowance (OAA) | 1 640 HK$/mois dès 70 ans, sans condition de ressources (1er février 2025) | [SWD, Level of Allowance](https://swd.gov.hk/en/pubsvc/socsecu/ssallowance/ssa_amt/ssa_amt_all) | non représentée (≈ 8 % du salaire médian) |
| Old Age Living Allowance (OALA) | 4 250 HK$/mois dès 65 ans, si le patrimoine d'une personne seule est sous 406 000 HK$ (1er février 2025) | [SWD, OALA](https://swd.gov.hk/oala/index_e.html) | non représentée (condition de patrimoine) |

Limites : le taux OCDE suppose une carrière complète et ne dépend pas du salaire dans le moteur. Comme le revenu cotisable du MPF est plafonné, la vraie pension des hauts salaires est plus faible (l'OCDE 2022 donnait 26,8 % à 2 fois le salaire moyen).
