#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
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
                assert "current_user" not in (commands["UPDATE"][1] + commands["UPDATE"][2]).lower()
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
                    str(UUID(int=620)),
                    str(UUID(int=610)),
                    "c" * 64,
                    "a" * 64,
                    str(UUID(int=621)),
                    str(UUID(int=611)),
                    "d" * 64,
                    "b" * 64,
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
                cursor.execute("UPDATE sitecontent_mediaasset SET original_name='unbound'")
                assert cursor.rowcount == 0, "media_asset_unbound_update_was_not_blocked"
                cursor.execute("UPDATE sitecontent_mediavariant SET storage_key='unbound'")
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
                assert cursor.fetchall() == [("site-a", "a-updated"), ("site-b", "b-updated")]
                cursor.execute(
                    """SELECT asset.site_id,variant.storage_key
                       FROM sitecontent_mediavariant variant
                       JOIN sitecontent_mediaasset asset ON asset.id=variant.asset_id
                       ORDER BY asset.site_id"""
                )
                assert cursor.fetchall() == [
                    ("site-a", "a-updated.bin"),
                    ("site-b", "b-updated.bin"),
                ]

            # Exercise the production lease helpers against real RLS. Two
            # overlapping schedulers may discover the same asset, but the
            # tenant-bound CAS must return exactly one delivery token.
            with owner, owner.cursor() as cursor:
                cursor.execute(
                    """UPDATE sitecontent_mediaasset
                       SET metadata=%s::jsonb,updated_at=NOW()
                       WHERE site_id='site-a' AND id=%s""",
                    ('{"admission":"content_verified"}', str(UUID(int=610))),
                )
            from api.db import close_pool
            from api.repositories.media_library import PostgresMediaLibraryRepository
            from api.services.content_workspace_worker import (
                begin_media_scan_attempt,
                due_media_scans,
                finish_media_scan_attempt,
                recover_media_scan_attempt,
            )
            from api.services.media_library_runtime import due_media_exports

            # Exercise the exact tenant-wide export admission lock and quota.
            # Exact replay remains available at capacity while new work fails
            # closed, and global discovery interleaves tenant ranks.
            with owner, owner.cursor() as cursor:
                for index in range(10):
                    cursor.execute(
                        """INSERT INTO sitecontent_mediaexportpackage
                           (id,site_id,requested_by,output_format,projection,status,
                            artifact_key,artifact_sha256,request_digest,expires_at,error_code,
                            created_at,updated_at)
                           VALUES (%s,'site-a','user:test','csv','{}'::jsonb,'queued',
                                   '','',%s,NOW()+INTERVAL '1 hour','',
                                   NOW()+(%s*INTERVAL '1 second'),NOW())""",
                        (str(UUID(int=700 + index)), f"{index:064x}", index),
                    )
                for index in range(2):
                    cursor.execute(
                        """INSERT INTO sitecontent_mediaexportpackage
                           (id,site_id,requested_by,output_format,projection,status,
                            artifact_key,artifact_sha256,request_digest,expires_at,error_code,
                            created_at,updated_at)
                           VALUES (%s,'site-b','user:test','csv','{}'::jsonb,'queued',
                                   '','',%s,NOW()+INTERVAL '1 hour','',
                                   NOW()+((20+%s)*INTERVAL '1 second'),NOW())""",
                        (str(UUID(int=800 + index)), f"{index + 100:064x}", index),
                    )
            export_repository = PostgresMediaLibraryRepository()
            replay = export_repository.create_export(
                site_id="site-a",
                actor_ref="user:test",
                output_format="csv",
                projection={},
                request_digest=f"{0:064x}",
                expires_at=datetime.now().astimezone(),
                maximum_outstanding=10,
            )
            assert replay["replayed"] is True
            try:
                export_repository.create_export(
                    site_id="site-a",
                    actor_ref="user:test",
                    output_format="csv",
                    projection={},
                    request_digest="f" * 64,
                    expires_at=datetime.now().astimezone(),
                    maximum_outstanding=10,
                )
            except ValueError as exc:
                assert str(exc) == "media_export_capacity_exceeded"
            else:
                raise AssertionError("media_export_capacity_was_not_enforced")
            fair = due_media_exports(limit=4)
            assert [site for site, _identifier in fair] == [
                "site-a",
                "site-b",
                "site-a",
                "site-b",
            ], f"media_export_discovery_unfair:{fair}"

            with ThreadPoolExecutor(max_workers=2) as executor:
                deliveries = list(executor.map(lambda _index: due_media_scans(limit=10), range(2)))
            claims = [claim for batch in deliveries for claim in batch]
            assert len(claims) == 1, f"media_overlapping_scheduler_duplicate:{claims}"
            site_id, asset_id, job_id, attempt, lease_value = claims[0]
            lease_token = datetime.fromisoformat(lease_value)
            assert attempt == 1
            assert begin_media_scan_attempt(
                site_id=site_id,
                asset_id=UUID(asset_id),
                job_id=UUID(job_id),
                attempt=attempt,
                lease_token=lease_token,
            )
            assert not begin_media_scan_attempt(
                site_id=site_id,
                asset_id=UUID(asset_id),
                job_id=UUID(job_id),
                attempt=attempt,
                lease_token=lease_token,
            ), "media_duplicate_delivery_was_not_noop"

            with worker, worker.cursor() as cursor:
                cursor.execute("SELECT set_config('app.tenant_id', 'site-a', true)")
                cursor.execute(
                    """UPDATE sitecontent_mediajob
                       SET status='retryable',attempt=%s,available_at=NOW()
                       WHERE site_id=%s AND id=%s""",
                    (attempt, site_id, job_id),
                )
                assert cursor.rowcount == 1
            finish_media_scan_attempt(
                site_id=site_id,
                job_id=UUID(job_id),
                attempt=attempt,
                lease_token=lease_token,
                result="quarantined",
            )
            assert due_media_scans(limit=10) == [], "media_retry_backoff_was_not_enforced"

            # A crashed running attempt becomes claimable only after its exact
            # lease expires. The old token remains unusable after recovery.
            with worker, worker.cursor() as cursor:
                cursor.execute("SELECT set_config('app.tenant_id', 'site-a', true)")
                cursor.execute(
                    """UPDATE sitecontent_mediajob
                       SET status='running',available_at=NOW()-INTERVAL '1 minute',
                           lease_expires_at=NOW()-INTERVAL '1 second'
                       WHERE site_id=%s AND id=%s""",
                    (site_id, job_id),
                )
                assert cursor.rowcount == 1
            recovered = due_media_scans(limit=10)
            assert len(recovered) == 1 and recovered[0][3] == 2, recovered
            recovered_token = datetime.fromisoformat(recovered[0][4])
            assert recovered_token != lease_token
            assert not begin_media_scan_attempt(
                site_id=site_id,
                asset_id=UUID(asset_id),
                job_id=UUID(job_id),
                attempt=attempt,
                lease_token=lease_token,
            )
            assert begin_media_scan_attempt(
                site_id=site_id,
                asset_id=UUID(asset_id),
                job_id=UUID(job_id),
                attempt=2,
                lease_token=recovered_token,
            )
            finish_media_scan_attempt(
                site_id=site_id,
                job_id=UUID(job_id),
                attempt=2,
                lease_token=recovered_token,
                result="scanned_infected",
            )
            with owner, owner.cursor() as cursor:
                cursor.execute(
                    """SELECT status,attempt,error_code,lease_expires_at
                       FROM sitecontent_mediajob WHERE id=%s""",
                    (job_id,),
                )
                assert cursor.fetchone() == ("failed", 2, "media_inspection_rejected", None)

                cursor.execute(
                    """INSERT INTO sitecontent_mediaasset
                       (id,site_id,storage_key,original_name,media_type,byte_size,sha256,status,
                        owner_ref,attribution,retention_until,metadata,visibility,
                        current_object_version,authorization_epoch,lock_version,deleted_at,
                        created_at,updated_at)
                       VALUES (%s,'site-a','superseded.bin','superseded.bin',
                               'application/octet-stream',1,%s,'quarantined','owner','',
                               '2099-01-01',%s::jsonb,'private',1,1,1,NULL,NOW(),NOW())""",
                    (
                        str(UUID(int=612)),
                        "f" * 64,
                        '{"admission":"content_verified"}',
                    ),
                )
            superseded_claims = due_media_scans(limit=10)
            assert len(superseded_claims) == 1, superseded_claims
            sup_site, sup_asset, sup_job, sup_attempt, sup_lease = superseded_claims[0]
            sup_token = datetime.fromisoformat(sup_lease)
            assert begin_media_scan_attempt(
                site_id=sup_site,
                asset_id=UUID(sup_asset),
                job_id=UUID(sup_job),
                attempt=sup_attempt,
                lease_token=sup_token,
            )
            with owner, owner.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO sitecontent_mediaabusecase
                       (id,site_id,asset_id,reporter_ref,reviewer_ref,appellant_ref,
                        reason_code,status,lock_version,created_at,updated_at)
                       VALUES (%s,'site-a',%s,'user:reporter','user:reviewer','',
                               'media_abuse_reviewed','quarantined',1,NOW(),NOW())""",
                    (str(UUID(int=630)), sup_asset),
                )
            from api.services.media_library_runtime import apply_due_media_governance

            assert apply_due_media_governance(limit=10) == {
                "holdsExpired": 0,
                "abuseCasesEnforced": 1,
            }
            finish_media_scan_attempt(
                site_id=sup_site,
                job_id=UUID(sup_job),
                attempt=sup_attempt,
                lease_token=sup_token,
                result="not_ready",
            )
            with owner, owner.cursor() as cursor:
                cursor.execute(
                    """SELECT job.status,job.attempt,job.error_code,job.lease_expires_at,
                              asset.status
                       FROM sitecontent_mediajob job
                       JOIN sitecontent_mediaasset asset ON asset.id=job.asset_id
                       WHERE job.id=%s""",
                    (sup_job,),
                )
                assert cursor.fetchone() == (
                    "cancelled",
                    1,
                    "media_scan_superseded",
                    None,
                    "archived",
                )
                cursor.execute(
                    """SELECT event_type,actor_ref,detail
                       FROM sitecontent_mediaauditevent
                       WHERE site_id='site-a' AND subject_ref=%s
                       ORDER BY sequence DESC LIMIT 1""",
                    (f"asset:{sup_asset}",),
                )
                event_type, actor_ref, detail = cursor.fetchone()
                assert event_type == "media.inspection.superseded"
                assert actor_ref == "system:media-worker"
                assert detail == {
                    "code": "media_scan_superseded",
                    "status": "cancelled",
                    "reason": "asset_ineligible",
                    "count": 1,
                }
            assert due_media_scans(limit=10) == [], "superseded_scan_was_rediscovered"

            delayed_asset = UUID(int=613)
            delayed_version = 3
            delayed_digest = hashlib.sha256(
                f"site-a\0{delayed_asset}\0owner\0soft_deleted\0{delayed_version}".encode()
            ).hexdigest()
            with owner, owner.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO sitecontent_mediaasset
                       (id,site_id,storage_key,original_name,media_type,byte_size,sha256,status,
                        owner_ref,attribution,retention_until,metadata,visibility,
                        current_object_version,authorization_epoch,lock_version,deleted_at,
                        created_at,updated_at)
                       VALUES (%s,'site-a','purged.bin','purged.bin','application/octet-stream',
                               1,%s,'purged','owner','','2099-01-01','{}','private',1,1,8,
                               NOW(),NOW(),NOW())""",
                    (str(delayed_asset), "9" * 64),
                )
                cursor.execute(
                    """INSERT INTO sitecontent_mediaoutboxevent
                       (id,site_id,aggregate_ref,event_kind,idempotency_key,payload_digest,
                        status,attempt,maximum_attempts,available_at,error_code,created_at,updated_at)
                       VALUES (%s,'site-a',%s,'asset.soft_deleted','delayed-delete',%s,
                               'completed',1,5,NOW(),'',NOW(),NOW())""",
                    (
                        str(UUID(int=640)),
                        f"asset:{delayed_asset}",
                        delayed_digest,
                    ),
                )
            from api.repositories.media_library import PostgresMediaLibraryRepository

            media_repository = PostgresMediaLibraryRepository()
            assert media_repository.transition_asset(
                site_id="site-a",
                asset_id=delayed_asset,
                actor_ref="owner",
                target="soft_deleted",
                expected_version=delayed_version,
                idempotency_key="delayed-delete",
            ) == {
                "id": str(delayed_asset),
                "status": "soft_deleted",
                "version": 4,
                "replayed": True,
            }
            try:
                media_repository.transition_asset(
                    site_id="site-a",
                    asset_id=delayed_asset,
                    actor_ref="owner",
                    target="archived",
                    expected_version=delayed_version,
                    idempotency_key="delayed-delete",
                )
            except ValueError as exc:
                assert str(exc) == "media_idempotency_conflict"
            else:
                raise AssertionError("media_changed_delayed_replay_was_not_rejected")
            try:
                media_repository.transition_asset(
                    site_id="site-a",
                    asset_id=delayed_asset,
                    actor_ref="owner",
                    target="archived",
                    expected_version=8,
                    idempotency_key="new-after-purge",
                )
            except ValueError as exc:
                assert str(exc) == "media_not_found"
            else:
                raise AssertionError("media_new_purge_state_mutation_was_not_rejected")

            with owner, owner.cursor() as cursor:
                cursor.execute(
                    """UPDATE sitecontent_mediaasset
                       SET metadata=%s::jsonb,updated_at=NOW()
                       WHERE site_id='site-b' AND id=%s""",
                    ('{"admission":"content_verified"}', str(UUID(int=611))),
                )
            clean_claims = due_media_scans(limit=10)
            assert len(clean_claims) == 1 and clean_claims[0][0] == "site-b", clean_claims
            clean_site, clean_asset, clean_job, clean_attempt, clean_lease = clean_claims[0]
            clean_token = datetime.fromisoformat(clean_lease)
            assert begin_media_scan_attempt(
                site_id=clean_site,
                asset_id=UUID(clean_asset),
                job_id=UUID(clean_job),
                attempt=clean_attempt,
                lease_token=clean_token,
            )
            finish_media_scan_attempt(
                site_id=clean_site,
                job_id=UUID(clean_job),
                attempt=clean_attempt,
                lease_token=clean_token,
                result="validated_safe_derivative",
            )
            with owner, owner.cursor() as cursor:
                cursor.execute(
                    """SELECT status,attempt,error_code,output_digest,lease_expires_at
                       FROM sitecontent_mediajob WHERE id=%s""",
                    (clean_job,),
                )
                clean_row = cursor.fetchone()
                assert clean_row == ("completed", 1, "", "b" * 64, None), clean_row
                cursor.execute(
                    """UPDATE sitecontent_mediaasset
                       SET current_object_version=2,sha256=%s,status='quarantined',updated_at=NOW()
                       WHERE site_id='site-b' AND id=%s""",
                    ("e" * 64, str(UUID(int=611))),
                )
            exception_claims = due_media_scans(limit=10)
            assert len(exception_claims) == 1, exception_claims
            error_site, error_asset, error_job, error_attempt, error_lease = exception_claims[0]
            error_token = datetime.fromisoformat(error_lease)
            assert begin_media_scan_attempt(
                site_id=error_site,
                asset_id=UUID(error_asset),
                job_id=UUID(error_job),
                attempt=error_attempt,
                lease_token=error_token,
            )
            assert recover_media_scan_attempt(
                site_id=error_site,
                job_id=UUID(error_job),
                attempt=error_attempt,
                lease_token=error_token,
            )
            with owner, owner.cursor() as cursor:
                cursor.execute(
                    """SELECT status,attempt,error_code,lease_expires_at,available_at>NOW()
                       FROM sitecontent_mediajob WHERE id=%s""",
                    (error_job,),
                )
                assert cursor.fetchone() == (
                    "retryable",
                    1,
                    "media_dependency_unavailable",
                    None,
                    True,
                )
            assert due_media_scans(limit=10) == [], "media_exception_backoff_was_not_enforced"
            close_pool()
        finally:
            runtime.close()
            worker.close()
    finally:
        owner.close()
    print("Media PostgreSQL RLS acceptance: PASS")


if __name__ == "__main__":
    main()
