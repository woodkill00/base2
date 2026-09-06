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
    "sitecontent_mediaauditevent",
    "sitecontent_mediadeliverygrant",
    "sitecontent_mediaexportpackage",
    "sitecontent_mediaoutboxevent",
    "sitecontent_mediareference",
    "sitecontent_mediainspectionresult",
    "sitecontent_mediapurgeplan",
    "sitecontent_mediauploadpart",
    "sitecontent_mediaabusecase",
    "sitecontent_mediaencryptionenvelope",
)

COMPOSITE_PARENTS = (
    "sitecontent_mediaasset",
    "sitecontent_mediacollection",
    "sitecontent_mediaobjectversion",
    "sitecontent_mediauploadsession",
    "sitecontent_contentrecord",
)

COMPOSITE_LINKS = (
    ("sitecontent_mediaretentionhold", "asset_id", "sitecontent_mediaasset", "media_hold_asset_scope_fk"),
    ("sitecontent_mediacollectionmembership", "asset_id", "sitecontent_mediaasset", "media_member_asset_scope_fk"),
    ("sitecontent_mediacollectionmembership", "collection_id", "sitecontent_mediacollection", "media_member_collection_scope_fk"),
    ("sitecontent_mediajob", "asset_id", "sitecontent_mediaasset", "media_job_asset_scope_fk"),
    ("sitecontent_mediametadatarevision", "asset_id", "sitecontent_mediaasset", "media_metadata_asset_scope_fk"),
    ("sitecontent_mediaobjectversion", "asset_id", "sitecontent_mediaasset", "media_object_asset_scope_fk"),
    ("sitecontent_mediadeliverygrant", "asset_id", "sitecontent_mediaasset", "media_grant_asset_scope_fk"),
    ("sitecontent_mediareference", "asset_id", "sitecontent_mediaasset", "media_reference_asset_scope_fk"),
    ("sitecontent_mediareference", "content_record_id", "sitecontent_contentrecord", "media_reference_content_scope_fk"),
    ("sitecontent_mediainspectionresult", "object_version_id", "sitecontent_mediaobjectversion", "media_inspection_object_scope_fk"),
    ("sitecontent_mediapurgeplan", "asset_id", "sitecontent_mediaasset", "media_purge_asset_scope_fk"),
    ("sitecontent_mediauploadpart", "session_id", "sitecontent_mediauploadsession", "media_part_session_scope_fk"),
    ("sitecontent_mediaabusecase", "asset_id", "sitecontent_mediaasset", "media_abuse_asset_scope_fk"),
    ("sitecontent_mediaencryptionenvelope", "object_version_id", "sitecontent_mediaobjectversion", "media_envelope_object_scope_fk"),
    ("sitecontent_mediauploadsession", "asset_ref", "sitecontent_mediaasset", "media_upload_asset_scope_fk"),
)


def _worker(schema_editor) -> str:
    worker = os.environ.get("WORKSPACE_WORKER_DB_USER", "").strip()
    if not ROLE_NAME.fullmatch(worker):
        raise RuntimeError("media_security_role_invalid")
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (worker,))
        if not cursor.fetchone():
            raise RuntimeError("media_security_role_missing")
    return worker


def harden_media_boundaries(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    worker = _worker(schema_editor).replace("'", "''")
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "ALTER TABLE sitecontent_mediauploadsession ADD COLUMN asset_ref uuid NULL"
        )
        cursor.execute(
            "CREATE UNIQUE INDEX media_upload_asset_ref_uq "
            "ON sitecontent_mediauploadsession(asset_ref) WHERE asset_ref IS NOT NULL"
        )
        for table in COMPOSITE_PARENTS:
            cursor.execute(
                f'ALTER TABLE "{table}" ADD CONSTRAINT "{table}_site_id_id_uq" '
                "UNIQUE (site_id, id)"
            )
        for table, column, parent, name in COMPOSITE_LINKS:
            cursor.execute(
                f'ALTER TABLE "{table}" ADD CONSTRAINT "{name}" '
                f'FOREIGN KEY (site_id, "{column}") REFERENCES "{parent}" (site_id, id) '
                "NOT VALID"
            )
            cursor.execute(f'ALTER TABLE "{table}" VALIDATE CONSTRAINT "{name}"')
        for table in MEDIA_TABLES:
            legacy = f"{table}_tenant_scope"
            cursor.execute(f'DROP POLICY IF EXISTS "{legacy}" ON "{table}"')
            for suffix in ("select", "insert", "update", "delete"):
                cursor.execute(f'DROP POLICY IF EXISTS "{table}_{suffix}" ON "{table}"')
            tenant = "site_id = current_setting('app.tenant_id', true)"
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


def restore_media_boundaries(apps, schema_editor):
    del apps
    if schema_editor.connection.vendor != "postgresql":
        return
    worker = _worker(schema_editor).replace("'", "''")
    with schema_editor.connection.cursor() as cursor:
        for table in MEDIA_TABLES:
            for suffix in ("select", "insert", "update", "delete"):
                cursor.execute(f'DROP POLICY IF EXISTS "{table}_{suffix}" ON "{table}"')
            legacy = f"{table}_tenant_scope"
            cursor.execute(
                f'''CREATE POLICY "{legacy}" ON "{table}"
                    USING (site_id = current_setting('app.tenant_id', true)
                           OR current_user = '{worker}')
                    WITH CHECK (site_id = current_setting('app.tenant_id', true)
                                OR current_user = '{worker}')'''
            )
        for table, _column, _parent, name in reversed(COMPOSITE_LINKS):
            cursor.execute(f'ALTER TABLE "{table}" DROP CONSTRAINT "{name}"')
        for table in reversed(COMPOSITE_PARENTS):
            cursor.execute(
                f'ALTER TABLE "{table}" DROP CONSTRAINT "{table}_site_id_id_uq"'
            )
        cursor.execute("DROP INDEX media_upload_asset_ref_uq")
        cursor.execute("ALTER TABLE sitecontent_mediauploadsession DROP COLUMN asset_ref")


class Migration(migrations.Migration):
    dependencies = [("sitecontent", "0015_media_portability_and_abuse")]
    operations = [migrations.RunPython(harden_media_boundaries, restore_media_boundaries)]
