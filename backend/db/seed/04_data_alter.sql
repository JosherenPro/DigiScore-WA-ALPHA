-- Idempotent : dates PAR / snapshot / tresorerie + cahier autres IF (pas mobile money).
-- python backend/db/seed/migrate_data.py

ALTER TABLE savings_snapshot ADD COLUMN IF NOT EXISTS as_of DATE;
UPDATE savings_snapshot SET as_of = DATE '2026-09-13' WHERE as_of IS NULL;
ALTER TABLE savings_snapshot ALTER COLUMN as_of SET DEFAULT DATE '2026-09-13';
CREATE UNIQUE INDEX IF NOT EXISTS uq_savings_snapshot_account_asof ON savings_snapshot (account_id, as_of);

ALTER TABLE monthly_cashflow ADD COLUMN IF NOT EXISTS period_month DATE;

ALTER TABLE outstanding_loan ADD COLUMN IF NOT EXISTS disbursed_on DATE;
ALTER TABLE outstanding_loan ADD COLUMN IF NOT EXISTS due_on DATE;
ALTER TABLE outstanding_loan ADD COLUMN IF NOT EXISTS observed_on DATE;

CREATE TABLE IF NOT EXISTS financial_institution (
    id      SERIAL PRIMARY KEY,
    code    VARCHAR(30) UNIQUE NOT NULL,
    name    VARCHAR(120) NOT NULL,
    city    VARCHAR(80) NOT NULL DEFAULT 'Lome',
    kind    VARCHAR(20) NOT NULL
            CHECK (kind IN ('coopec', 'banque', 'microfinance'))
);

INSERT INTO financial_institution (code, name, city, kind) VALUES
    ('IF-COOPEC-KPA', 'COOPEC Kpalime Union', 'Kpalime', 'coopec'),
    ('IF-COOPEC-SOK', 'COOPEC Sokode', 'Sokode', 'coopec'),
    ('IF-BTCI', 'BTCI Lome', 'Lome', 'banque'),
    ('IF-UTB', 'UTB', 'Lome', 'banque'),
    ('IF-WAGES', 'WAGES', 'Lome', 'microfinance')
ON CONFLICT (code) DO NOTHING;

ALTER TABLE past_credit ADD COLUMN IF NOT EXISTS institution_id INT REFERENCES financial_institution (id);

