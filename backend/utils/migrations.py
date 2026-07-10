from __future__ import annotations

from pathlib import Path

import config


def run_production_migrations() -> None:
    if not config.IS_PRODUCTION or not config.DATABASE_URL:
        return

    try:
        import psycopg
    except ImportError:
        print("[migrations] psycopg is not installed; skipping database migrations.", flush=True)
        return

    migrations_dir = Path(__file__).resolve().parents[1] / "migrations"
    migration_files = sorted(migrations_dir.glob("*.sql"))
    if not migration_files:
        return

    try:
        with psycopg.connect(config.DATABASE_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                for migration_file in migration_files:
                    cur.execute(migration_file.read_text(encoding="utf-8"))
                    print(f"[migrations] applied {migration_file.name}", flush=True)
    except Exception as exc:
        print(f"[migrations] failed: {exc}", flush=True)
