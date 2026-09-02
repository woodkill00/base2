from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / 'django' / 'sitecontent' / 'migrations'


def test_django_is_the_only_owner_of_workspace_physical_schema():
    django_text = '\n'.join(path.read_text() for path in sorted(MIGRATIONS.glob('*.py')))
    api_text = '\n'.join(
        path.read_text()
        for path in sorted((ROOT / 'api' / 'migrations').glob('*'))
        if path.is_file()
    )
    assert 'ContentTypeDefinition' in django_text
    assert 'ContentRecordVersion' in django_text
    assert 'sitecontent_contenttypedefinition' not in api_text
    assert 'sitecontent_contentrecord' not in api_text


def test_workspace_rls_inventory_is_closed_and_migration_is_reversible():
    migration_path = MIGRATIONS / '0003_workspace_row_security.py'
    tree = ast.parse(migration_path.read_text())
    assignments = {
        node.targets[0].id: ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
    }
    tables = assignments['WORKSPACE_TABLES']
    assert len(tables) == len(set(tables)) == 9
    assert all(table.startswith('sitecontent_') for table in tables)
    text = migration_path.read_text()
    assert 'ENABLE ROW LEVEL SECURITY' in text
    assert 'WITH CHECK' in text
    assert "current_setting('app.tenant_id', true)" in text
    assert 'disable_workspace_rls' in text