CREATE TABLE IF NOT EXISTS external_account (
    id               SERIAL PRIMARY KEY,
    member_id        INT NOT NULL REFERENCES member (id) ON DELETE CASCADE,
    institution_id   INT NOT NULL REFERENCES financial_institution (id),
    account_no_mask  VARCHAR(40) NOT NULL,
    opened_on        DATE NOT NULL,
    status           VARCHAR(20) NOT NULL DEFAULT 'actif'
                     CHECK (status IN ('actif', 'gele', 'cloture')),
    current_balance  NUMERIC(14, 0) NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_ext_account_member ON external_account (member_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_ext_account_mask ON external_account (account_no_mask);

CREATE TABLE IF NOT EXISTS external_account_movement (
    id              SERIAL PRIMARY KEY,
    account_id      INT NOT NULL REFERENCES external_account (id) ON DELETE CASCADE,
    moved_on        DATE NOT NULL,
    movement_type   VARCHAR(20) NOT NULL CHECK (movement_type IN ('depot', 'retrait', 'interet')),
    amount          NUMERIC(14, 0) NOT NULL,
    label           VARCHAR(160)
);

CREATE INDEX IF NOT EXISTS idx_ext_mvt_account_date ON external_account_movement (account_id, moved_on DESC);

CREATE TABLE IF NOT EXISTS external_savings_snapshot (
    id              SERIAL PRIMARY KEY,
    account_id      INT NOT NULL REFERENCES external_account (id) ON DELETE CASCADE,
    as_of           DATE NOT NULL,
    avg_balance_3m  NUMERIC(14, 0) NOT NULL DEFAULT 0,
    avg_balance_6m  NUMERIC(14, 0) NOT NULL DEFAULT 0,
    avg_balance_12m NUMERIC(14, 0) NOT NULL DEFAULT 0,
    UNIQUE (account_id, as_of)
);

UPDATE monthly_cashflow
SET period_month = make_date(2025, GREATEST(LEAST(month_no, 12), 1), 1)
WHERE period_month IS NULL AND month_no BETWEEN 1 AND 12;

UPDATE outstanding_loan
SET disbursed_on = COALESCE(disbursed_on, DATE '2025-01-01'),
    due_on = COALESCE(due_on, DATE '2025-11-01'),
    observed_on = COALESCE(observed_on, DATE '2026-09-13')
WHERE disbursed_on IS NULL OR due_on IS NULL OR observed_on IS NULL;

UPDATE past_credit pc
SET institution_id = fi.id
FROM financial_institution fi
WHERE pc.member_id = 12 AND pc.source = 'externe' AND fi.code = 'IF-BTCI'
  AND pc.institution_id IS NULL;

INSERT INTO external_account (member_id, institution_id, account_no_mask, opened_on, status, current_balance)
SELECT 12, fi.id, 'EXT-TCI-0000012', DATE '2024-03-01', 'actif', 95000
FROM financial_institution fi
WHERE fi.code = 'IF-BTCI'
  AND NOT EXISTS (SELECT 1 FROM external_account WHERE account_no_mask = 'EXT-TCI-0000012');

INSERT INTO external_account_movement (account_id, moved_on, movement_type, amount, label)
SELECT a.id, v.moved_on, v.movement_type, v.amount, v.label
FROM external_account a
JOIN (VALUES
    (DATE '2026-08-02', 'depot', 25000, 'Depot salaire BTCI Extern'),
    (DATE '2026-07-02', 'depot', 24000, 'Depot salaire BTCI Extern 07'),
    (DATE '2026-06-02', 'retrait', 8000, 'Retrait BTCI Extern'),
    (DATE '2025-12-15', 'depot', 30000, 'Depot fin annee BTCI')
) AS v(moved_on, movement_type, amount, label) ON TRUE
WHERE a.account_no_mask = 'EXT-TCI-0000012'
  AND NOT EXISTS (
      SELECT 1 FROM external_account_movement e WHERE e.account_id = a.id
  );

INSERT INTO external_savings_snapshot (account_id, as_of, avg_balance_3m, avg_balance_6m, avg_balance_12m)
SELECT a.id, DATE '2026-09-13', 90000, 85000, 70000
FROM external_account a
WHERE a.account_no_mask = 'EXT-TCI-0000012'
  AND NOT EXISTS (
      SELECT 1 FROM external_savings_snapshot s WHERE s.account_id = a.id AND s.as_of = DATE '2026-09-13'
  );

INSERT INTO account_movement (account_id, moved_on, movement_type, amount, label)
SELECT 1,
       DATE '2024-01-08' + (g * 21),
       CASE WHEN g % 11 = 0 THEN 'interet' WHEN g % 6 = 0 THEN 'retrait' ELSE 'depot' END,
       28000 + g * 1730,
       'Livret Mensah dense #' || g
FROM generate_series(0, 39) AS g
WHERE NOT EXISTS (
    SELECT 1 FROM account_movement WHERE account_id = 1 AND label LIKE 'Livret Mensah dense #%'
);

INSERT INTO account_movement (account_id, moved_on, movement_type, amount, label)
SELECT 5,
       DATE '2023-02-10' + (g * 28),
       CASE WHEN g % 10 = 0 THEN 'interet' WHEN g % 7 = 0 THEN 'retrait' ELSE 'depot' END,
       41000 + g * 2210,
       'Atelier Agbeko dense #' || g
FROM generate_series(0, 35) AS g
WHERE NOT EXISTS (
    SELECT 1 FROM account_movement WHERE account_id = 5 AND label LIKE 'Atelier Agbeko dense #%'
);

INSERT INTO account_movement (account_id, moved_on, movement_type, amount, label)
SELECT 9,
       DATE '2022-03-04' + (g * 18),
       CASE WHEN g % 12 = 0 THEN 'interet' WHEN g % 5 = 0 THEN 'retrait' ELSE 'depot' END,
       95000 + g * 4500,
       'Entrepot Gbeglo dense #' || g
FROM generate_series(0, 47) AS g
WHERE NOT EXISTS (
    SELECT 1 FROM account_movement WHERE account_id = 9 AND label LIKE 'Entrepot Gbeglo dense #%'
);
