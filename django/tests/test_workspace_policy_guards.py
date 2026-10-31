"""Migration authority contracts; SQL effects require the real-role PostgreSQL suite."""

from contextlib import nullcontext
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


def module():
    return import_module("sitecontent.migrations.0038_workspace_policy_guards")


def editor(vendor="postgresql", owner=True):
    cur = Mock()
    cur.fetchone.return_value = (owner,)
    return SimpleNamespace(
        connection=SimpleNamespace(vendor=vendor, cursor=lambda: nullcontext(cur))
    ), cur


def test_sqlite_does_not_install_postgres_helpers():
    target, cur = editor("sqlite")
    module().configure(None, target)
    cur.execute.assert_not_called()


def test_runtime_roles_never_receive_owner_or_arbitrary_identity_access(monkeypatch):
    roles = import_module("sitecontent.migrations.0037_workspace_policy_runtime_roles")
    monkeypatch.setattr(
        roles, "roles", lambda _: dict(request='"request"', worker='"worker"', api='"api"')
    )
    target, cur = editor()
    module().configure(None, target)
    statements = [call.args[0] for call in cur.execute.call_args_list]
    for signature in module().FUNCTIONS:
        assert f"REVOKE ALL ON FUNCTION public.{signature} FROM PUBLIC" in statements
    assert any(
        "UPDATE OF id,is_active" in sql and "ON api_auth_users " in sql for sql in statements
    )
    assert any("UPDATE OF organization_id,user_id,role,status" in sql for sql in statements)
    assert any("UPDATE OF id,tenant_id" in sql for sql in statements)
    grants = [sql for sql in statements if sql.startswith("GRANT")]
    assert not any("api_auth_users" in sql or "BYPASSRLS" in sql for sql in grants)
    assert not any("base2_review_maintenance_allowed" in sql for sql in grants)
    assert len(
        [sql for sql in statements if sql.startswith("CREATE TRIGGER workspace_effect_lock")]
    ) == len(module().PROTECTED)
    assert any(
        "AS RESTRICTIVE" in sql and "workspace_public_asset_visibility" in sql for sql in statements
    )
    assert all(
        "SET search_path=pg_catalog,public" in item
        for item in module().SQL.split("SECURITY DEFINER")[1:]
    )


def test_helpers_require_real_migration_owner_force_rls_capability(monkeypatch):
    roles = import_module("sitecontent.migrations.0037_workspace_policy_runtime_roles")
    monkeypatch.setattr(
        roles, "roles", lambda _: dict(request='"request"', worker='"worker"', api='"api"')
    )
    target, cur = editor(owner=False)
    with pytest.raises(RuntimeError, match="migration_owner_rls_capability_required"):
        module().configure(None, target)
    assert cur.execute.call_count == 1


def test_cycle_authority_and_native_schedule_guards_are_not_timestamp_heuristics():
    sql = module().SQL
    assert "content_review_cycle_invalid" in sql
    assert "a.subject_revision=s.semantic_revision" in sql
    assert "p_permission IS NULL" in sql
    assert "content_review_provenance_immutable" in sql
    assert "session_user<>'__WORKER_ROLE__'" in sql
    assert "OLD.publish_at>NOW()" in sql
    assert "base2_review_maintenance_allowed" in sql


def test_reverse_fails_closed_for_guard_removal():
    with pytest.raises(RuntimeError, match="rollback"):
        module().reverse(None, editor()[0])
