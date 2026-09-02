from __future__ import annotations

import os
import re

from django.db import migrations

ROLE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,62}$")
WORKSPACE_TABLES = (
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
)
RLS_TABLES = (
    "sitecontent_contenttypedefinition",
    "sitecontent_contentrecord",
    "sitecontent_contentrelationship",
    "sitecontent_savedview",
    "sitecontent_assetbinding",
    "sitecontent_importjob",
    "sitecontent_exportjob",
    "sitecontent_workspaceauditevent",
    "sitecontent_mediaasset",
)


def _worker_role(schema_editor) -> tuple[str, str]:
    role = os.environ.get("WORKSPACE_WORKER_DB_USER", "").strip()
    runtime_role = os.environ.get("WORKSPACE_DB_USER", "").strip()
    if not ROLE_NAME.fullmatch(role) or role == runtime_role:
        raise RuntimeError("workspace_worker_role_invalid")
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,))
        if not cursor.fetchone():
            raise RuntimeError("workspace_worker_role_missing")
    return role, schema_editor.connection.ops.quote_name(role)


def configure_worker_role(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    role, quoted_role = _worker_role(schema_editor)
    literal_role = f"'{role}'"
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f"GRANT USAGE ON SCHEMA public TO {quoted_role}")
        for table in WORKSPACE_TABLES:
            cursor.execute(
                f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "{table}" TO {quoted_role}'
            )
        for table in RLS_TABLES:
            policy = f"{table}_tenant_scope"
            cursor.execute(f'DROP POLICY IF EXISTS "{policy}" ON "{table}"')
            cursor.execute(
                f'''CREATE POLICY "{policy}" ON "{table}"
                    USING (site_id = current_setting('app.tenant_id', true)
                           OR current_user = {literal_role})
                    WITH CHECK (site_id = current_setting('app.tenant_id', true)
                                OR current_user = {literal_role})'''
            )


def remove_worker_role(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    _role, quoted_role = _worker_role(schema_editor)
    with schema_editor.connection.cursor() as cursor:
        for table in RLS_TABLES:
            policy = f"{table}_tenant_scope"
            cursor.execute(f'DROP POLICY IF EXISTS "{policy}" ON "{table}"')
            cursor.execute(
                f'''CREATE POLICY "{policy}" ON "{table}"
                    USING (site_id = current_setting('app.tenant_id', true))
                    WITH CHECK (site_id = current_setting('app.tenant_id', true))'''
            )
        for table in reversed(WORKSPACE_TABLES):
            cursor.execute(f'REVOKE ALL PRIVILEGES ON TABLE "{table}" FROM {quoted_role}')
        cursor.execute(f"REVOKE USAGE ON SCHEMA public FROM {quoted_role}")


class Migration(migrations.Migration):
    dependencies = [("sitecontent", "0009_workspace_runtime_role")]
    operations = [migrations.RunPython(configure_worker_role, remove_worker_role)]
