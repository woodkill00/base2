"""Upgrade repair must compose tenant admission with existing restrictive fences."""
from contextlib import nullcontext
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import Mock


def test_revision_upgrade_adds_only_scoped_permissive_policy(monkeypatch):
    migration = import_module('sitecontent.migrations.0041_workspace_revision_tenant_scope')
    cursor = Mock()
    editor = SimpleNamespace(connection=SimpleNamespace(
        vendor='postgresql', cursor=lambda: nullcontext(cursor),
    ))
    helper = import_module('sitecontent.migrations.0034_public_content_runtime_scope')
    monkeypatch.setattr(helper, 'role_name', lambda _, key: {
        'WORKSPACE_DB_USER': '"request_role"',
        'WORKSPACE_WORKER_DB_USER': '"worker_role"',
    }[key])
    migration.configure(None, editor)
    sql = '\n'.join(call.args[0] for call in cursor.execute.call_args_list)
    assert 'AS PERMISSIVE FOR ALL TO "request_role", "worker_role"' in sql
    assert sql.count('content.id=sitecontent_contentrevision.content_id') == 2
    assert sql.count("content.site_id=current_setting('app.tenant_id',true)") == 2
    assert 'public.sitecontent_contentrecord content' in sql
    assert 'WITH CHECK' in sql and 'USING' in sql
    assert 'GRANT' not in sql and 'data_rights_claim_fence' not in sql
    assert 'DISABLE' not in sql and 'NO FORCE' not in sql
    assert migration.Migration.dependencies == [('sitecontent', '0040_workspace_asset_retention')]
    cursor.reset_mock()
    migration.reverse(None, editor)
    assert cursor.execute.call_args.args == (
        'DROP POLICY IF EXISTS workspace_revision_tenant_scope '
        'ON public.sitecontent_contentrevision',
    )


def test_revision_policy_sqlite_noop():
    migration = import_module('sitecontent.migrations.0041_workspace_revision_tenant_scope')
    editor = SimpleNamespace(connection=SimpleNamespace(vendor='sqlite'))
    migration.configure(None, editor)
    migration.reverse(None, editor)
