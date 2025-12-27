from __future__ import annotations

import os
from pathlib import Path

from api.db import db_conn


_MIGRATIONS_DIR = Path(__file__).resolve().parent / "sql"


def _read_sql(version: str) -> str:
    path = _MIGRATIONS_DIR / f"{version}.sql"
    return path.read_text(encoding="utf-8")


def apply_migrations() -> None:
    """Apply API-side schema migrations.

    This is a lightweight migration runner intended for the droplet environment,
    where we need idempotent schema creation during UpdateOnly deploys.
    """

    # Allow disabling in rare cases.
    if os.getenv("API_DISABLE_MIGRATIONS", "").strip().lower() in {"1", "true", "yes", "on"}:
        return

    migrations = [
        "001_create_auth_tables",
        "002_create_email_outbox",
    ]

    with db_conn() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            # Ensure the migration table exists even if migration SQL changes.
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS api_schema_migrations (
                  version TEXT PRIMARY KEY,
                  applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )

            for version in migrations:
                cur.execute("SELECT 1 FROM api_schema_migrations WHERE version=%s", (version,))
                already = cur.fetchone() is not None
                if already:
                    continue

                sql = _read_sql(version)
                cur.execute(sql)
                cur.execute(
                    "INSERT INTO api_schema_migrations(version) VALUES (%s)",
                    (version,),
                )
