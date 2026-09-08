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
JOB_GRANTS = {
    "sitecontent_durablejob": "SELECT, INSERT, UPDATE",
    "sitecontent_durableschedule": "SELECT, UPDATE",
}
EMAIL_GRANTS = {"api_email_outbox": "SELECT, UPDATE"}


def _worker_role(schema_editor) -> str:
    configured = os.environ.get("WORKSPACE_WORKER_DB_USER", "").strip()
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('base2.workspace_worker_role', true)")
        session_role = str((cursor.fetchone() or ("",))[0] or "").strip()
        if not ROLE.fullmatch(configured):
            raise RuntimeError("runtime:workspace_worker_role_invalid")
        if session_role and configured and session_role != configured:
            raise RuntimeError("runtime:workspace_worker_role_mismatch")
        role = configured
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,))
        if not cursor.fetchone():
            raise RuntimeError("runtime:workspace_worker_role_missing")
        cursor.execute("SELECT set_config('base2.workspace_worker_role', %s, false)", (role,))
    return schema_editor.connection.ops.quote_name(role)


def narrow_worker_runtime_grants(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    worker = _worker_role(schema_editor)
    grants = {
        **{table: "SELECT, INSERT, UPDATE, DELETE" for table in OPERATIONS_TABLES},
        **JOB_GRANTS,
        **EMAIL_GRANTS,
    }
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f"GRANT USAGE ON SCHEMA public TO {worker}")
        for table, privileges in grants.items():
            quoted_table = schema_editor.connection.ops.quote_name(table)
            cursor.execute(f"REVOKE ALL PRIVILEGES ON TABLE {quoted_table} FROM PUBLIC")
            cursor.execute(f"REVOKE ALL PRIVILEGES ON TABLE {quoted_table} FROM {worker}")
            cursor.execute(f"GRANT {privileges} ON TABLE {quoted_table} TO {worker}")


class Migration(migrations.Migration):
    dependencies = [
        ("api_schema", "0001_api_auth_and_outbox_tables"),
        ("sitecontent", "0027_destructiveapprovaluse_and_more"),
    ]

    operations = [
        # Reversal deliberately never restores historical broad grants.
        migrations.RunPython(narrow_worker_runtime_grants, migrations.RunPython.noop),
    ]
