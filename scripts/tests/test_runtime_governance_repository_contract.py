from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_repository_uses_tenant_context_locks_bounded_discovery_and_exact_replay():
    source = (ROOT / "api/repositories/runtime_governance.py").read_text()
    for required in (
        "workspace_db_conn(tenant_id=tenant_id)",
        "pg_advisory_xact_lock",
        "FOR UPDATE SKIP LOCKED",
        "idempotency_conflict",
        "lease_expires_at<=%s",
        "dead_letter",
        "LIMIT %s",
    ):
        assert required in source


def test_runtime_governance_tables_are_forced_rls_for_request_and_worker_roles():
    source = (ROOT / "django/sitecontent/migrations/0025_runtime_governance_rls.py").read_text()
    for table in (
        "sitecontent_breakglassgrant", "sitecontent_durablejob",
        "sitecontent_durableschedule", "sitecontent_tenantnotification",
    ):
        assert table in source
    assert "FORCE ROW LEVEL SECURITY" in source
    assert "current_setting('app.tenant_id', true)" in source
