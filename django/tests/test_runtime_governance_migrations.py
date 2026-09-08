from __future__ import annotations

from datetime import UTC, datetime, timedelta
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

pytestmark = pytest.mark.django_db(transaction=True)

BEFORE = ("sitecontent", "0025_runtime_governance_rls")
AFTER = ("sitecontent", "0028_worker_runtime_least_privilege")
LATEST = ("sitecontent", "0030_worker_scope_and_lifecycle_repair")


def _executor() -> MigrationExecutor:
    return MigrationExecutor(connection)


def test_runtime_integrity_migration_quarantines_permissive_legacy_job_before_constraints():
    executor = _executor()
    executor.migrate([BEFORE])
    old_apps = executor.loader.project_state([BEFORE]).apps
    DurableJob = old_apps.get_model("sitecontent", "DurableJob")
    job_id = UUID(int=106)
    now = datetime(2026, 9, 8, tzinfo=UTC)
    DurableJob.objects.create(
        id=job_id,
        site_id="tenant-one",
        owner_ref="../legacy-owner",
        generation=1,
        job_type="Legacy Job",
        payload_digest="X" * 64,
        payload_schema=1,
        idempotency_key="legacy+unsafe",
        state="leased",
        attempts=1,
        maximum_attempts=5,
        available_at=now,
        lease_owner="legacy-worker",
        lease_expires_at=now + timedelta(minutes=5),
        result_digest="not-a-digest",
        error_code="",
    )

    try:
        executor = _executor()
        executor.migrate([AFTER])
        current_apps = executor.loader.project_state([AFTER]).apps
        migrated = current_apps.get_model("sitecontent", "DurableJob").objects.get(pk=job_id)
        assert migrated.state == "dead_letter"
        assert migrated.owner_ref == f"legacy:{job_id}"
        assert migrated.job_type == "legacy.invalid"
        assert migrated.idempotency_key == f"legacy:{job_id}"
        assert migrated.payload_digest == "0" * 64
        assert migrated.result_digest == ""
        assert migrated.lease_owner == ""
        assert migrated.lease_token is None
        assert migrated.lease_expires_at is None
        assert migrated.error_code == "job.legacy_identity_invalid"
    finally:
        _executor().migrate([LATEST])


def test_worker_runtime_grants_are_explicit_and_public_access_is_revoked(monkeypatch):
    migration = import_module("sitecontent.migrations.0028_worker_runtime_least_privilege")
    cursor = MagicMock()
    database = MagicMock()
    database.vendor = "postgresql"
    database.cursor.return_value.__enter__.return_value = cursor
    database.ops.quote_name.side_effect = lambda value: f'"{value}"'
    editor = SimpleNamespace(connection=database)
    monkeypatch.setattr(migration, "_worker_role", lambda _: '"base2_worker"')
    monkeypatch.setattr(migration, "_content_worker_role", lambda _: '"base2_content_worker"')
    monkeypatch.setattr(migration, "_email_worker_role", lambda _: '"base2_email_worker"')

    migration.narrow_worker_runtime_grants(None, editor)

    statements = [call.args[0] for call in cursor.execute.call_args_list]
    targets = {
        **{table: "SELECT, INSERT, UPDATE, DELETE" for table in migration.OPERATIONS_TABLES},
        **migration.JOB_GRANTS,
        **migration.QUOTA_GRANTS,
    }
    for table, privileges in targets.items():
        assert f'REVOKE ALL PRIVILEGES ON TABLE "{table}" FROM PUBLIC' in statements
        assert f'REVOKE ALL PRIVILEGES ON TABLE "{table}" FROM "base2_worker"' in statements
        assert f'GRANT {privileges} ON TABLE "{table}" TO "base2_worker"' in statements
    assert 'REVOKE ALL PRIVILEGES ON TABLE api_email_outbox FROM "base2_worker"' in statements
    assert (
        'REVOKE ALL PRIVILEGES ON TABLE api_email_outbox FROM "base2_content_worker"' in statements
    )
    assert 'GRANT SELECT, UPDATE ON TABLE api_email_outbox TO "base2_email_worker"' in statements
    assert all(
        not ("GRANT" in statement and "sitecontent_breakglassgrant" in statement)
        for statement in statements
    )
    assert all("CREATE POLICY" not in statement for statement in statements)


def test_worker_role_fails_closed_on_session_environment_mismatch(monkeypatch):
    migration = import_module("sitecontent.migrations.0028_worker_runtime_least_privilege")
    cursor = MagicMock()
    cursor.fetchone.return_value = ("session_worker",)
    database = MagicMock()
    database.cursor.return_value.__enter__.return_value = cursor
    editor = SimpleNamespace(connection=database)
    monkeypatch.setenv("RUNTIME_WORKER_DB_USER", "environment_worker")
    with pytest.raises(RuntimeError, match="role_mismatch"):
        migration._worker_role(editor)
