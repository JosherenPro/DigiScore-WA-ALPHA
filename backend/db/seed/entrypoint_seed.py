#!/usr/bin/env python3
"""One-shot Compose : génère les CSV s'ils manquent, puis COPY (sauf LOAD_VOLUME=0)."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import psycopg

HERE = Path(__file__).resolve().parent
VOL = Path(os.getenv("VOLUME_DIR", "/data/volume"))
DSN = os.getenv("DATABASE_URL", "postgresql://digiscore:digiscore@postgres:5432/digiscore")


def _truthy(val: str | None) -> bool:
    return (val or "1").strip().lower() not in {"0", "false", "no", "off"}


def wait_postgres(dsn: str, attempts: int = 40) -> None:
    last: Exception | None = None
    for _ in range(attempts):
        try:
            with psycopg.connect(dsn) as conn:
                conn.execute("SELECT 1")
            return
        except Exception as exc:  # noqa: BLE001 — retry jusqu'à healthy
            last = exc
            time.sleep(1)
    raise SystemExit(f"Postgres injoignable ({dsn}): {last}")


def main() -> None:
    if not _truthy(os.getenv("LOAD_VOLUME", "1")):
        print("LOAD_VOLUME=0 : skip volumétrie (12 profils démo uniquement).")
        return

    VOL.mkdir(parents=True, exist_ok=True)
    wait_postgres(DSN)

    if not (VOL / "member.csv").exists():
        print(f"CSV absents dans {VOL} — génération (VOLUME_MEMBERS={os.getenv('VOLUME_MEMBERS', '120000')})…")
        env = os.environ.copy()
        env["VOLUME_DIR"] = str(VOL)
        subprocess.check_call([sys.executable, str(HERE / "generate_volume_csv.py")], env=env)
    else:
        print(f"CSV déjà présents dans {VOL} — skip génération.")

    subprocess.check_call([sys.executable, str(HERE / "load_volume_csv.py")])


if __name__ == "__main__":
    main()
