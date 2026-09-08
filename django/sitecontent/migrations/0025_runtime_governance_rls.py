from __future__ import annotations

import os
import re

from django.db import migrations

ROLE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,62}$")
TABLES = (
    "sitecontent_breakglassgrant",
    "sitecontent_durablejob",
    "sitecontent_durableschedule",
    "sitecontent_tenantnotification",
)


def _role(schema_editor, name):
    value = os.environ.get(name, "").strip()
    if not ROLE.fullmatch(value):
        raise RuntimeError(f"runtime:{name.lower()}_invalid")
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (value,))
        if not cursor.fetchone():
            raise RuntimeError(f"runtime:{name.lower()}_missing")
    return value.replace("'", "''")


def install(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    runtime = _role(schema_editor, "WORKSPACE_DB_USER")
    worker = _role(schema_editor, "WORKSPACE_WORKER_DB_USER")
    tenant = "site_id = current_setting('app.tenant_id', true)"
    with schema_editor.connection.cursor() as cursor:
        for table in TABLES:
            cursor.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
            cursor.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
            for action in ("select", "insert", "update", "delete"):
                cursor.execute(f'DROP POLICY IF EXISTS "{table}_{action}" ON "{table}"')
            cursor.execute(f'CREATE POLICY "{table}_select" ON "{table}" FOR SELECT USING ({tenant})')
            cursor.execute(f'CREATE POLICY "{table}_insert" ON "{table}" FOR INSERT WITH CHECK ({tenant})')
            cursor.execute(
                f'CREATE POLICY "{table}_update" ON "{table}" FOR UPDATE USING ({tenant}) WITH CHECK ({tenant})'
            )
            cursor.execute(f'CREATE POLICY "{table}_delete" ON "{table}" FOR DELETE USING ({tenant})')
            cursor.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "{table}" TO "{runtime}"')
            cursor.execute(f'GRANT SELECT, INSERT, UPDATE ON TABLE "{table}" TO "{worker}"')


def uninstall(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    runtime = _role(schema_editor, "WORKSPACE_DB_USER")
    worker = _role(schema_editor, "WORKSPACE_WORKER_DB_USER")
    with schema_editor.connection.cursor() as cursor:
        for table in reversed(TABLES):
            cursor.execute(f'REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLE "{table}" FROM "{runtime}"')
            cursor.execute(f'REVOKE SELECT, INSERT, UPDATE ON TABLE "{table}" FROM "{worker}"')
            for action in ("select", "insert", "update", "delete"):
                cursor.execute(f'DROP POLICY IF EXISTS "{table}_{action}" ON "{table}"')
            cursor.execute(f'ALTER TABLE "{table}" NO FORCE ROW LEVEL SECURITY')
            cursor.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')


class Migration(migrations.Migration):
    dependencies = [("sitecontent", "0024_breakglassgrant_durablejob_durableschedule_and_more")]
    operations = [migrations.RunPython(install, uninstall)]
