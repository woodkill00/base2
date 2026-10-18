from importlib import import_module
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def setup(monkeypatch):
    module = import_module("sitecontent.migrations.0035_booking_runtime_capability")
    editor = MagicMock()
    editor.connection.vendor = "postgresql"
    editor.connection.ops.quote_name.side_effect = lambda value: f'"{value}"'
    cursor = editor.connection.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = (False, False, False, False)
    monkeypatch.setenv("API_RUNTIME_DB_USER", "api_runtime")
    return module, editor, cursor


def test_forward_is_narrow_fixed_search_path_and_reverse_revokes(setup):
    module, editor, _ = setup
    module.configure(None, editor)
    editor.execute.assert_any_call(module.SQL, params=None)
    statements = [call.args[0] for call in editor.execute.call_args_list]
    assert "SECURITY DEFINER SET search_path = pg_catalog" in module.SQL
    assert "WHERE id = p_event AND site_id = tenant FOR UPDATE" in module.SQL
    assert "ev.ends_at <= clock_timestamp()" in module.SQL
    assert f"REVOKE ALL ON FUNCTION {module.SIGNATURE} FROM PUBLIC" in statements
    grants = [sql for sql in statements if sql.startswith("GRANT")]
    assert grants == [
        f'GRANT EXECUTE ON FUNCTION {module.SIGNATURE} TO "api_runtime"',
        'GRANT SELECT ON public.scheduling_event TO "api_runtime"',
    ]
    editor.reset_mock()
    module.reverse(None, editor)
    statements = [call.args[0] for call in editor.execute.call_args_list]
    assert f"DROP FUNCTION {module.SIGNATURE}" in statements
    assert 'REVOKE SELECT ON public.scheduling_event FROM "api_runtime"' in statements
    assert not any("DISABLE ROW LEVEL SECURITY" in sql for sql in statements)


@pytest.mark.parametrize("flags", [None, (True, False, False, False), (False, False, False, True)])
def test_missing_or_privileged_role_fails_before_mutation(setup, flags):
    module, editor, cursor = setup
    cursor.fetchone.return_value = flags
    with pytest.raises(RuntimeError, match="restricted_role_required"):
        module.configure(None, editor)
    editor.execute.assert_not_called()


def test_sqlite_is_noop(setup):
    module, editor, _ = setup
    editor.connection.vendor = "sqlite"
    module.configure(None, editor)
    module.reverse(None, editor)
    editor.execute.assert_not_called()
