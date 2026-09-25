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
                cur.execute("select pg_advisory_lock(hashtext('ragverse_schema_migrations'))")
                try:
                    cur.execute(
                        """
                        create table if not exists public.schema_migrations (
                            filename text primary key,
                            applied_at timestamptz not null default now()
                        )
                        """
                    )
                    cur.execute("select filename from public.schema_migrations")
                    applied = {row[0] for row in cur.fetchall()}
                    for migration_file in migration_files:
                        if migration_file.name in applied:
                            continue
                        cur.execute(migration_file.read_text(encoding="utf-8"))
                        cur.execute(
                            "insert into public.schema_migrations (filename) values (%s)",
                            (migration_file.name,),
                        )
                        print(f"[migrations] applied {migration_file.name}", flush=True)
                finally:
                    cur.execute("select pg_advisory_unlock(hashtext('ragverse_schema_migrations'))")
    except Exception as exc:
        print(f"[migrations] failed: {exc}", flush=True)
