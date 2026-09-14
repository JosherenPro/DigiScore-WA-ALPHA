# Guide ML — Backend et BDD

## But et limite

Ce guide traduit les idées de ML en tâches pour les responsables backend et
BDD. La référence produit est `doc/ML.md` (document de travail externe au
monorepo). La règle non négociable est : **le ML éclaire, l'humain décide**.

Le moteur `scoring/` reste déterministe. Le ML ne modifie jamais :

- `eligible` ;
- `montant_eligible` ;
- `zone` ;
- `message_code` ;
- les knockouts ;
- le routage Agent → Chef → CIC.

Le point d'entrée du moteur reste donc inchangé :

```text
build_dossier() -> run(DossierInput) -> ScoreResult
```

La couche ML est appelée par le backend **après** le calcul de `ScoreResult`.

## Architecture cible

```text
PostgreSQL
    -> dossier_builder
    -> scoring.run()              décision explicable par règles
    -> advisory_service           enrichissements ML consultatifs
    -> réponse API / persistance
    -> agent, chef ou CIC         décision humaine tracée
```

Créer les nouveaux services backend dans `backend/app/services/`. Ils ne sont
pas importés par `scoring/` :

```text
advisory_service.py       orchestration des capacités et réponses ML
anomaly_service.py        détection d'incohérences
resilience_service.py     simulations de scénarios
early_warning_service.py  alertes portefeuille chef/CIC
```

## Phase 1 — Capabilities

Le backend expose les modules disponibles afin que le front puisse masquer les
écrans non prêts, sans casser le parcours par règles.

### Endpoint

```text
GET /capabilities
```

Réponse initiale recommandée :

```json
{
  "ml_scorecard": false,
  "anomalies": true,
  "simulation": true,
  "early_warning": false,
  "model_version": null
}
```

Le backend définit ces valeurs ; le front ne les déduit jamais lui-même. Une
capacité à `false` signifie « composant masqué », pas « résultat négatif ».

## Phase 2 — Anomalies consultatives

### Endpoint

```text
GET /demandes/{demande_id}/anomalies
```

Rôles autorisés : `agent`, `chef`, `cic`. Les anomalies sont consultatives et
ne changent aucune donnée de la demande.

### Contrat de réponse

```json
{
  "model_version": "anomaly-rules-v1",
  "anomalies": [
    {
      "feature": "ca",
      "value": 5600000,
      "reference_value": 1000000,
      "z_score": 4.6,
      "severity": "a_verifier",
      "message": "Chiffre d'affaires déclaré inhabituel pour ce profil."
    }
  ]
}
```

`severity` ne peut être que `a_verifier` dans le MVP. Aucun statut rouge, aucun
blocage automatique. Le backend calcule les features depuis le dossier déjà
assemblé ; il ne duplique pas les formules CAF/RCSD du package `scoring/`.

### BDD

Pour le MVP, la réponse peut être calculée à la demande et non persistée. Si
une persistance est nécessaire, créer une table additive :

```text
advisory_anomaly
  id
  application_id       FK -> credit_application.id
  model_version
  feature
  value
  reference_value
  z_score
  severity
  message
  created_at
```

Ne jamais écrire ces anomalies dans `score_result` : elles ne font pas partie
du contrat `ScoreResult`.

## Phase 3 — Simulateur de résilience

### Endpoints

```text
POST /demandes/{demande_id}/simuler
POST /demandes/{demande_id}/simulation/enregistrer
```

La simulation ne remplace ni plafond ni décision. Elle utilise le dossier
courant, puis applique un choc explicite au scénario demandé :

```json
{
  "scenario": "mauvaise_recolte",
  "montant": 2000000,
  "duree_mois": 18,
  "horizon_mois": 18,
  "iterations": 1000
}
```

La réponse doit être explicable et reproductible :

```json
{
  "scenario": "mauvaise_recolte",
  "model_version": "resilience-v1",
  "seed": 42,
  "p_incident": 0.27,
  "p10": [0, 0, 0],
  "p50": [120000, 80000, 50000],
  "p90": [240000, 190000, 140000],
  "mois_critique": 8,
  "explication": ["27 % des simulations ne couvrent pas l'échéance du mois 8."]
}
```

