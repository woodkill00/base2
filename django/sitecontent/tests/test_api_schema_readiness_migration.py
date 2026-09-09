from __future__ import annotations

import importlib
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


migration = importlib.import_module("sitecontent.migrations.0033_api_schema_readiness")


def schema_editor(*, vendor: str = "postgresql"):
    editor = MagicMock()
    editor.connection = SimpleNamespace(
        vendor=vendor,
        ops=SimpleNamespace(quote_name=lambda value: f'"{value}"'),
    )
    return editor


def test_non_postgresql_database_is_unchanged(monkeypatch):
    monkeypatch.delenv("API_RUNTIME_DB_USER", raising=False)
    editor = schema_editor(vendor="sqlite")
    migration.grant_schema_readiness(None, editor)
    migration.revoke_schema_readiness(None, editor)
    editor.execute.assert_not_called()


def test_invalid_runtime_role_fails_before_database_access(monkeypatch):
    monkeypatch.setenv("API_RUNTIME_DB_USER", "invalid-role")
    editor = schema_editor()
    with pytest.raises(RuntimeError, match="api_runtime:role_invalid"):
        migration.grant_schema_readiness(None, editor)
    with pytest.raises(RuntimeError, match="api_runtime:role_invalid"):
        migration.revoke_schema_readiness(None, editor)
    editor.execute.assert_not_called()


def test_forward_and_reverse_are_ledger_only(monkeypatch):
    monkeypatch.setenv("API_RUNTIME_DB_USER", "base2_api_runtime")
    editor = schema_editor()
    migration.grant_schema_readiness(None, editor)
    migration.revoke_schema_readiness(None, editor)
    assert [call.args[0] for call in editor.execute.call_args_list] == [
        'GRANT SELECT ON TABLE django_migrations TO "base2_api_runtime"',
        'REVOKE SELECT ON TABLE django_migrations FROM "base2_api_runtime"',
    ]
