from __future__ import annotations

import os
import re

from django.db import migrations

ROLE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,62}$")
ASSET_TABLE = "sitecontent_mediaasset"
VARIANT_TABLE = "sitecontent_mediavariant"


def _worker(schema_editor) -> str:
    worker = os.environ.get("WORKSPACE_WORKER_DB_USER", "").strip()
    if not ROLE_NAME.fullmatch(worker):
        raise RuntimeError("media_security_role_invalid")
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (worker,))
        if not cursor.fetchone():
            raise RuntimeError("media_security_role_missing")
    return worker


def complete_media_worker_boundaries(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    worker = _worker(schema_editor).replace("'", "''")
    tenant = "site_id = current_setting('app.tenant_id', true)"
    with schema_editor.connection.cursor() as cursor:
        table = ASSET_TABLE
        cursor.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
        cursor.execute(f'DROP POLICY IF EXISTS "{table}_tenant_scope" ON "{table}"')
        for suffix in ("select", "insert", "update", "delete"):
            cursor.execute(f'DROP POLICY IF EXISTS "{table}_{suffix}" ON "{table}"')
        cursor.execute(
            f'''CREATE POLICY "{table}_select" ON "{table}" FOR SELECT
                USING ({tenant} OR current_user = '{worker}')'''
        )
        cursor.execute(
            f'''CREATE POLICY "{table}_insert" ON "{table}" FOR INSERT
                WITH CHECK ({tenant})'''
        )
        cursor.execute(
            f'''CREATE POLICY "{table}_update" ON "{table}" FOR UPDATE
                USING ({tenant}) WITH CHECK ({tenant})'''
        )
        cursor.execute(
            f'''CREATE POLICY "{table}_delete" ON "{table}" FOR DELETE
                USING ({tenant})'''
        )

        table = VARIANT_TABLE
        cursor.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        cursor.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
        cursor.execute(f'DROP POLICY IF EXISTS "{table}_tenant_scope" ON "{table}"')
        for suffix in ("select", "insert", "update", "delete"):
            cursor.execute(f'DROP POLICY IF EXISTS "{table}_{suffix}" ON "{table}"')
        tenant_asset = (
            "EXISTS (SELECT 1 FROM sitecontent_mediaasset asset "
            "WHERE asset.id = asset_id "
            "AND asset.site_id = current_setting('app.tenant_id', true))"
        )
        worker_asset = (
            "EXISTS (SELECT 1 FROM sitecontent_mediaasset asset "
            "WHERE asset.id = asset_id)"
        )
        cursor.execute(
            f'''CREATE POLICY "{table}_select" ON "{table}" FOR SELECT
                USING ({tenant_asset} OR (current_user = '{worker}' AND {worker_asset}))'''
        )
        cursor.execute(
            f'''CREATE POLICY "{table}_insert" ON "{table}" FOR INSERT
                WITH CHECK ({tenant_asset})'''
        )
        cursor.execute(
            f'''CREATE POLICY "{table}_update" ON "{table}" FOR UPDATE
                USING ({tenant_asset}) WITH CHECK ({tenant_asset})'''
        )
        cursor.execute(
            f'''CREATE POLICY "{table}_delete" ON "{table}" FOR DELETE
                USING ({tenant_asset})'''
        )


def restore_media_worker_boundaries(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    worker = _worker(schema_editor).replace("'", "''")
    with schema_editor.connection.cursor() as cursor:
        for table in (ASSET_TABLE, VARIANT_TABLE):
            for suffix in ("select", "insert", "update", "delete"):
                cursor.execute(f'DROP POLICY IF EXISTS "{table}_{suffix}" ON "{table}"')
        table = ASSET_TABLE
        cursor.execute(
            f'''CREATE POLICY "{table}_tenant_scope" ON "{table}"
                USING (site_id = current_setting('app.tenant_id', true)
                       OR current_user = '{worker}')
                WITH CHECK (site_id = current_setting('app.tenant_id', true)
                            OR current_user = '{worker}')'''
        )
        cursor.execute(f'ALTER TABLE "{ASSET_TABLE}" NO FORCE ROW LEVEL SECURITY')
        cursor.execute(f'ALTER TABLE "{VARIANT_TABLE}" NO FORCE ROW LEVEL SECURITY')
        cursor.execute(f'ALTER TABLE "{VARIANT_TABLE}" DISABLE ROW LEVEL SECURITY')


class Migration(migrations.Migration):
    dependencies = [("sitecontent", "0016_media_security_boundaries")]
    operations = [
        migrations.RunPython(complete_media_worker_boundaries, restore_media_worker_boundaries)
    ]
