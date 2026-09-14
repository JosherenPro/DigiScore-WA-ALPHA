#!/usr/bin/env python3
"""ALTER idempotent + mot de passe demo pour un volume Postgres deja cree."""

from __future__ import annotations

import os

import bcrypt
import psycopg

DSN = os.getenv("DATABASE_URL", "postgresql://digiscore:digiscore@localhost:5432/digiscore")
DEMO = os.getenv("DEMO_PASSWORD", "demo")

STMTS = [
    "ALTER TABLE app_user ADD COLUMN IF NOT EXISTS password_hash VARCHAR(128)",
    "ALTER TABLE score_result ADD COLUMN IF NOT EXISTS engine_version VARCHAR(40)",
    "UPDATE score_result SET engine_version = 'rules-v1' WHERE engine_version IS NULL",
    "ALTER TABLE score_result ALTER COLUMN engine_version SET DEFAULT 'rules-v1'",
    "ALTER TABLE financial_ratio ADD COLUMN IF NOT EXISTS computed_at TIMESTAMPTZ",
    "UPDATE financial_ratio SET computed_at = NOW() WHERE computed_at IS NULL",
    "ALTER TABLE financial_ratio ALTER COLUMN computed_at SET DEFAULT NOW()",
    """
    CREATE TABLE IF NOT EXISTS score_result_history (
        history_id SERIAL PRIMARY KEY,
        archived_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        application_id INT NOT NULL REFERENCES credit_application (id) ON DELETE CASCADE,
        score_total NUMERIC(6, 2) NOT NULL,
        thin_file BOOLEAN NOT NULL DEFAULT FALSE,
        eligible BOOLEAN NOT NULL DEFAULT FALSE,
        requested_amount NUMERIC(14, 0) NOT NULL,
        eligible_amount NUMERIC(14, 0) NOT NULL,
        suggested_max_amount NUMERIC(14, 0),
        message_code VARCHAR(40) NOT NULL,
        message_text TEXT NOT NULL,
        criteria JSONB NOT NULL DEFAULT '[]',
        knockouts JSONB NOT NULL DEFAULT '[]',
        explanation JSONB NOT NULL DEFAULT '[]',
        engine_version VARCHAR(40) NOT NULL DEFAULT 'rules-v1',
        scored_at TIMESTAMPTZ
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_score_history_app ON score_result_history (application_id, archived_at DESC)",
    """
    CREATE TABLE IF NOT EXISTS financial_ratio_history (
        history_id SERIAL PRIMARY KEY,
        archived_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        application_id INT NOT NULL REFERENCES credit_application (id) ON DELETE CASCADE,
        ebe NUMERIC(14, 2),
        caf NUMERIC(14, 2),
        rcsd NUMERIC(8, 3),
        gross_margin_pct NUMERIC(8, 2),
        net_margin_pct NUMERIC(8, 2),
        solvency NUMERIC(8, 3),
        inventory_days NUMERIC(10, 1),
        equity_ratio_pct NUMERIC(8, 2),
        working_capital_pct NUMERIC(8, 2),
        net_worth NUMERIC(14, 2),
        weak_ratio_count INT NOT NULL DEFAULT 0,
        stress_month INT,
        computed_at TIMESTAMPTZ
    )
    """,
]


def main() -> None:
    dsn = DSN.replace("postgresql+psycopg://", "postgresql://")
    hashed = bcrypt.hashpw(DEMO.encode(), bcrypt.gensalt()).decode()
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            for stmt in STMTS:
                cur.execute(stmt)
            cur.execute(
                "UPDATE app_user SET password_hash = %s WHERE login IN ('agent', 'chef', 'cic')",
                (hashed,),
            )
            print("auth migrate OK, password_hash mis a jour pour", cur.rowcount, "users")
        conn.commit()


if __name__ == "__main__":
    main()
