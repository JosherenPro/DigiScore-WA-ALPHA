#!/usr/bin/env python3
"""ALTER dates + tables autres IF pour un volume Postgres deja cree."""

from __future__ import annotations

import os
from pathlib import Path

import psycopg

DSN = os.getenv("DATABASE_URL", "postgresql://digiscore:digiscore@localhost:5432/digiscore")
SQL = Path(__file__).with_name("04_data_alter.sql")


def main() -> None:
    dsn = DSN.replace("postgresql+psycopg://", "postgresql://")
    text = SQL.read_text(encoding="utf-8")
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(text)
        conn.commit()
    print("data alter OK (dates + financial_institution + external_* + golden MEM-012)")


if __name__ == "__main__":
    main()
