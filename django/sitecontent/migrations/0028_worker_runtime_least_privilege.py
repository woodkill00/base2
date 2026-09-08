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
QUOTA_GRANTS = {
    "sitecontent_tenantquota": "SELECT, INSERT, UPDATE",
    "sitecontent_tenantquotareservation": "SELECT, INSERT, UPDATE",
}
HISTORICAL_WORKSPACE_TABLES = (
    "sitecontent_assetbinding",
    "sitecontent_contentfielddefinition",
    "sitecontent_contentrecord",
    "sitecontent_contentrelationship",
    "sitecontent_contentrevision",
    "sitecontent_contenttypedefinition",
    "sitecontent_exportjob",
    "sitecontent_importjob",
    "sitecontent_importrowoutcome",
    "sitecontent_mediaasset",
    "sitecontent_mediavariant",
    "sitecontent_savedview",
    "sitecontent_searchdocument",
    "sitecontent_workflowdefinition",
    "sitecontent_workspaceauditevent",
    "sitecontent_mediacollection",
    "sitecontent_mediacollectionmembership",
    "sitecontent_mediajob",
    "sitecontent_mediametadatarevision",
    "sitecontent_mediaobjectversion",
    "sitecontent_mediaretentionhold",
    "sitecontent_mediauploadsession",
)
DIRECT_TENANT_RLS_TABLES = (
    "sitecontent_contenttypedefinition",
    "sitecontent_contentrecord",
    "sitecontent_contentrelationship",
    "sitecontent_savedview",
    "sitecontent_assetbinding",
    "sitecontent_importjob",
    "sitecontent_exportjob",
    "sitecontent_workspaceauditevent",
    "sitecontent_mediaasset",
    "sitecontent_mediacollection",
    "sitecontent_mediacollectionmembership",
    "sitecontent_mediajob",
    "sitecontent_mediametadatarevision",
    "sitecontent_mediaobjectversion",
    "sitecontent_mediaretentionhold",
    "sitecontent_mediauploadsession",
)
CONTENT_FORBIDDEN_TABLES = (
    *OPERATIONS_TABLES,
    *JOB_GRANTS,
    *QUOTA_GRANTS,
    "sitecontent_breakglassgrant",
    "sitecontent_tenantnotification",
    "sitecontent_tenantdomainclaim",
)


def _worker_role(schema_editor) -> str:
    configured = os.environ.get("RUNTIME_WORKER_DB_USER", "").strip()
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('base2.runtime_worker_role', true)")
        session_role = str((cursor.fetchone() or ("",))[0] or "").strip()
        if not ROLE.fullmatch(configured):
            raise RuntimeError("runtime:runtime_worker_role_invalid")
        if session_role and configured and session_role != configured:
            raise RuntimeError("runtime:runtime_worker_role_mismatch")
        role = configured
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,))
        if not cursor.fetchone():
            raise RuntimeError("runtime:runtime_worker_role_missing")
        cursor.execute("SELECT set_config('base2.runtime_worker_role', %s, false)", (role,))
    return schema_editor.connection.ops.quote_name(role)


def _content_worker_role(schema_editor) -> str:
    configured = os.environ.get("WORKSPACE_WORKER_DB_USER", "").strip()
    if not ROLE.fullmatch(configured):
        raise RuntimeError("runtime:content_worker_role_invalid")
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (configured,))
        if not cursor.fetchone():
            raise RuntimeError("runtime:content_worker_role_missing")
    return schema_editor.connection.ops.quote_name(configured)


def _email_worker_role(schema_editor) -> str:
    configured = os.environ.get("EMAIL_WORKER_DB_USER", "").strip()
    if not ROLE.fullmatch(configured):
        raise RuntimeError("runtime:email_worker_role_invalid")
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (configured,))
        if not cursor.fetchone():
            raise RuntimeError("runtime:email_worker_role_missing")
    return schema_editor.connection.ops.quote_name(configured)


def narrow_worker_runtime_grants(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    worker = _worker_role(schema_editor)
    content_worker = _content_worker_role(schema_editor)
    email_worker = _email_worker_role(schema_editor)
    grants = {
        **{table: "SELECT, INSERT, UPDATE, DELETE" for table in OPERATIONS_TABLES},
        **JOB_GRANTS,
        **QUOTA_GRANTS,
    }
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f"GRANT USAGE ON SCHEMA public TO {worker}")
        # Remove every historical blanket grant before adding the small fixed
        # runtime set. This also repairs databases upgraded through 0010/0012.
        for table in HISTORICAL_WORKSPACE_TABLES:
            quoted_table = schema_editor.connection.ops.quote_name(table)
            cursor.execute(f"REVOKE ALL PRIVILEGES ON TABLE {quoted_table} FROM {worker}")
        for table in CONTENT_FORBIDDEN_TABLES:
            quoted_table = schema_editor.connection.ops.quote_name(table)
            cursor.execute(f"REVOKE ALL PRIVILEGES ON TABLE {quoted_table} FROM {content_worker}")
        for table, privileges in grants.items():
            quoted_table = schema_editor.connection.ops.quote_name(table)
            cursor.execute(f"REVOKE ALL PRIVILEGES ON TABLE {quoted_table} FROM PUBLIC")
            cursor.execute(f"REVOKE ALL PRIVILEGES ON TABLE {quoted_table} FROM {worker}")
            cursor.execute(f"GRANT {privileges} ON TABLE {quoted_table} TO {worker}")
        cursor.execute(f"GRANT USAGE ON SCHEMA public TO {email_worker}")
        cursor.execute("REVOKE ALL PRIVILEGES ON TABLE api_email_outbox FROM PUBLIC")
        cursor.execute(f"REVOKE ALL PRIVILEGES ON TABLE api_email_outbox FROM {worker}")
        cursor.execute(f"REVOKE ALL PRIVILEGES ON TABLE api_email_outbox FROM {content_worker}")
        cursor.execute(f"REVOKE ALL PRIVILEGES ON TABLE api_email_outbox FROM {email_worker}")
        cursor.execute(f"GRANT SELECT, UPDATE ON TABLE api_email_outbox TO {email_worker}")


def remove_worker_runtime_grants(apps, schema_editor):
    """Remove only this migration's grants and policies during a rollback.

    Historical broad worker grants are intentionally never restored. Earlier
    migration reverse functions may then rebuild their own era-specific policy
    shapes without colliding with this migration's consolidated policies.
    """
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    worker = _worker_role(schema_editor)
    email_worker = _email_worker_role(schema_editor)
    with schema_editor.connection.cursor() as cursor:
        for table in (*OPERATIONS_TABLES, *JOB_GRANTS, *QUOTA_GRANTS):
            quoted_table = schema_editor.connection.ops.quote_name(table)
            cursor.execute(f"REVOKE ALL PRIVILEGES ON TABLE {quoted_table} FROM {worker}")
        cursor.execute(f"REVOKE ALL PRIVILEGES ON TABLE api_email_outbox FROM {email_worker}")


class Migration(migrations.Migration):
    dependencies = [
        ("api_schema", "0001_api_auth_and_outbox_tables"),
        ("sitecontent", "0027_destructiveapprovaluse_and_more"),
    ]

    operations = [
        migrations.RunPython(narrow_worker_runtime_grants, remove_worker_runtime_grants),
    ]
