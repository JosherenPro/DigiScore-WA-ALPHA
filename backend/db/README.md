# Backend data — DigiScore-WA

Identifiants **anglais**. Notes / `COMMENT ON` **français**. Codes métier (actif, gele, N1…) inchangés pour le moteur et l’API.

## Contenu A–Z (vérifié)

| Bloc | Tables | Couvert |
|------|--------|---------|
| Référentiel | `agency` (shared/split), `credit_product` (seuil caution, exceptionnel), `app_user` | oui |
| Membre + compte | `member.external_code`, `account`, index lookup | oui |
| Historique | `account_movement` (LIMIT), `savings_snapshot`, `past_credit`, `incident`, `member_guarantee` | oui |
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

CSV gitignorés. Relance COPY évitée via table `seed_meta` (`volume_loaded`). Reset : `docker compose down -v`.

Voir `NAMING.md` et `docs/mapping_si.md`.
