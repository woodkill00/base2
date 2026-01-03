from __future__ import annotations

import os
import sys


# Ensure repository root is on sys.path for imports in tests
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def pytest_sessionstart(session):
    """Validate DB schema when a DB is reachable.

    Schema ownership is Django. Tests should rely on `python manage.py migrate` having
    been run (e.g., in CI and deploy AllTests).
    """

    try:
        from api.db import db_conn

        with db_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.api_auth_users')")
            exists = cur.fetchone()[0] is not None
    except Exception:
        # No DB available: unit tests that don't require DB can still run.
        return

    if not exists:
        raise RuntimeError(
            "Database is reachable but API tables are missing. "
            "Schema ownership is Django; run `python manage.py migrate` "
            "(using project.settings.production against Postgres) before running API integration tests."
        )
