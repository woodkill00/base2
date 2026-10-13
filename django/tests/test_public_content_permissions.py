from importlib import import_module
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def migration_setup(monkeypatch):
    module = import_module("sitecontent.migrations.0034_public_content_runtime_scope")
    connection = MagicMock()
    connection.vendor = "postgresql"
    connection.ops.quote_name.side_effect = lambda value: f'"{value}"'
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = (False, False, False, False)
    monkeypatch.setenv("API_RUNTIME_DB_USER", "api_runtime")
    monkeypatch.setenv("DATA_RIGHTS_WORKER_DB_USER", "rights_worker")
    return module, SimpleNamespace(connection=connection), cursor


def test_permissions_are_column_scoped_and_reversible(migration_setup):
    module, editor, cursor = migration_setup
    module.configure(None, editor)
    forward = [call.args[0] for call in cursor.execute.call_args_list]
    assert len([sql for sql in forward if sql.startswith("GRANT ")]) == 7
    assert all(" (" in sql for sql in forward if sql.startswith("GRANT "))
    assert not any("GRANT UPDATE" in sql or "GRANT DELETE" in sql for sql in forward)
    assert "payload" not in module.SELECT["sitecontent_formsubmission"]
    assert "storage_key" not in module.SELECT["sitecontent_mediaasset"]
    for verb, predicates in [("SELECT", module.READ_SCOPE), ("INSERT", module.WRITE_SCOPE)]:
        for table, predicate in predicates.items():
            assert any(
                f'ON {table} AS RESTRICTIVE FOR {verb} TO "api_runtime"' in sql and predicate in sql
                for sql in forward
            )
    assert any("data_rights_claim_fence" in sql and 'TO "rights_worker"' in sql for sql in forward)
    cursor.reset_mock()
    module.reverse(None, editor)
    reverse = [call.args[0] for call in cursor.execute.call_args_list]
    assert len([sql for sql in reverse if sql.startswith("REVOKE ")]) == 7
    assert len([sql for sql in reverse if "DISABLE ROW LEVEL SECURITY" in sql]) == 3
    assert "ALTER POLICY data_rights_claim_fence ON sitecontent_contentrecord TO PUBLIC" in reverse


@pytest.mark.parametrize("role", ["", "bad;role", "a" * 64])
def test_invalid_role_is_rejected(migration_setup, monkeypatch, role):
    module, editor, _cursor = migration_setup
    monkeypatch.setenv("API_RUNTIME_DB_USER", role)
    with pytest.raises(RuntimeError, match="role_invalid"):
        module.configure(None, editor)


@pytest.mark.parametrize("flags", [None, (True, False, False, False), (False, False, False, True)])
def test_privileged_or_missing_role_is_rejected(migration_setup, flags):
    module, editor, cursor = migration_setup
    cursor.fetchone.return_value = flags
    with pytest.raises(RuntimeError, match="restricted_role_required"):
        module.configure(None, editor)


def test_sqlite_is_noop(migration_setup):
    module, editor, cursor = migration_setup
    editor.connection.vendor = "sqlite"
    module.configure(None, editor)
    module.reverse(None, editor)
    cursor.execute.assert_not_called()
