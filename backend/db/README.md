# Backend data — DigiScore-WA

Identifiants **anglais**. Notes / `COMMENT ON` **français**. Codes métier (actif, gele, N1…) inchangés pour le moteur et l’API.

## Contenu A–Z (vérifié)

| Bloc | Tables | Couvert |
|------|--------|---------|
| Référentiel | `agency` (shared/split), `credit_product` (seuil caution, exceptionnel), `app_user` | oui |
| Membre + compte | `member.external_code`, `account`, index lookup | oui |
| Historique | `account_movement` (LIMIT), `savings_snapshot`, `past_credit`, `incident`, `member_guarantee`, **`external_account` + `external_account_movement`** (ailleurs, pas mélangé) | oui |
| Collecte A–E | `household`, `activity`, `economic_model`, `market`, `income_expense`, `wealth`, `monthly_cashflow`, `application_guarantee` + N1–N3 | oui |
| BIC / fiscal / pièces | `bic_consent` (+ scan), `bic_report`, `supporting_document` (OCR) | oui |
| Cautions | `guarantor`, `application_guarantor`, `guarantor_review` | oui |
| Score / décision | `score_result`, `amortization_line`, `decision`, `audit_log` | oui |
| Sidecar | `digiscore_member_map` ADD-only | oui |
| M6 / M7 | `outstanding_loan`, `portfolio_followup` (V1–V3), `par_indicator`, `recovery_case`, `recovery_action` | oui (structure ; moteur live OUT) |

**Hors BDD volontaire (OUT 72 h)** : connecteurs live core/BIC/Flooz/SYSCOFOP, ML réel, tontine groupe.

## Démarrer

```bash
docker compose up -d          # schema + 12 profils + db-seed (CSV volume)
LOAD_VOLUME=0 docker compose up -d   # 12 profils seulement
# manuel (depuis la racine du repo) :
python backend/db/seed/generate_volume_csv.py
python backend/db/seed/load_volume_csv.py
```

CSV gitignorés. Relance COPY évitée via `seed_meta.volume_loaded=v2`. Volume v1 (marqueur `1`) **ne se recharge pas** tout seul : `docker compose down -v` puis `up` (premier chargement long). Laptop : `VOLUME_MEMBERS=5000`.

Volume **déjà créé** (colonnes dates + autres IF, sans `-v`) :

```bash
python backend/db/seed/migrate_data.py
# ou : docker exec -i digiscore_wa-postgres-1 psql -U digiscore < backend/db/seed/04_data_alter.sql
# le ledger dense 120k unique exige quand même un -v + régénération CSV
```

Auth déjà en base :

```bash
python backend/db/seed/migrate_auth.py
```

Voir `NAMING.md` et `docs/mapping_si.md`. Dates PAR / point-in-time : [docs/PLAN_ROBUSTESSE_DONNEES.md](../../docs/PLAN_ROBUSTESSE_DONNEES.md) (pas d’entraînement sur le volume).
