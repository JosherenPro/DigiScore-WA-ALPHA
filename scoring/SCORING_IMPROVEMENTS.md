# Améliorations du moteur de scoring

## Objectif

Le moteur reste déterministe pour les décisions MVP. Les knockouts, les seuils
RCSD, le plafond et les messages doivent être auditables et reproductibles.
Le ML n'est pas utilisé pour contourner une règle de sécurité.

## Changements implémentés

### Politique centralisée

`digiscore/policy.py` centralise les paramètres sensibles :

- taux annuel simple du crédit : `1,8 %` ;
- RCSD knockout : `< 1,00` ;
- RCSD confort : `>= 1,50` ;
- seuil documentaire fiscal : `500 000 FCFA` ;
- seuil de voie exceptionnelle : `8 000 000 FCFA` ;
- priorité des messages de knockout.

Le pipeline ne contient plus une longue chaîne de conditions répétant cette
priorité. `select_knockout_message()` sélectionne le premier code présent selon
la politique métier. Les knockouts restent tous conservés dans la réponse pour
l'explicabilité.

### Formule de plafond cohérente

Le service annuel est calculé dans `financials.py` avec le taux de `1,8 %`.
Le plafond RCSD utilise maintenant l'inverse exact de cette formule via
`montant_pour_service()`. L'ancienne approximation `1.1` pouvait produire un
plafond incohérent avec le RCSD affiché.

Le plafond final respecte toujours :

```text
min(plafond produit, capacité épargne/CAF/historique, capacité RCSD)
```

Puis il applique le micro-plafond thin-file, le facteur de zone et un arrondi
inférieur à `10 000 FCFA`.

## Règle d'intégration

Les tests unitaires couvrent le package pur. Un test d'intégration doit aussi
rejouer le chemin réel :

```text
PostgreSQL -> dossier_builder -> run() -> ScoreResult
```

Cette séparation est importante : les fixtures unitaires peuvent être valides
alors que les seeds SQL portent une combinaison différente de CAF, montant,
fiscalité ou garanties. Les cas seed doivent donc être vérifiés avec le
backend, puis synchronisés avec `data/synthetic/cas_attendus.json`.

## ML : trajectoire recommandée

Les 120 000 profils synthétiques sont utiles pour tester la volumétrie, mais ne
constituent pas une base de risque crédit fiable. Ils ne fournissent pas une
cible historique indépendante comme `PAR30`, `PAR90` ou défaut après
décaissement.

La trajectoire proposée est :

1. conserver les règles et knockouts comme décision de référence ;
2. collecter des demandes historiques avec une cible future et la date de
   décision ;
3. entraîner une régression logistique ou un modèle gradient boosting avec
   séparation temporelle et contrôle des fuites ;
4. exécuter le modèle en *shadow mode* et comparer son risque au score métier ;
5. envisager un recalibrage validé par le métier, sans autoriser le modèle à
   lever un knockout.

## Garde-fous ML v2

La scorecard `scorecard-v2` utilise une régression logistique non pondérée. Sa
sortie peut être nommée `probabilite_defaut` dans le cadre du jeu synthétique,
car elle n'est plus déformée par `class_weight="balanced"`. Les seuils du
plafond ML restent indicatifs et devront être recalibrés sur des défauts réels
avant toute utilisation en production.

La recommandation `plafond_ml_recommande` est toujours inférieure ou égale au
plafond règles. Un knockout retourne une recommandation `null`. Le montant ML
ne remplace donc pas RCSD, les garanties, le plafond produit ou le CIC.

Le simulateur de résilience `resilience-v2` applique des aléas indépendants
aux encaissements et décaissements. Son `p_incident` est une fréquence de
simulation reproductible par `seed`, pas une probabilité de défaut crédit.

Les anomalies utilisent une feature logarithmique revenus/épargne. Les
thin-files sont explicitement hors scope de cette détection : ils ne génèrent
pas d'anomalie automatique seulement parce que leur épargne est faible.

## Vérifications

Depuis la racine du dépôt :

```bash
pytest scoring/tests -q
```

Les invariants à conserver sont :

- tout knockout implique `eligible=false` et `montant_eligible=0` ;
- le plafond ne dépasse jamais le plafond produit ;
- une dette existante réduit la capacité RCSD ;
- les frontières de zone `40/41/70/71` restent stables ;
- une demande exceptionnelle est soumise à une décision humaine/CIC.

## ML v3 — nouvelles variables et serving FastAPI

`scorecard-v3` / `anomaly-v3` (`training/train_v3.py`, dataset
`training/dataset_v3.csv` construit depuis Postgres point-in-time à
`applied_at`, label `par30_futur` = `outstanding_loan` impayé J30+ seul).

Nouvelles variables (défaut 0 = compatible v2) :
`has_external`, `ext_epargne_6m/log`, `ext_nb_mouvements_90j`,
`bic_incidents`, `past_impayes`, `max_jours_retard`, `preuves_score` (N1+N2+N3),
`dependance_debouche`, `concurrence`, `signaux_patrimoine`.
`dossier_builder` calcule désormais le vrai `COUNT` 90 j, le snapshot
`as_of <= applied_at`, l'épargne externe et le BIC — plus de proxy `4/1`.

Réserve : volume v2 synthétique déterministe (profil `late` ⇒ passé +
PAR30 liés, `max_jours_retard` poids 0.69, AUC ≈ 1). Pipeline prouvé,
pas un risque réel : **shadow/demo uniquement**, production = historiques
FUCEC réels. Servies par `GET /demandes/{id}/ml/scorecard` et
`/ml/plafond` (`routes_ml.py`, `ML_ENABLED=1`), sans toucher
`eligible/zone/KO` ni `/analyser`.
