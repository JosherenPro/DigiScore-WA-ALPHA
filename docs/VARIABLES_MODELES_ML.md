# Variables des modèles ML — état actuel

Document de référence : sur quelles variables les modèles de la couche ML sont
entraînés aujourd'hui, avec quelle cible, et quelles réserves. Le moteur règles
(`digiscore.pipeline.run`) reste la seule décision exposée ; le ML est
consultatif et masqué par défaut (`ML_ENABLED=0`).

| Modèle | Artefact | Entraînement | Données | Algo | Version |
|---|---|---|---|---|---|
| Scorecard v3 (actif) | `scoring/models/scorecard_v3.joblib` | `training/train_v3.py` | `training/dataset_v3.csv` (20 011 demandes, Postgres) | LogReg + StandardScaler | `scorecard-v3` |
| Anomalies v3 | `scoring/models/anomaly_v3.joblib` | `training/train_v3.py` | dossiers label=0 du dataset v3 (max 8 000) | IsolationForest | `anomaly-v3` |
| Scorecard v2 (fallback) | `scoring/models/scorecard_v2.joblib` | `training/train_scorecard.py` | `training/dataset_v1.csv` (20 000 lignes synthétiques) | LogReg + StandardScaler | `scorecard-v2` |
| Anomalies v2 | `scoring/models/anomaly_v2.joblib` | `training/train_anomaly.py` | lignes synthétiques « normales » | IsolationForest | `anomaly-v2` |

## 1. Scorecard v3 — 20 variables

Définies dans `scoring/digiscore/adaptive/scorecard_ml.py` (`FEATURE_NAMES_V3`) :
11 variables v2 + 9 variables v3 (externes, BIC, comportement, preuves, marché).

### Notes du moteur règles (6)

| Variable | Description |
|---|---|
| `note_financier` | Note financière /100 (solvabilité, fonds de roulement, marge, ratios dégradés) |
| `note_capacite` | Note capacité /100 (RCSD, creux de trésorerie, signaux) |
| `note_historique` | Note historique /100 (crédits soldés, impayés, incidents, ancienneté, épargne) |
| `note_activite` | Note activité /100 (saisonnalité, dépendance débouché, érosion CA) |
| `note_garanties` | Note garanties /100 (couverture, cautionnaires) |
| `note_documents` | Note documents /100 (preuves N1–N3, fiscalité, preuves externes) |

### Historique et capacité (5)

| Variable | Description | Source |
|---|---|---|
| `anciennete_mois` | Ancienneté du membre (mois) | `member.joined_on` |
| `rcsd` | Ratio de couverture du service de dette | `financials.compute_all` |
| `epargne_regularite` | `epargne_moy_3m / epargne_moy_6m × 100` | `savings_snapshot` (point-in-time) |
| `incidents_graves` | Nombre d'incidents graves | `incident.severity='grave'` |
| `montant_sur_plafond` | `montant demandé / plafond produit` | `credit_application` + `credit_product` |

### Nouvelles variables v3 (9)

| Variable | Description | Source |
|---|---|---|
| `has_external` | A des crédits hors agence | `credit_application.has_external_credits` |
| `ext_epargne_log` | `log1p(épargne moyenne 6 mois ailleurs)` | `external_savings_snapshot.avg_balance_6m` |
| `bic_incidents` | Max d'incidents BIC | `bic_report.bic_incident_count` |
| `past_impayes` | Nombre de crédits passés impayés | `past_credit.status='impaye'` |
| `max_jours_retard` | Max des jours de retard passés | `past_credit.max_days_late` |
| `preuves_score` | Somme des niveaux de preuve (N1=0, N2=1, N3=2) | `income_expense.income_proof_level` + `expense_proof_level` (0–4) |
| `dependance_debouche` | Dépendance à un seul débouché | `market.single_outlet_dependency` |
| `concurrence` | Nombre de concurrents | `market.competitor_count` |
| `signaux_patrimoine` | Somme des 5 signaux patrimoniaux | `wealth.signal_*` (0–5) |

### Cible (label)

`label_par30_futur` : 1 si le membre a un `outstanding_loan` impayé avec
`days_late >= 30`, sinon 0 (`training/build_dataset_v3.py`, taux ~2,45 %).
`label_defaut` (fallback) ajoute `past_credit.status='impaye'`.

## 2. Anomalies v3 — 10 variables

`ANOMALY_FEATURE_NAMES_V3` (`scoring/digiscore/anomalies.py`) :

