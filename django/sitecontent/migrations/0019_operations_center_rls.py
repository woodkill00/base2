from __future__ import annotations

import os
import re

from django.db import migrations

ROLE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,62}$")
TABLES = (
    "sitecontent_operationsservice",
    "sitecontent_operationshealthsample",
    "sitecontent_operationssyntheticrun",
    "sitecontent_operationsobjective",
    "sitecontent_operationsincident",
    "sitecontent_operationsincidentevent",
    "sitecontent_operationsalertdelivery",
)
PARENTS = (
    "sitecontent_operationsservice",
    "sitecontent_operationsincident",
)
LINKS = (
    (
        "sitecontent_operationshealthsample",
        "service_id",
        "sitecontent_operationsservice",
        "operations_health_service_scope_fk",
    ),
    (
        "sitecontent_operationsincidentevent",
        "incident_id",
        "sitecontent_operationsincident",
        "operations_event_incident_scope_fk",
    ),
    (
        "sitecontent_operationsalertdelivery",
        "incident_id",
        "sitecontent_operationsincident",
        "operations_delivery_incident_scope_fk",
    ),
)


def _role(schema_editor, variable: str, error_prefix: str) -> str:
    role = os.environ.get(variable, "").strip()
    if not ROLE_NAME.fullmatch(role):
        raise RuntimeError(f"{error_prefix}_role_invalid")
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,))
        if not cursor.fetchone():
            raise RuntimeError(f"{error_prefix}_role_missing")
    return role


def install_operations_boundaries(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    runtime = _role(schema_editor, "WORKSPACE_DB_USER", "operations_runtime").replace("'", "''")
    worker = _role(schema_editor, "WORKSPACE_WORKER_DB_USER", "operations_worker").replace(
        "'", "''"
    )
    with schema_editor.connection.cursor() as cursor:
        for table in PARENTS:
            cursor.execute(
                f'ALTER TABLE "{table}" ADD CONSTRAINT "{table}_site_id_id_uq" '
                "UNIQUE (site_id, id)"
            )
        for table, column, parent, name in LINKS:
            cursor.execute(
                f'ALTER TABLE "{table}" ADD CONSTRAINT "{name}" '
                f'FOREIGN KEY (site_id, "{column}") REFERENCES "{parent}" (site_id, id) '
                "NOT VALID"
            )
            cursor.execute(f'ALTER TABLE "{table}" VALIDATE CONSTRAINT "{name}"')
        for table in TABLES:
            tenant = "site_id = current_setting('app.tenant_id', true)"
            cursor.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
            cursor.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
            for suffix in ("select", "insert", "update", "delete"):
                cursor.execute(f'DROP POLICY IF EXISTS "{table}_{suffix}" ON "{table}"')
            cursor.execute(
                f"""CREATE POLICY "{table}_select" ON "{table}" FOR SELECT
                    USING ({tenant} OR current_user = '{worker}')"""
            )
            cursor.execute(
                f"""CREATE POLICY "{table}_insert" ON "{table}" FOR INSERT
                    WITH CHECK ({tenant})"""
            )
            cursor.execute(
                f"""CREATE POLICY "{table}_update" ON "{table}" FOR UPDATE
                    USING ({tenant}) WITH CHECK ({tenant})"""
            )
            cursor.execute(
                f"""CREATE POLICY "{table}_delete" ON "{table}" FOR DELETE
                    USING ({tenant})"""
            )
            cursor.execute(
                f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "{table}" TO "{runtime}"'
            )
            cursor.execute(f'GRANT SELECT ON TABLE "{table}" TO "{worker}"')


def remove_operations_boundaries(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    runtime = _role(schema_editor, "WORKSPACE_DB_USER", "operations_runtime").replace("'", "''")
    worker = _role(schema_editor, "WORKSPACE_WORKER_DB_USER", "operations_worker").replace(
        "'", "''"
    )
    with schema_editor.connection.cursor() as cursor:
        for table in reversed(TABLES):
            cursor.execute(
                f'REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLE "{table}" FROM "{runtime}"'
            )
            cursor.execute(f'REVOKE SELECT ON TABLE "{table}" FROM "{worker}"')
            for suffix in ("select", "insert", "update", "delete"):
                cursor.execute(f'DROP POLICY IF EXISTS "{table}_{suffix}" ON "{table}"')
            cursor.execute(f'ALTER TABLE "{table}" NO FORCE ROW LEVEL SECURITY')
            cursor.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
        for table, _column, _parent, name in reversed(LINKS):
            cursor.execute(f'ALTER TABLE "{table}" DROP CONSTRAINT "{name}"')
        for table in reversed(PARENTS):
            cursor.execute(f'ALTER TABLE "{table}" DROP CONSTRAINT "{table}_site_id_id_uq"')


class Migration(migrations.Migration):
    dependencies = [("sitecontent", "0018_production_operations_center")]
    operations = [migrations.RunPython(install_operations_boundaries, remove_operations_boundaries)]
