-- Idempotent : snapshots de simulation de resilience (ML consultatif, phase 3).
-- Applique par Compose (docker-entrypoint-initdb.d) ou manuellement :
--   docker exec -i alpha-postgres-1 psql -U digiscore -d digiscore < backend/db/seed/05_ml_alter.sql

CREATE TABLE IF NOT EXISTS resilience_simulation (
    id                    SERIAL PRIMARY KEY,
    application_id        INT NOT NULL REFERENCES credit_application (id) ON DELETE CASCADE,
    scenario              VARCHAR(60) NOT NULL,
    requested_amount      NUMERIC(14, 0) NOT NULL,
    term_months           INT NOT NULL,
    horizon_months        INT NOT NULL,
    iterations            INT NOT NULL,
    random_seed           INT NOT NULL,
    model_version         VARCHAR(40) NOT NULL,
    incident_probability  NUMERIC(6, 5) NOT NULL,
    critical_month        INT,
    result_json           JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by            INT REFERENCES app_user (id),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resilience_application
    ON resilience_simulation (application_id, created_at DESC);