| Variable | Description |
|---|---|
| `log_revenus_sur_epargne` | `log1p(CA / épargne 6 mois locale)` |
| `solde_sur_revenu_mensuel` | `solde / (CA / 12)` |
| `patrimoine_sur_fonds_propres` | `actif total / fonds propres` |
| `garanties_sur_demande` | `valeur garanties / montant demandé` |
| `rcsd` | Ratio de couverture (borné 0–10) |
| `mouvements_90j` | Nombre de mouvements agence sur 90 jours |
| `ext_epargne_log` | `log1p(épargne moyenne 6 mois ailleurs)` |
| `bic_incidents` | Incidents BIC |
| `past_impayes` | Crédits passés impayés |
| `preuves_score` | Niveau de preuve cumulé (0–4) |

Entraîné uniquement sur les dossiers **sains** (label=0), 8 000 max ; les
thin-files sont hors scope à l'inférence (`scope_excluded: true`).

## 3. Scorecard v2 — 11 variables

`FEATURE_NAMES` (`scorecard_ml.py`) : les 6 notes métier + `anciennete_mois`,
`rcsd`, `epargne_regularite`, `incidents_graves`, `montant_sur_plafond`.

Données **100 % synthétiques** (`training/generate.py`) : features tirées autour
d'un profil moyen, label probabiliste à partir des coefficients de
`training/ground_truth.json` + bruit `σ = 0,35`. Utilisé seulement si l'artefact
v3 est absent (`predict_scorecard_v3` → fallback `predict_scorecard`).

## 4. Anomalies v2 — 6 variables

Les 6 premières de la liste v3 : `log_revenus_sur_epargne`,
`solde_sur_revenu_mensuel`, `patrimoine_sur_fonds_propres`,
`garanties_sur_demande`, `rcsd`, `mouvements_90j`.

## Composants sans entraînement

| Composant | Nature |
|---|---|
| Résilience (`resilience-v2`) | Monte Carlo déterministe sur la trésorerie (seed + itérations) |
| Early warning (`early-warning-v1`) | Règles SQL sur `outstanding_loan.days_late` + signaux `portfolio_followup` |
| Plafond ML (`credit-limit-advisory-v1`) | Décote du plafond règles selon `probabilite_defaut` (seuils 10/20/35 %) |

## Construction des features au runtime

`backend/app/services/dossier_builder.py` assemble le dossier au format scoring
et calcule les variables point-in-time (épargne `as_of <= applied_at`,
mouvements 90 j, `external_*`, `bic_report`, `past_credit`, signaux `wealth`).
`training/build_dataset_v3.py` refait les mêmes calculs en SQL pour
l'entraînement. Toute variable ajoutée à `DossierInput` doit être coordonnée
entre scoring et backend.

## Réserves connues

- **Fuite dans le label v3** : la requête de `label_par30_futur` n'a **aucun
  filtre de date par rapport à `applied_at`** — elle lit le statut courant du
  membre (`outstanding_loan.status='impaye'`, `past_credit`), pas une issue
  postérieure à la demande. C'est la cause de l'AUC 1.0 et du Brier 4,6e-05.
- **Anomalies v3 saturées** : sur un bon payeur, `anomaly_score` peut valoir
  1.0 ; le composant `sigmoid((z − 3) × 1,5)` sature trop vite.
- **Modèle v2 ancien** : 11 variables, sans les données externes/BIC, mais
  calibré (bin de calibration alignés, Brier ≈ 0,145).
- **Artefacts sklearn 1.7.2** désérialisés en 1.9.1 (warnings d'incompatibilité).
- Le « score ML » `/100` a été supprimé de l'API ; le shadow expose
  `probabilite_defaut` + `niveau_risque` et signale `regles_knockout`.

## Réentraînement

```bash
# v3 : scorecard-v3 + anomaly-v3 (dataset Postgres point-in-time)
python training/build_dataset_v3.py     # régénère training/dataset_v3.csv
python training/train_v3.py

# v2 (synthétique) : dataset puis modèles
python training/generate.py             # training/dataset_v1.csv + ground_truth.json
python training/train_scorecard.py      # scorecard_v2.joblib + métriques
python training/train_anomaly.py        # anomaly_v2.joblib + métadonnées
```

## Références

- Contrats API ML : `docs/GUIDE_ML_BACKEND_DATA.md`
- Bug scoring / moteur : `docs/SYNTHESE_RESPONSABLE_SCORING.md`
- Données v2 (mix 120k, dates, externe) : `docs/DONNEES_RESPONSABLE_MODELE.md`
- Code : `scoring/digiscore/adaptive/scorecard_ml.py`,
  `scoring/digiscore/anomalies.py`, `training/train_v3.py`,
  `training/build_dataset_v3.py`, `backend/app/services/dossier_builder.py`
