-- Idempotent : part assurance du tableau d'amortissement (M5, B12/B13).
-- Applique par Compose (docker-entrypoint-initdb.d) ou manuellement :
--   docker exec -i alpha-postgres-1 psql -U digiscore -d digiscore < backend/db/seed/06_assurance_alter.sql

ALTER TABLE amortization_line ADD COLUMN IF NOT EXISTS insurance_amount NUMERIC(14, 0) NOT NULL DEFAULT 0;
COMMENT ON COLUMN amortization_line.insurance_amount IS 'Cotisation assurance mensuelle (B12, constante, assise sur le capital initial).';
COMMENT ON COLUMN amortization_line.installment_amount IS 'Mensualite totale payee (B13 = echeance + assurance).';