`seed`, `model_version`, paramètres et résultat doivent être enregistrés au
moment du snapshot. Cela permet au CIC de rejouer le même scénario.

### BDD

Créer une table additive :

```text
resilience_simulation
  id
  application_id       FK -> credit_application.id
  scenario
  requested_amount
  term_months
  horizon_months
  iterations
  random_seed
  model_version
  incident_probability
  critical_month
  result_json
  created_by            FK -> app_user.id
  created_at
```

Les tableaux P10/P50/P90 vont dans `result_json`. Ne pas créer une colonne par
mois : l'horizon de simulation peut varier.

## Phase 4 — Scorecard adaptatif en shadow mode

Ne pas entraîner un modèle de défaut sur les 120 000 profils synthétiques pour
prendre une décision crédit. Ils servent à la volumétrie et à la démonstration,
pas à valider le risque réel.

Quand des données historiques labellisées seront disponibles, le backend peut
retourner un enrichissement distinct :

```json
{
  "model_version": "risk-logistic-v1",
  "mode": "shadow",
  "default_probability": 0.07,
  "weights_learned": {
    "financier": 0.24,
    "capacite": 0.26,
    "historique": 0.22,
    "activite": 0.12,
    "garanties": 0.09,
    "documents": 0.07
  },
  "top_factors": ["RCSD favorable", "Historique sans retard"]
}
```

Le score règles et les poids métier restent affichés en parallèle. Le backend
ne remplace pas les six poids de `scoring/digiscore/scorecard.py` avec des
poids appris.

Avant tout entraînement, la BDD doit fournir, pour chaque demande historique :

- les variables connues à la date de décision ;
- la date de décision et de décaissement ;
- une cible future définie par le métier (`PAR30`, `PAR90`, impayé ou défaut) ;
- des données anonymisées ou pseudonymisées ;
- une séparation temporelle entraînement/validation/test.

Les variables postérieures à la décision sont interdites comme features : ce
sont des fuites de données.

## Phase 5 — Early warning portefeuille

### Endpoint et droits

```text
GET /portefeuille/alertes?limit=20
```

Rôles autorisés : `chef`, `cic` uniquement. Répondre `403` à l'agent.

Réponse minimale :

```json
{
  "model_version": "early-warning-v1",
  "items": [
    {
      "application_id": 42,
      "member_code": "MEM-042",
      "p_par30_90j": 0.31,
      "exposure": 850000,
      "signals": ["Retard récent", "Baisse des dépôts"],
      "explication": "Risque consultatif : revue recommandée."
    }
  ]
}
```

L'alerte est une file de revue. Elle ne change pas le statut d'un crédit.

## Règles de migration et de coordination

- Data ajoute les tables au schéma et fournit les seeds correspondants.
- Backend n'invente pas de table ; il consomme le schéma validé.
- Toutes les tables ML sont additives : aucune modification destructive de
  `credit_application`, `score_result` ou `financial_ratio`.
- Tout endpoint est ajouté aux schémas Pydantic et à `docs/openapi.json`.
- Tout nouveau champ transmis au front est versionné, documenté et accompagné
  d'un exemple de réponse.
- Le frontend ne calcule pas de probabilité, z-score ou simulation.
- Le package `scoring/` ne fait ni SQL, ni HTTP, ni lecture de modèle ML.

## Tests d'acceptation

Avant merge, vérifier :

1. Un `POST /demandes/{id}/analyser` donne le même `ScoreResult` avec ou sans
   capacités ML actives.
2. Une anomalie apparaît dans sa route dédiée sans changer l'éligibilité, le
   plafond, les knockouts ou la zone.
3. Une simulation enregistrée est relisible et reproductible avec son `seed`.
4. Un agent obtient `403` sur `/portefeuille/alertes`.
5. Chaque réponse ML porte un `model_version` et une `explication` lisible.
6. Les migrations et seeds démarrent avec `docker compose up -d`.

## Ordre de livraison

1. `GET /capabilities` ;
2. anomalies consultatives ;
3. simulateur de résilience et snapshots ;
4. early warning ;
5. scorecard adaptatif uniquement après réception de vraies cibles historiques.

Branches recommandées :

```text
feat/ml-capabilities-anomalies
feat/ml-resilience-simulator
feat/ml-early-warning
feat/ml-scorecard-shadow
```
