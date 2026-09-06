#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from uuid import UUID

import psycopg2
from psycopg2 import errors

TABLES = (
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
HARDENED_TABLES = (
    "sitecontent_mediaasset",
    "sitecontent_mediavariant",
)

TENANT_CONSTRAINTS = (
    "media_hold_asset_scope_fk",
    "media_member_asset_scope_fk",
    "media_member_collection_scope_fk",
    "media_job_asset_scope_fk",
    "media_metadata_asset_scope_fk",
    "media_object_asset_scope_fk",
    "media_grant_asset_scope_fk",
    "media_reference_asset_scope_fk",
    "media_reference_content_scope_fk",
    "media_inspection_object_scope_fk",
    "media_purge_asset_scope_fk",
    "media_part_session_scope_fk",
    "media_abuse_asset_scope_fk",
    "media_envelope_object_scope_fk",
    "media_upload_asset_scope_fk",
)


def connect(user: str, password: str):
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ["DB_NAME"],
        user=user,
        password=password,
    )


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "forward"
    owner_user = os.environ["DB_USER"]
    owner_password = os.environ["DB_PASSWORD"]
    runtime_user = os.environ["WORKSPACE_DB_USER"]
    runtime_password = os.environ["WORKSPACE_DB_PASSWORD"]
    worker_user = os.environ["WORKSPACE_WORKER_DB_USER"]
    worker_password = os.environ["WORKSPACE_WORKER_DB_PASSWORD"]

    owner = connect(owner_user, owner_password)
    try:
        with owner, owner.cursor() as cursor:
            cursor.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename = ANY(%s)",
                (list(TABLES),),
            )
            present = {row[0] for row in cursor.fetchall()}
            if mode == "reversed":
                assert not present, f"media_tables_remain_after_reverse:{sorted(present)}"
                print("Media PostgreSQL reverse acceptance: PASS")
                return
            assert present == set(TABLES), f"media_table_inventory_mismatch:{sorted(present)}"
            cursor.execute(
                """SELECT cls.relname, cls.relrowsecurity, cls.relforcerowsecurity
                   FROM pg_class AS cls
                   JOIN pg_namespace AS ns ON ns.oid = cls.relnamespace
                   WHERE ns.nspname='public' AND cls.relname = ANY(%s)""",
                (list(TABLES + HARDENED_TABLES),),
            )
            assert all(row[1:] == (True, True) for row in cursor.fetchall())
            cursor.execute(
                """SELECT tablename, policyname, cmd, qual, with_check FROM pg_policies
                   WHERE schemaname='public' AND tablename = ANY(%s)""",
                (list(TABLES + HARDENED_TABLES),),
            )
            policies = {}
            for table, policy, command, qualifier, check in cursor.fetchall():
                policies.setdefault(table, {})[command] = (policy, qualifier or "", check or "")
            assert set(policies) == set(
                TABLES + HARDENED_TABLES
            ), f"media_policy_inventory_mismatch:{policies}"
            for table in TABLES + HARDENED_TABLES:
                commands = policies[table]
                assert set(commands) == {"SELECT", "INSERT", "UPDATE", "DELETE"}, commands
                assert "current_user" in commands["SELECT"][1].lower()
                assert "current_user" not in commands["INSERT"][2].lower()
                assert "current_user" not in (
                    commands["UPDATE"][1] + commands["UPDATE"][2]
                ).lower()
                assert "current_user" not in commands["DELETE"][1].lower()
            cursor.execute(
                """SELECT conname, convalidated FROM pg_constraint
                   WHERE conname = ANY(%s)""",
                (list(TENANT_CONSTRAINTS),),
            )
            constraints = dict(cursor.fetchall())
            assert constraints == {name: True for name in TENANT_CONSTRAINTS}, constraints
            cursor.execute(
                """SELECT COUNT(*) FROM pg_indexes
                   WHERE schemaname='public' AND indexname='media_upload_asset_ref_uq'"""
            )
            assert cursor.fetchone()[0] == 1
            for role in (runtime_user, worker_user):
                cursor.execute(
                    "SELECT rolbypassrls, rolsuper, rolcreaterole FROM pg_roles WHERE rolname=%s",
                    (role,),
                )
                assert cursor.fetchone() == (False, False, False)
            cursor.execute("DELETE FROM sitecontent_mediavariant")
            cursor.execute("DELETE FROM sitecontent_mediaasset")
            cursor.execute("DELETE FROM sitecontent_mediacollection")
            cursor.execute(
                """INSERT INTO sitecontent_mediacollection
                   (id,site_id,title,owner_ref,visibility,shared_roles,lock_version,created_at,updated_at)
                   VALUES (%s,'site-a','Tenant A','owner','private','[]',1,NOW(),NOW()),
                          (%s,'site-b','Tenant B','owner','private','[]',1,NOW(),NOW())""",
                (str(UUID(int=601)), str(UUID(int=602))),
            )
            cursor.execute(
                """INSERT INTO sitecontent_mediaasset
                   (id,site_id,storage_key,original_name,media_type,byte_size,sha256,status,
                    owner_ref,attribution,retention_until,metadata,visibility,current_object_version,
                    authorization_epoch,lock_version,deleted_at,created_at,updated_at)
                   VALUES (%s,'site-a','a.bin','a.bin','application/octet-stream',1,%s,
                           'quarantined','owner','','2099-01-01','{}','private',1,1,1,NULL,NOW(),NOW()),
                          (%s,'site-b','b.bin','b.bin','application/octet-stream',1,%s,
                           'quarantined','owner','','2099-01-01','{}','private',1,1,1,NULL,NOW(),NOW())""",
                (str(UUID(int=610)), "a" * 64, str(UUID(int=611)), "b" * 64),
            )
            cursor.execute(
                """INSERT INTO sitecontent_mediavariant
                   (id,asset_id,name,storage_key,media_type,byte_size,sha256,width,height,
                    inline_safe,processor_ref,recipe_id,recipe_version,source_sha256,created_at)
                   VALUES (%s,%s,'safe','a-safe.bin','application/octet-stream',1,%s,NULL,NULL,
                           FALSE,'test','test-v1',1,%s,NOW()),
                          (%s,%s,'safe','b-safe.bin','application/octet-stream',1,%s,NULL,NULL,
                           FALSE,'test','test-v1',1,%s,NOW())""",
                (
                    str(UUID(int=620)), str(UUID(int=610)), "c" * 64, "a" * 64,
                    str(UUID(int=621)), str(UUID(int=611)), "d" * 64, "b" * 64,
                ),
            )

        runtime = connect(runtime_user, runtime_password)
        worker = connect(worker_user, worker_password)
        try:
            with runtime, runtime.cursor() as cursor:
                cursor.execute("SELECT set_config('app.tenant_id', 'site-a', true)")
                cursor.execute("SELECT title FROM sitecontent_mediacollection ORDER BY title")
                assert cursor.fetchall() == [("Tenant A",)]
                try:
                    cursor.execute(
                        """INSERT INTO sitecontent_mediacollection
                           (id,site_id,title,owner_ref,visibility,shared_roles,lock_version,created_at,updated_at)
                           VALUES (%s,'site-b','Blocked','owner','private','[]',1,NOW(),NOW())""",
                        (str(UUID(int=603)),),
                    )
                except errors.InsufficientPrivilege:
                    runtime.rollback()
                else:
                    raise AssertionError("media_cross_tenant_insert_was_not_blocked")
            with worker, worker.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM sitecontent_mediacollection")
                assert cursor.fetchone()[0] == 2
                cursor.execute("SELECT COUNT(*) FROM sitecontent_mediaasset")
                assert cursor.fetchone()[0] == 2
                cursor.execute("SELECT COUNT(*) FROM sitecontent_mediavariant")
                assert cursor.fetchone()[0] == 2
                try:
                    cursor.execute(
                        """INSERT INTO sitecontent_mediacollection
                           (id,site_id,title,owner_ref,visibility,shared_roles,lock_version,created_at,updated_at)
                           VALUES (%s,'site-b','Worker blocked','worker','private','[]',1,NOW(),NOW())""",
                        (str(UUID(int=604)),),
                    )
                except errors.InsufficientPrivilege:
                    worker.rollback()
                else:
                    raise AssertionError("media_worker_unscoped_mutation_was_not_blocked")
            with worker, worker.cursor() as cursor:
                cursor.execute(
                    "UPDATE sitecontent_mediaasset SET original_name='unbound'"
                )
                assert cursor.rowcount == 0, "media_asset_unbound_update_was_not_blocked"
                cursor.execute(
                    "UPDATE sitecontent_mediavariant SET storage_key='unbound'"
                )
                assert cursor.rowcount == 0, "media_variant_unbound_update_was_not_blocked"
            with worker, worker.cursor() as cursor:
                cursor.execute("SELECT set_config('app.tenant_id', 'site-a', true)")
                try:
                    cursor.execute(
                        """INSERT INTO sitecontent_mediacollection
                           (id,site_id,title,owner_ref,visibility,shared_roles,lock_version,created_at,updated_at)
                           VALUES (%s,'site-b','Worker cross tenant','worker','private','[]',1,NOW(),NOW())""",
                        (str(UUID(int=605)),),
                    )
                except errors.InsufficientPrivilege:
                    worker.rollback()
                else:
                    raise AssertionError("media_worker_cross_tenant_mutation_was_not_blocked")
            with worker, worker.cursor() as cursor:
                cursor.execute("SELECT set_config('app.tenant_id', 'site-a', true)")
                cursor.execute(
                    "UPDATE sitecontent_mediaasset SET original_name='a-updated' WHERE site_id='site-a'"
                )
                assert cursor.rowcount == 1
                cursor.execute(
                    "UPDATE sitecontent_mediaasset SET original_name='blocked' WHERE site_id='site-b'"
                )
                assert cursor.rowcount == 0, "media_asset_cross_tenant_update_was_not_blocked"
                cursor.execute(
                    """UPDATE sitecontent_mediavariant SET storage_key='a-updated.bin'
                       WHERE asset_id=%s""",
                    (str(UUID(int=610)),),
                )
                assert cursor.rowcount == 1
                cursor.execute(
                    """UPDATE sitecontent_mediavariant SET storage_key='blocked.bin'
                       WHERE asset_id=%s""",
                    (str(UUID(int=611)),),
                )
                assert cursor.rowcount == 0, "media_variant_cross_tenant_update_was_not_blocked"
            with worker, worker.cursor() as cursor:
                cursor.execute("SELECT set_config('app.tenant_id', 'site-b', true)")
                cursor.execute(
                    "UPDATE sitecontent_mediaasset SET original_name='b-updated' WHERE site_id='site-b'"
                )
                assert cursor.rowcount == 1
                cursor.execute(
                    "UPDATE sitecontent_mediaasset SET original_name='blocked' WHERE site_id='site-a'"
                )
                assert cursor.rowcount == 0, "media_asset_reverse_cross_tenant_update_not_blocked"
                cursor.execute(
                    """UPDATE sitecontent_mediavariant SET storage_key='b-updated.bin'
                       WHERE asset_id=%s""",
                    (str(UUID(int=611)),),
                )
                assert cursor.rowcount == 1
                cursor.execute(
                    """UPDATE sitecontent_mediavariant SET storage_key='blocked.bin'
                       WHERE asset_id=%s""",
                    (str(UUID(int=610)),),
                )
                assert cursor.rowcount == 0, "media_variant_reverse_cross_tenant_update_not_blocked"
            with owner, owner.cursor() as cursor:
                cursor.execute(
                    "SELECT site_id,original_name FROM sitecontent_mediaasset ORDER BY site_id"
                )
                assert cursor.fetchall() == [
                    ('site-a', 'a-updated'), ('site-b', 'b-updated')
                ]
                cursor.execute(
                    """SELECT asset.site_id,variant.storage_key
                       FROM sitecontent_mediavariant variant
                       JOIN sitecontent_mediaasset asset ON asset.id=variant.asset_id
                       ORDER BY asset.site_id"""
                )
                assert cursor.fetchall() == [
                    ('site-a', 'a-updated.bin'), ('site-b', 'b-updated.bin')
                ]
        finally:
            runtime.close()
            worker.close()
    finally:
        owner.close()
    print("Media PostgreSQL RLS acceptance: PASS")


if __name__ == "__main__":
    main()
