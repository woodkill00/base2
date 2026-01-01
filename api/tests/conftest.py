from __future__ import annotations

import os
import sys


# Ensure repository root is on sys.path for imports in tests
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def pytest_sessionstart(session):
    # Ensure idempotent schema exists before any tests run.
    try:
        from api.migrations.runner import apply_migrations

        apply_migrations()
    except Exception:
        # If DB isn't available, tests that rely on it will fail naturally.
        pass
