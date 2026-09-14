-- Idempotent : socle M6 suivi portefeuille (echeances datees, paiements, visites,
-- signaux, recouvrement, snapshots PAR). Additif uniquement.
--   docker exec -i alpha-postgres-1 psql -U digiscore -d digiscore < backend/db/seed/06_m6_alter.sql

ALTER TABLE amortization_line ADD COLUMN IF NOT EXISTS due_on DATE;

ALTER TABLE outstanding_loan ADD COLUMN IF NOT EXISTS restructured BOOLEAN NOT NULL DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS idx_loan_late ON outstanding_loan (days_late DESC);

CREATE TABLE IF NOT EXISTS loan_payment (
    id                   SERIAL PRIMARY KEY,
    outstanding_loan_id  INT NOT NULL REFERENCES outstanding_loan (id) ON DELETE CASCADE,
    paid_on              DATE NOT NULL,
    amount               NUMERIC(14, 0) NOT NULL,
    kind                 VARCHAR(20) NOT NULL DEFAULT 'echeance'
                         CHECK (kind IN ('echeance', 'anticipe', 'reechelonnement')),
    external_ref         VARCHAR(60)
);
CREATE INDEX IF NOT EXISTS idx_loan_payment_loan ON loan_payment (outstanding_loan_id, paid_on);

ALTER TABLE portfolio_followup ADD COLUMN IF NOT EXISTS signal_code VARCHAR(40);
ALTER TABLE portfolio_followup ADD COLUMN IF NOT EXISTS visit_status VARCHAR(20) NOT NULL DEFAULT 'realisee';
ALTER TABLE portfolio_followup ADD COLUMN IF NOT EXISTS next_on DATE;
ALTER TABLE portfolio_followup ADD COLUMN IF NOT EXISTS action_taken VARCHAR(160);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'portfolio_followup_visit_status_check') THEN
        ALTER TABLE portfolio_followup
            ADD CONSTRAINT portfolio_followup_visit_status_check
            CHECK (visit_status IN ('planifiee', 'realisee', 'manquee'));
    END IF;
END $$;

ALTER TABLE par_indicator ADD COLUMN IF NOT EXISTS par1_pct NUMERIC(6, 2) NOT NULL DEFAULT 0;
ALTER TABLE par_indicator ADD COLUMN IF NOT EXISTS encours_brut NUMERIC(16, 0) NOT NULL DEFAULT 0;
ALTER TABLE par_indicator ADD COLUMN IF NOT EXISTS restructured_amount NUMERIC(16, 0) NOT NULL DEFAULT 0;
ALTER TABLE par_indicator ADD COLUMN IF NOT EXISTS computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

ALTER TABLE recovery_case ADD COLUMN IF NOT EXISTS priority VARCHAR(4);
ALTER TABLE recovery_case ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'ouvert';
ALTER TABLE recovery_case ADD COLUMN IF NOT EXISTS recovered_amount NUMERIC(14, 0) NOT NULL DEFAULT 0;
ALTER TABLE recovery_case ADD COLUMN IF NOT EXISTS last_action_on DATE;
ALTER TABLE recovery_case ADD COLUMN IF NOT EXISTS closed_on DATE;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'recovery_case_status_check') THEN
        ALTER TABLE recovery_case
            ADD CONSTRAINT recovery_case_status_check
            CHECK (status IN ('ouvert', 'clos'));
    END IF;
END $$;

ALTER TABLE recovery_action ADD COLUMN IF NOT EXISTS promise_on DATE;
ALTER TABLE recovery_action ADD COLUMN IF NOT EXISTS promise_kept BOOLEAN;
ALTER TABLE recovery_action ADD COLUMN IF NOT EXISTS amount_recovered NUMERIC(14, 0) NOT NULL DEFAULT 0;
