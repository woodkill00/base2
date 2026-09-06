from __future__ import annotations

import os
import re

from django.db import migrations


ROLE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,62}$")
MEDIA_TABLES = (
    "sitecontent_mediacollection",
    "sitecontent_mediacollectionmembership",
    "sitecontent_mediajob",
    "sitecontent_mediametadatarevision",
    "sitecontent_mediaobjectversion",
    "sitecontent_mediaretentionhold",
    "sitecontent_mediauploadsession",
)


def _roles(schema_editor) -> tuple[str, str, str]:
    runtime = os.environ.get("WORKSPACE_DB_USER", "").strip()
    worker = os.environ.get("WORKSPACE_WORKER_DB_USER", "").strip()
    if (
        not ROLE_NAME.fullmatch(runtime)
        or not ROLE_NAME.fullmatch(worker)
        or runtime == worker
    ):
        raise RuntimeError("media_library_role_invalid")
    with schema_editor.connection.cursor() as cursor:
        for role in (runtime, worker):
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,))
            if not cursor.fetchone():
                raise RuntimeError("media_library_role_missing")
    quote = schema_editor.connection.ops.quote_name
    return quote(runtime), quote(worker), f"'{worker}'"


def configure_media_roles(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    runtime, worker, worker_literal = _roles(schema_editor)
    with schema_editor.connection.cursor() as cursor:
        for role in (runtime, worker):
            cursor.execute(f"GRANT USAGE ON SCHEMA public TO {role}")
        for table in MEDIA_TABLES:
            cursor.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "{table}" TO {runtime}')
            cursor.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "{table}" TO {worker}')
            cursor.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
            cursor.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
            policy = f"{table}_tenant_scope"
            cursor.execute(f'DROP POLICY IF EXISTS "{policy}" ON "{table}"')
            cursor.execute(
                f'''CREATE POLICY "{policy}" ON "{table}"
                    USING (site_id = current_setting('app.tenant_id', true)
                           OR current_user = {worker_literal})
                    WITH CHECK (site_id = current_setting('app.tenant_id', true)
                                OR current_user = {worker_literal})'''
            )


def remove_media_roles(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    runtime, worker, _worker_literal = _roles(schema_editor)
    with schema_editor.connection.cursor() as cursor:
        for table in reversed(MEDIA_TABLES):
            policy = f"{table}_tenant_scope"
            cursor.execute(f'DROP POLICY IF EXISTS "{policy}" ON "{table}"')
            cursor.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
            cursor.execute(f'REVOKE ALL PRIVILEGES ON TABLE "{table}" FROM {worker}')
            cursor.execute(f'REVOKE ALL PRIVILEGES ON TABLE "{table}" FROM {runtime}')


class Migration(migrations.Migration):
    dependencies = [("sitecontent", "0011_universal_media_library")]
    operations = [migrations.RunPython(configure_media_roles, remove_media_roles)]
