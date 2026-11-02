from contextlib import nullcontext
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import Mock

migration = import_module("sitecontent.migrations.0037_workspace_policy_runtime_roles")


def test_sqlite_roles_are_noop():
    editor = SimpleNamespace(connection=SimpleNamespace(vendor="sqlite"))
    migration.configure(None, editor)
    migration.reverse(None, editor)


def test_review_role_grants_are_scoped_and_do_not_broaden_public_access(monkeypatch):
    cursor = Mock()
    editor = SimpleNamespace(
        connection=SimpleNamespace(vendor="postgresql", cursor=lambda: nullcontext(cursor))
    )
    monkeypatch.setattr(
        migration,
        "roles",
        lambda _: {"request": '"request_role"', "worker": '"worker_role"', "api": '"api_role"'},
    )
    migration.configure(None, editor)
    sql = "\n".join(call.args[0] for call in cursor.execute.call_args_list)
    assert "FORCE ROW LEVEL SECURITY" in sql
    assert "site_id=current_setting('app.tenant_id',true)" in sql
    assert "tenant_id=current_setting('app.tenant_id',true)" in sql
    assert 'GRANT SELECT, INSERT ON sitecontent_reviewapproval TO "request_role"' in sql
    assert 'GRANT SELECT, INSERT ON sitecontent_reviewnotificationdelivery TO "worker_role"' in sql
    assert "GRANT DELETE" not in sql
    assert "GRANT SELECT (site_id,schema_version,version,require_review,public_access)" in sql
    assert not any(
        "api_role" in line and "GRANT" in line and "reviewsubject" in line
        for line in sql.splitlines()
    )
    cursor.reset_mock()
    migration.reverse(None, editor)
    reverse = "\n".join(call.args[0] for call in cursor.execute.call_args_list)
    assert "DISABLE ROW LEVEL SECURITY" not in reverse
    assert "NO FORCE" not in reverse


def test_roles_use_existing_validated_role_names(monkeypatch):
    for variable, value in [
        ("WORKSPACE_DB_USER", "workspace"),
        ("WORKSPACE_WORKER_DB_USER", "worker"),
        ("API_RUNTIME_DB_USER", "api"),
    ]:
        monkeypatch.setenv(variable, value)
    cursor = Mock()
    cursor.fetchone.return_value = (False, False, False, False)
    editor = SimpleNamespace(
        connection=SimpleNamespace(
            ops=SimpleNamespace(quote_name=lambda name: '"' + name + '"'),
            cursor=lambda: nullcontext(cursor),
        )
    )
    assert migration.roles(editor) == {
        "request": '"workspace"',
        "worker": '"worker"',
        "api": '"api"',
    }
