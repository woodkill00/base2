from __future__ import annotations

import os
import re

from django.db import migrations

ROLE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,62}$")
TABLE = "sitecontent_tenantdomainclaim"


def _role(schema_editor, name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not ROLE.fullmatch(value):
        raise RuntimeError(f"domain:{name.lower()}_invalid")
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (value,))
        if not cursor.fetchone():
            raise RuntimeError(f"domain:{name.lower()}_missing")
    return value.replace("'", "''")


def install(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    runtime = _role(schema_editor, "WORKSPACE_DB_USER")
    worker = _role(schema_editor, "WORKSPACE_WORKER_DB_USER")
    tenant = "site_id = current_setting('app.tenant_id', true)"
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f'ALTER TABLE "{TABLE}" ENABLE ROW LEVEL SECURITY')
        cursor.execute(f'ALTER TABLE "{TABLE}" FORCE ROW LEVEL SECURITY')
        for action in ("select", "insert", "update", "delete"):
            cursor.execute(f'DROP POLICY IF EXISTS "{TABLE}_{action}" ON "{TABLE}"')
        cursor.execute(f'CREATE POLICY "{TABLE}_select" ON "{TABLE}" FOR SELECT USING ({tenant})')
        cursor.execute(
            f'CREATE POLICY "{TABLE}_insert" ON "{TABLE}" FOR INSERT WITH CHECK ({tenant})'
        )
        cursor.execute(
            f'CREATE POLICY "{TABLE}_update" ON "{TABLE}" FOR UPDATE '
            f'USING ({tenant}) WITH CHECK ({tenant})'
        )
        cursor.execute(f'CREATE POLICY "{TABLE}_delete" ON "{TABLE}" FOR DELETE USING ({tenant})')
        cursor.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "{TABLE}" TO "{runtime}"')
        cursor.execute(f'GRANT SELECT, INSERT, UPDATE ON TABLE "{TABLE}" TO "{worker}"')


def uninstall(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    runtime = _role(schema_editor, "WORKSPACE_DB_USER")
    worker = _role(schema_editor, "WORKSPACE_WORKER_DB_USER")
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f'REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLE "{TABLE}" FROM "{runtime}"')
        cursor.execute(f'REVOKE SELECT, INSERT, UPDATE ON TABLE "{TABLE}" FROM "{worker}"')
        for action in ("select", "insert", "update", "delete"):
            cursor.execute(f'DROP POLICY IF EXISTS "{TABLE}_{action}" ON "{TABLE}"')
        cursor.execute(f'ALTER TABLE "{TABLE}" NO FORCE ROW LEVEL SECURITY')
        cursor.execute(f'ALTER TABLE "{TABLE}" DISABLE ROW LEVEL SECURITY')


class Migration(migrations.Migration):
    dependencies = [("sitecontent", "0022_tenantdomainclaim")]
    operations = [migrations.RunPython(install, uninstall)]
