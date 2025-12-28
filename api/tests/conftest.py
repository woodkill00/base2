from __future__ import annotations


def pytest_sessionstart(session):
    # Ensure idempotent schema exists before any tests run.
    try:
        from api.migrations.runner import apply_migrations

        apply_migrations()
    except Exception:
        # If DB isn't available, tests that rely on it will fail naturally.
        pass
