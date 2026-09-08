from __future__ import annotations

import os
import re

from django.db import migrations

ROLE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,62}$")
OPERATIONS_TABLES = (
    "sitecontent_operationsservice",
    "sitecontent_operationshealthsample",
    "sitecontent_operationssyntheticrun",
    "sitecontent_operationsobjective",
    "sitecontent_operationsincident",
    "sitecontent_operationsincidentevent",
    "sitecontent_operationsalertdelivery",
)
QUOTA_TABLES = ("sitecontent_tenantquota", "sitecontent_tenantquotareservation")


def _role(schema_editor, name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not ROLE.fullmatch(value):
        raise RuntimeError(f"quota:{name.lower()}_invalid")
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (value,))
        if not cursor.fetchone():
            raise RuntimeError(f"quota:{name.lower()}_missing")
    return value.replace("'", "''")


def install(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    runtime = _role(schema_editor, "WORKSPACE_DB_USER")
    worker = _role(schema_editor, "WORKSPACE_WORKER_DB_USER")
    tenant = "site_id = current_setting('app.tenant_id', true)"
    with schema_editor.connection.cursor() as cursor:
        # Remove the former worker-wide bypass. Workers must select a tenant
        # context for every unit of work just like request handlers.
        for table in OPERATIONS_TABLES:
            cursor.execute(f'DROP POLICY IF EXISTS "{table}_select" ON "{table}"')
            cursor.execute(
                f'CREATE POLICY "{table}_select" ON "{table}" FOR SELECT USING ({tenant})'
            )
        cursor.execute(
            'ALTER TABLE "sitecontent_tenantquota" ADD CONSTRAINT '
            '"tenant_quota_site_id_id_uq" UNIQUE (site_id, id)'
        )
        cursor.execute(
            'ALTER TABLE "sitecontent_tenantquotareservation" ADD CONSTRAINT '
            '"tenant_quota_reservation_scope_fk" FOREIGN KEY (site_id, quota_id) '
            'REFERENCES "sitecontent_tenantquota" (site_id, id) NOT VALID'
        )
        cursor.execute(
            'ALTER TABLE "sitecontent_tenantquotareservation" '
            'VALIDATE CONSTRAINT "tenant_quota_reservation_scope_fk"'
        )
        for table in QUOTA_TABLES:
            cursor.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
            cursor.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
            for action in ("select", "insert", "update", "delete"):
                cursor.execute(f'DROP POLICY IF EXISTS "{table}_{action}" ON "{table}"')
            cursor.execute(
                f'CREATE POLICY "{table}_select" ON "{table}" FOR SELECT USING ({tenant})'
            )
            cursor.execute(
                f'CREATE POLICY "{table}_insert" ON "{table}" FOR INSERT WITH CHECK ({tenant})'
            )
            cursor.execute(
                f'CREATE POLICY "{table}_update" ON "{table}" FOR UPDATE '
                f"USING ({tenant}) WITH CHECK ({tenant})"
            )
            cursor.execute(
                f'CREATE POLICY "{table}_delete" ON "{table}" FOR DELETE USING ({tenant})'
            )
            cursor.execute(
                f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "{table}" TO "{runtime}"'
            )
            cursor.execute(f'GRANT SELECT, INSERT, UPDATE ON TABLE "{table}" TO "{worker}"')


def uninstall(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    runtime = _role(schema_editor, "WORKSPACE_DB_USER")
    worker = _role(schema_editor, "WORKSPACE_WORKER_DB_USER")
    with schema_editor.connection.cursor() as cursor:
        for table in reversed(QUOTA_TABLES):
            cursor.execute(
                f'REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLE "{table}" FROM "{runtime}"'
            )
            cursor.execute(f'REVOKE SELECT, INSERT, UPDATE ON TABLE "{table}" FROM "{worker}"')
            for action in ("select", "insert", "update", "delete"):
                cursor.execute(f'DROP POLICY IF EXISTS "{table}_{action}" ON "{table}"')
            cursor.execute(f'ALTER TABLE "{table}" NO FORCE ROW LEVEL SECURITY')
            cursor.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
        cursor.execute(
            'ALTER TABLE "sitecontent_tenantquotareservation" '
            'DROP CONSTRAINT "tenant_quota_reservation_scope_fk"'
        )
        cursor.execute(
            'ALTER TABLE "sitecontent_tenantquota" ' 'DROP CONSTRAINT "tenant_quota_site_id_id_uq"'
        )
        tenant = "site_id = current_setting('app.tenant_id', true)"
        historical_worker_bypass = tenant + " " + "OR " + f"current_user = '{worker}'"
        for table in OPERATIONS_TABLES:
            cursor.execute(f'DROP POLICY IF EXISTS "{table}_select" ON "{table}"')
            cursor.execute(
                f'CREATE POLICY "{table}_select" ON "{table}" FOR SELECT '
                f"USING ({historical_worker_bypass})"
            )


class Migration(migrations.Migration):
    dependencies = [("sitecontent", "0020_tenant_quota_persistence")]
    operations = [migrations.RunPython(install, uninstall)]
