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


def _role(schema_editor):
    role = os.environ.get("WORKSPACE_DB_USER", "").strip()
    if not ROLE_NAME.fullmatch(role):
        raise RuntimeError("workspace_runtime_role_invalid")
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,))
        if not cursor.fetchone():
            raise RuntimeError("workspace_runtime_role_missing")
    return schema_editor.connection.ops.quote_name(role)


def grant_workspace_runtime(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    role = _role(schema_editor)
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f"GRANT USAGE ON SCHEMA public TO {role}")
        for table in WORKSPACE_TABLES:
            cursor.execute(
                f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "{table}" TO {role}'
            )


def revoke_workspace_runtime(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    role = _role(schema_editor)
    with schema_editor.connection.cursor() as cursor:
        for table in reversed(WORKSPACE_TABLES):
            cursor.execute(f'REVOKE ALL PRIVILEGES ON TABLE "{table}" FROM {role}')
        cursor.execute(f"REVOKE USAGE ON SCHEMA public FROM {role}")


class Migration(migrations.Migration):
    dependencies = [("sitecontent", "0008_exportjob_projection_fields")]
    operations = [migrations.RunPython(grant_workspace_runtime, revoke_workspace_runtime)]
