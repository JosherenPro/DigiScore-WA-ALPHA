# Preuve perf 1M+ — index et EXPLAIN

Lookups métier via index, jamais scan de table.

| Requête | Index | Attendu |
|---------|-------|---------|
| `member.external_code = ?` | `idx_member_external_code` (UNIQUE) | Index Scan |
| `member(last_name, first_name)` | `idx_member_name` | Index / Bitmap |
| `account.account_no = ?` | `idx_account_no` (UNIQUE) | Index Scan |
| `account_movement(account_id, moved_on DESC)` | `idx_movement_account_date` | Index + LIMIT |
| `past_credit.member_id` | `idx_past_credit_member` | Index Scan |
| `credit_application.status` | `idx_application_status` | Files chef/CIC |

```sql
EXPLAIN ANALYZE SELECT id, last_name, first_name FROM member WHERE external_code = 'MEM-001';
EXPLAIN ANALYZE SELECT id FROM account WHERE account_no = 'CPT-001';
EXPLAIN ANALYZE
  SELECT moved_on, movement_type, amount
  FROM account_movement
  WHERE account_id = 1
  ORDER BY moved_on DESC
  LIMIT 20;
```

Volumétrie (hors docker init) :

```bash
python backend/db/seed/generate_volume_csv.py   # 120 000 membres + historiques
python backend/db/seed/load_volume_csv.py       # COPY dans Postgres
```

Agrégats épargne : `savings_snapshot` — le backend ne charge pas tout l’historique brut.
