#!/usr/bin/env python3
from __future__ import annotations

import os
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import psycopg2
from psycopg2 import errors

from api.migrations.runner import apply_migrations
from api.repositories.operations import due_alert_deliveries, record_probe_batch
from api.repositories.runtime_governance import claim_jobs, enqueue_job, settle_job
from api.repositories.tenant_quota import QuotaRepositoryError, reserve
from api.services.email_service import create_outbox_email
from scripts.python.production_backup import _repeatable_read_snapshot


def connect(user: str, password: str):
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ["DB_NAME"],
        user=user,
        password=password,
    )


def count(conn, tenant: str | None) -> int:
    with conn.cursor() as cursor:
        if tenant is not None:
            cursor.execute("SELECT set_config('app.tenant_id', %s, true)", (tenant,))
        cursor.execute("SELECT COUNT(*) FROM sitecontent_contenttypedefinition")
        return int(cursor.fetchone()[0])


def operations_count(conn, tenant: str | None) -> int:
    with conn.cursor() as cursor:
        if tenant is not None:
            cursor.execute("SELECT set_config('app.tenant_id', %s, true)", (tenant,))
        cursor.execute("SELECT COUNT(*) FROM sitecontent_operationsservice")
        return int(cursor.fetchone()[0])


def quota_count(conn, tenant: str | None) -> int:
    with conn.cursor() as cursor:
        if tenant is not None:
            cursor.execute("SELECT set_config('app.tenant_id', %s, true)", (tenant,))
        cursor.execute("SELECT COUNT(*) FROM sitecontent_tenantquota")
        return int(cursor.fetchone()[0])


def outbox_count(conn) -> int:
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM api_email_outbox")
        return int(cursor.fetchone()[0])


def data_rights_count(conn) -> int:
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM api_data_rights_operations")
        return int(cursor.fetchone()[0])


def auth_user_count(conn) -> int:
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM api_auth_users")
        return int(cursor.fetchone()[0])


def insert_outbox(conn) -> None:
    with conn.cursor() as cursor:
        cursor.execute(
            "INSERT INTO api_email_outbox "
            "(id,to_email,subject,body_text) VALUES (%s,'x@example.invalid','x','x')",
            (str(UUID(int=41)),),
        )


def assert_permission_denied(call, connection, marker: str) -> None:
    try:
        call()
    except errors.InsufficientPrivilege:
        connection.rollback()
    else:
        raise AssertionError(marker)


def quota_reservation_race() -> None:
    """Prove two real API-role sessions cannot over-reserve one quota."""
    barrier = threading.Barrier(2)
    results: list[str] = []
    result_lock = threading.Lock()

    def contender(index: int) -> None:
        barrier.wait(timeout=5)
        try:
            result = reserve(
                tenant_id="site-a",
                quota_key="jobs",
                amount=6,
                reservation_id=f"job.race-{index}",
            )
            outcome = result["status"]
        except QuotaRepositoryError as exc:
            outcome = str(exc)
        with result_lock:
            results.append(outcome)

    contenders = [
        threading.Thread(target=contender, args=(index,), daemon=True) for index in (1, 2)
    ]
    for contender_thread in contenders:
        contender_thread.start()
    for contender_thread in contenders:
        contender_thread.join(timeout=10)
        assert not contender_thread.is_alive(), "quota_concurrency_contender_timed_out"
    assert sorted(results) == ["quota:exhausted", "reserved"], results


def optimistic_race(
    *,
    runtime_user: str,
    runtime_password: str,
    statement: str,
    parameters: tuple,
) -> None:
    """Prove two physical sessions cannot both win one guarded mutation."""
    barrier = threading.Barrier(2)
    results: list[int] = []
    failures: list[BaseException] = []
    result_lock = threading.Lock()

    def contender() -> None:
        connection = connect(runtime_user, runtime_password)
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('app.tenant_id', 'site-a', true)")
                barrier.wait(timeout=5)
                cursor.execute(statement, parameters)
                affected = cursor.rowcount
            connection.commit()
            with result_lock:
                results.append(affected)
        except BaseException as exc:  # pragma: no cover - surfaced by parent assertion
            connection.rollback()
            with result_lock:
                failures.append(exc)
        finally:
            connection.close()

    contenders = [threading.Thread(target=contender, daemon=True) for _ in range(2)]
    for contender_thread in contenders:
        contender_thread.start()
    for contender_thread in contenders:
        contender_thread.join(timeout=10)
        assert not contender_thread.is_alive(), "workspace_concurrency_contender_timed_out"
    assert not failures, failures
    assert sorted(results) == [0, 1], results


def migration_lock_race() -> None:
    barrier = threading.Barrier(2)
    failures: list[BaseException] = []

    def contender() -> None:
        try:
            barrier.wait(timeout=5)
            apply_migrations()
        except BaseException as exc:  # pragma: no cover - surfaced below
            failures.append(exc)

    contenders = [threading.Thread(target=contender, daemon=True) for _ in range(2)]
    for contender in contenders:
        contender.start()
    for contender in contenders:
        contender.join(timeout=20)
        assert not contender.is_alive(), "api_migration_lock_contender_timed_out"
    assert not failures, failures


def main() -> None:
    owner_user = os.environ["DB_USER"]
    owner_password = os.environ["DB_PASSWORD"]
    runtime_user = os.environ["WORKSPACE_DB_USER"]
    runtime_password = os.environ["WORKSPACE_DB_PASSWORD"]
    api_runtime_user = os.environ["API_RUNTIME_DB_USER"]
    api_runtime_password = os.environ["API_RUNTIME_DB_PASSWORD"]
    content_worker_user = os.environ["WORKSPACE_WORKER_DB_USER"]
    content_worker_password = os.environ["WORKSPACE_WORKER_DB_PASSWORD"]
    worker_user = os.environ["RUNTIME_WORKER_DB_USER"]
    worker_password = os.environ["RUNTIME_WORKER_DB_PASSWORD"]
    email_worker_user = os.environ["EMAIL_WORKER_DB_USER"]
    email_worker_password = os.environ["EMAIL_WORKER_DB_PASSWORD"]
    data_rights_user = os.environ["DATA_RIGHTS_WORKER_DB_USER"]
    data_rights_password = os.environ["DATA_RIGHTS_WORKER_DB_PASSWORD"]
    owner = connect(owner_user, owner_password)
    api_runtime = connect(api_runtime_user, api_runtime_password)
    runtime = connect(runtime_user, runtime_password)
    content_worker = connect(content_worker_user, content_worker_password)
    worker = connect(worker_user, worker_password)
    email_worker = connect(email_worker_user, email_worker_password)
    data_rights_worker = connect(data_rights_user, data_rights_password)
    try:
        # Exercise the real API ledger concurrently before relying on any
        # API-side columns below. Both contenders must converge under the
        # transaction-scoped PostgreSQL advisory lock.
        migration_lock_race()
        with owner, owner.cursor() as cursor:
            cursor.execute("DELETE FROM api_data_rights_operations")
            cursor.execute("DELETE FROM api_identity_memberships")
            cursor.execute("DELETE FROM api_identity_organizations")
            cursor.execute("DELETE FROM api_auth_refresh_tokens")
            cursor.execute("DELETE FROM api_auth_users")
            cursor.execute("DELETE FROM sitecontent_tenantlifecycleevent")
            cursor.execute("DELETE FROM sitecontent_tenantlifecyclestate")
            cursor.execute("DELETE FROM sitecontent_tenantquotareservation")
            cursor.execute("DELETE FROM sitecontent_durablejob")
            cursor.execute("DELETE FROM sitecontent_durableschedule")
            cursor.execute("DELETE FROM sitecontent_breakglassgrant")
            cursor.execute("DELETE FROM sitecontent_tenantnotification")
            cursor.execute("DELETE FROM sitecontent_tenantdomainclaim")
            cursor.execute("DELETE FROM sitecontent_tenantquota")
            cursor.execute("DELETE FROM sitecontent_operationsservice")
            cursor.execute("DELETE FROM sitecontent_contenttypedefinition")
            cursor.execute(
                """INSERT INTO sitecontent_contenttypedefinition
                   (id,site_id,type_key,version,name,description,status,preset_id,
                    preset_version,compatibility,migration_digest,lock_version,
                    created_by,updated_by,created_at,updated_at)
                   VALUES (%s,'site-a','article',1,'A','','draft','custom',1,
                           'additive','',1,'','','2026-09-02','2026-09-02'),
                          (%s,'site-b','article',1,'B','','draft','custom',1,
                           'additive','',1,'','','2026-09-02','2026-09-02')""",
                (str(UUID(int=1)), str(UUID(int=2))),
            )
            cursor.execute(
                """INSERT INTO sitecontent_operationsservice
                   (id,site_id,service_key,environment,enabled,release_id,created_at,updated_at)
                   VALUES (%s,'site-a','api.health','staging',true,'release-a',NOW(),NOW()),
                          (%s,'site-b','api.health','staging',true,'release-b',NOW(),NOW())""",
                (str(UUID(int=20)), str(UUID(int=21))),
            )
            cursor.execute(
                """INSERT INTO sitecontent_tenantquota
                   (id,site_id,quota_key,"limit",used,reserved,revision,created_at,updated_at)
                   VALUES (%s,'site-a','jobs',10,0,0,1,NOW(),NOW()),
                          (%s,'site-b','jobs',20,0,0,1,NOW(),NOW())""",
                (str(UUID(int=30)), str(UUID(int=31))),
            )
            cursor.execute(
                """INSERT INTO api_email_outbox
                   (id,to_email,subject,body_text,body_html,status,provider,
                    provider_message_id,error,created_at,sent_at,delivery_key)
                   VALUES (%s,'owner@example.invalid','Synthetic','Body','','queued',
                           'local_outbox','','',NOW(),NULL,%s)""",
                (str(UUID(int=40)), str(UUID(int=40))),
            )
            cursor.execute(
                """INSERT INTO api_auth_users
                   (id,email,password_hash,is_active,is_email_verified,display_name,
                    avatar_url,bio,created_at,updated_at,failed_login_attempts)
                   VALUES (%s,'rights@example.invalid','hash',true,true,'Rights','','',NOW(),NOW(),0)""",
                (str(UUID(int=50)),),
            )
            cursor.execute(
                "INSERT INTO api_identity_organizations (id,tenant_id,name) VALUES (%s,'site-a','A')",
                (str(UUID(int=51)),),
            )
            cursor.execute(
                "INSERT INTO api_auth_users "
                "(id,email,password_hash,is_active,is_email_verified,display_name,avatar_url,bio,created_at,updated_at,failed_login_attempts) "
                "VALUES (%s,'other@example.invalid','hash',true,true,'Other','','',NOW(),NOW(),0)",
                (str(UUID(int=53)),),
            )
            cursor.execute(
                "INSERT INTO api_auth_users "
                "(id,email,password_hash,is_active,is_email_verified,display_name,avatar_url,bio,created_at,updated_at,failed_login_attempts) "
                "VALUES (%s,'same-tenant-other@example.invalid','hash',true,true,'Other A','','',NOW(),NOW(),0)",
                (str(UUID(int=57)),),
            )
            cursor.execute(
                "INSERT INTO api_identity_organizations (id,tenant_id,name) VALUES (%s,'site-b','B')",
                (str(UUID(int=54)),),
            )
            cursor.execute(
                """INSERT INTO api_identity_memberships
                   (organization_id,user_id,role,status,created_at,updated_at)
                   VALUES (%s,%s,'owner','active',NOW(),NOW())""",
                (str(UUID(int=51)), str(UUID(int=50))),
            )
            cursor.execute(
                "INSERT INTO api_identity_memberships "
                "(organization_id,user_id,role,status,created_at,updated_at) "
                "VALUES (%s,%s,'owner','active',NOW(),NOW())",
                (str(UUID(int=54)), str(UUID(int=53))),
            )
            cursor.execute(
                "INSERT INTO api_identity_memberships "
                "(organization_id,user_id,role,status,created_at,updated_at) "
                "VALUES (%s,%s,'viewer','active',NOW(),NOW())",
                (str(UUID(int=54)), str(UUID(int=50))),
            )
            cursor.execute(
                "INSERT INTO api_identity_memberships "
                "(organization_id,user_id,role,status,created_at,updated_at) "
                "VALUES (%s,%s,'viewer','active',NOW(),NOW())",
                (str(UUID(int=51)), str(UUID(int=57))),
            )
            cursor.execute(
                """INSERT INTO api_data_rights_operations
                   (id,tenant_id,user_id,kind,status,request_ciphertext,retention_until)
                   VALUES (%s,'site-a',%s,'export','queued','ciphertext',NOW()+INTERVAL '1 day'),
                          (%s,'site-a',%s,'deletion','queued','ciphertext',NOW()+INTERVAL '1 day')""",
                (str(UUID(int=52)), str(UUID(int=50)), str(UUID(int=58)), str(UUID(int=50))),
            )
            cursor.execute(
                """INSERT INTO sitecontent_tenantlifecyclestate
                   (id,site_id,state,owner_ref,configuration,revision,last_operation_id,
                    last_receipt_digest,created_at,updated_at)
                   VALUES (%s,'site-a','active','owner','{}',1,%s,%s,NOW(),NOW()),
                          (%s,'site-b','active','owner','{}',1,%s,%s,NOW(),NOW())""",
                (
                    str(UUID(int=42)),
                    str(UUID(int=43)),
                    "a" * 64,
                    str(UUID(int=44)),
                    str(UUID(int=45)),
                    "b" * 64,
                ),
            )
            cursor.execute(
                "SELECT rolbypassrls, rolsuper FROM pg_roles WHERE rolname=%s", (runtime_user,)
            )
            assert cursor.fetchone() == (False, False)
            cursor.execute(
                "SELECT rolbypassrls,rolsuper,rolcreatedb,rolcreaterole "
                "FROM pg_roles WHERE rolname=%s", (api_runtime_user,)
            )
            assert cursor.fetchone() == (False, False, False, False)
            cursor.execute(
                "SELECT rolbypassrls, rolsuper FROM pg_roles WHERE rolname=%s",
                (data_rights_user,),
            )
            assert cursor.fetchone() == (False, False)
            cursor.execute(
                "SELECT has_table_privilege(%s,'api_auth_users','SELECT'),"
                "has_table_privilege(%s,'api_auth_users','UPDATE'),"
                "has_table_privilege(%s,'api_auth_users','INSERT'),"
                "has_table_privilege(%s,'api_auth_users','DELETE'),"
                "NOT EXISTS (SELECT 1 FROM information_schema.table_privileges "
                "WHERE grantee='PUBLIC' AND table_name='api_auth_users')",
                (data_rights_user,) * 4,
            )
            assert cursor.fetchone() == (True, False, False, False, True)
            cursor.execute(
                "SELECT rolbypassrls, rolsuper FROM pg_roles WHERE rolname=%s", (worker_user,)
            )
            assert cursor.fetchone() == (False, False)
            cursor.execute(
                "SELECT rolbypassrls, rolsuper FROM pg_roles WHERE rolname=%s",
                (content_worker_user,),
            )
            assert cursor.fetchone() == (False, False)
            cursor.execute(
                "SELECT rolbypassrls, rolsuper FROM pg_roles WHERE rolname=%s",
                (email_worker_user,),
            )
            assert cursor.fetchone() == (False, False)
            cursor.execute(
                """SELECT COUNT(*) FROM pg_policies
                   WHERE schemaname='public' AND tablename='sitecontent_contenttypedefinition'"""
            )
            assert cursor.fetchone()[0] == 4
            cursor.execute(
                """SELECT COUNT(*) FROM pg_class
                   WHERE relname LIKE 'sitecontent_operations%'
                     AND relrowsecurity AND relforcerowsecurity"""
            )
            assert cursor.fetchone()[0] == 7
            cursor.execute(
                """SELECT COUNT(*) FROM pg_policies
                   WHERE tablename LIKE 'sitecontent_operations%'"""
            )
            operations_policy_count = cursor.fetchone()[0]
            assert operations_policy_count == 30, operations_policy_count
            cursor.execute(
                """SELECT COUNT(*) FROM pg_policies
                   WHERE tablename IN (
                       'sitecontent_operationsincident',
                       'sitecontent_operationsincidentevent'
                   )
                     AND policyname='data_rights_claim_fence'
                     AND permissive='RESTRICTIVE'"""
            )
            assert cursor.fetchone()[0] == 2
            cursor.execute(
                """SELECT COUNT(*) FROM pg_class
                   WHERE relname LIKE 'sitecontent_tenantquota%'
                     AND relrowsecurity AND relforcerowsecurity"""
            )
            assert cursor.fetchone()[0] == 2
            cursor.execute(
                """SELECT COUNT(*) FROM pg_policies
                   WHERE tablename LIKE 'sitecontent_tenantquota%'"""
            )
            assert cursor.fetchone()[0] == 8
            cursor.execute(
                """SELECT policyname,cmd,permissive,qual,with_check
                   FROM pg_policies
                   WHERE tablename='api_data_rights_operations'
                   ORDER BY policyname"""
            )
            operation_policies = cursor.fetchall()
            assert len(operation_policies) == 2, operation_policies
            cursor.execute(
                """SELECT COUNT(*) FROM pg_class WHERE relname IN (
                       'sitecontent_tenantdomainclaim','sitecontent_durablejob',
                       'sitecontent_durableschedule','sitecontent_breakglassgrant',
                       'sitecontent_tenantnotification') AND relrowsecurity AND relforcerowsecurity"""
            )
            assert cursor.fetchone()[0] == 5
            cursor.execute(
                """SELECT indexname FROM pg_indexes
                   WHERE tablename='sitecontent_contenttypedefinition'"""
            )
            indexes = {row[0] for row in cursor.fetchall()}
            assert "sitecontent_type_state_idx" in indexes

            record_mutation_id = str(UUID(int=10))
            record_transition_id = str(UUID(int=11))
            scheduled_record_id = str(UUID(int=12))
            saved_view_id = str(UUID(int=13))
            privacy_saved_view_id = str(UUID(int=15))
            other_saved_view_id = str(UUID(int=16))
            import_job_id = str(UUID(int=14))
            cursor.execute(
                """INSERT INTO sitecontent_contentrecord
                   (id,site_id,content_type,slug,title,excerpt,body,metadata,state,
                    publish_at,schedule_timezone,published_at,sitemap_include,search_visible,
                    version,definition_id,schema_version,values,deleted_at,created_at,updated_at)
                   VALUES
                   (%s,'site-a','article','mutation','Mutation','','','{}','draft',
                    NULL,'',NULL,true,true,1,%s,1,'{}',NULL,NOW(),NOW()),
                   (%s,'site-a','article','transition','Transition','','','{}','draft',
                    NULL,'',NULL,true,true,1,%s,1,'{}',NULL,NOW(),NOW()),
                   (%s,'site-a','article','scheduled','Scheduled','','','{}','scheduled',
                    NOW() - INTERVAL '1 minute','UTC',NULL,true,true,1,%s,1,'{}',NULL,NOW(),NOW())""",
                (
                    record_mutation_id,
                    str(UUID(int=1)),
                    record_transition_id,
                    str(UUID(int=1)),
                    scheduled_record_id,
                    str(UUID(int=1)),
                ),
            )
            cursor.execute(
                """INSERT INTO sitecontent_savedview
                   (id,site_id,definition_id,owner_ref,title,query,visibility,shared_roles,
                    schema_version,lock_version,created_at,updated_at)
                   VALUES (%s,'site-a',%s,'owner','View','{}','private','[]',1,1,NOW(),NOW()),
                          (%s,'site-a',%s,%s,'Privacy view','{}','private','[]',1,1,NOW(),NOW()),
                          (%s,'site-a',%s,%s,'Other view','{}','private','[]',1,1,NOW(),NOW())""",
                (
                    saved_view_id, str(UUID(int=1)),
                    privacy_saved_view_id, str(UUID(int=1)), str(UUID(int=50)),
                    other_saved_view_id, str(UUID(int=1)), str(UUID(int=57)),
                ),
            )
            cursor.execute(
                """INSERT INTO sitecontent_importjob
                   (id,site_id,definition_id,requester_ref,request_digest,idempotency_key,
                    schema_version,error_code,counters,completed_at,source_sha256,source_format,
                    source_object_key,status,mapping,duplicate_policy,atomic_policy,
                    created_at,updated_at)
                   VALUES (%s,'site-a',%s,'owner',%s,'race-import',1,'','{}',NULL,%s,'json',
                           'private/source','validated','{}','review','all_or_nothing',NOW(),NOW())""",
                (import_job_id, str(UUID(int=1)), "a" * 64, "b" * 64),
            )
            cursor.execute(
                """INSERT INTO sitecontent_mediaasset
                   (id,site_id,storage_key,original_name,media_type,byte_size,sha256,status,
                    owner_ref,attribution,retention_until,metadata,visibility,lock_version,
                    current_object_version,authorization_epoch,archived_at,deleted_at,created_at,updated_at)
                   VALUES (%s,'site-a','media/site-a/original','safe.png','image/png',10,%s,
                           'ready','owner','',NULL,'{}','private',1,1,1,NULL,NULL,NOW(),NOW())""",
                (str(UUID(int=70)), "d" * 64),
            )
            cursor.execute(
                """INSERT INTO sitecontent_mediavariant
                   (id,asset_id,name,storage_key,media_type,byte_size,sha256,width,height,
                    recipe_id,recipe_version,source_sha256,processor_ref,inline_safe,
                    duration_seconds,page_number,created_at)
                   VALUES (%s,%s,'thumbnail','media/site-a/thumbnail','image/png',8,%s,32,32,
                           'safe-v1',1,%s,'processor-v1',true,NULL,NULL,NOW())""",
                (str(UUID(int=71)), str(UUID(int=70)), "e" * 64, "d" * 64),
            )
            cursor.execute(
                """INSERT INTO sitecontent_mediaobjectversion
                   (id,site_id,asset_id,version,storage_key,sha256,byte_size,detected_type,
                    inspection_state,scanner_ref,scanner_definitions_at,source_upload_ref,
                    replaces_id,created_at,updated_at)
                   VALUES (%s,'site-a',%s,1,'media/site-a/object-v1',%s,10,'image/png',
                           'accepted','scanner-v1',NOW(),NULL,NULL,NOW(),NOW())""",
                (str(UUID(int=72)), str(UUID(int=70)), "d" * 64),
            )

        assert count(runtime, None) == 0
        runtime.rollback()
        assert auth_user_count(api_runtime) == 3
        api_runtime.rollback()
        assert_permission_denied(
            lambda: count(api_runtime, "site-a"),
            api_runtime,
            "api_runtime_workspace_table_access_was_not_blocked",
        )
        with api_runtime.cursor() as cursor:
            try:
                cursor.execute("CREATE TABLE api_runtime_forbidden(id integer)")
            except errors.InsufficientPrivilege:
                api_runtime.rollback()
            else:
                raise AssertionError("api_runtime_schema_create_was_not_blocked")
        with api_runtime.cursor() as cursor:
            cursor.execute("SET app.tenant_id = 'site-a'")
            cursor.execute(
                "SELECT id FROM api_identity_organizations WHERE tenant_id='site-b'"
            )
            assert cursor.fetchone() is None, "api_runtime_cross_tenant_org_read_was_not_blocked"
        api_runtime.rollback()
        with api_runtime.cursor() as cursor:
            cursor.execute("SET app.tenant_id = 'site-a'")
            try:
                cursor.execute(
                    "INSERT INTO api_identity_organizations(id,tenant_id,name) "
                    "VALUES (%s,'site-b','forbidden')",
                    (str(UUID(int=80)),),
                )
            except errors.InsufficientPrivilege:
                api_runtime.rollback()
            else:
                raise AssertionError("api_runtime_cross_tenant_org_insert_was_not_blocked")
        with api_runtime.cursor() as cursor:
            cursor.execute("SET app.tenant_id = 'site-a'")
            cursor.execute(
                "SELECT id FROM api_data_rights_operations WHERE tenant_id='site-b'"
            )
            assert cursor.fetchone() is None, "api_runtime_cross_tenant_queue_read_was_not_blocked"
        api_runtime.rollback()
        with api_runtime.cursor() as cursor:
            try:
                cursor.execute(
                    "INSERT INTO api_schema_migrations(version,applied_at) VALUES (999,NOW())"
                )
            except errors.InsufficientPrivilege:
                api_runtime.rollback()
            else:
                raise AssertionError("api_runtime_migration_ledger_dml_was_not_blocked")
        with api_runtime.cursor() as cursor:
            try:
                cursor.execute(
                    "UPDATE api_data_rights_operations SET status='failed' WHERE id=%s",
                    (str(UUID(int=52)),),
                )
            except errors.InsufficientPrivilege:
                api_runtime.rollback()
            else:
                raise AssertionError("api_runtime_queue_update_was_not_blocked")
        assert operations_count(runtime, None) == 0
        runtime.rollback()
        # Runtime workers have only operations/job authority. Content workers
        # use a separately credentialed content/media identity, never this role.
        assert_permission_denied(
            lambda: count(worker, None), worker, "runtime_worker_content_read_was_not_blocked"
        )
        assert_permission_denied(
            lambda: outbox_count(worker), worker, "runtime_worker_outbox_read_was_not_blocked"
        )
        assert count(content_worker, None) == 2
        content_worker.rollback()
        assert_permission_denied(
            lambda: data_rights_count(content_worker),
            content_worker,
            "content_worker_data_rights_read_was_not_blocked",
        )
        assert_permission_denied(
            lambda: auth_user_count(content_worker),
            content_worker,
            "content_worker_identity_read_was_not_blocked",
        )
        assert_permission_denied(
            lambda: data_rights_count(data_rights_worker),
            data_rights_worker,
            "data_rights_operation_enumeration_was_not_blocked",
        )
        with worker.cursor() as cursor:
            cursor.execute("SELECT * FROM base2_list_due_data_rights_operations(25)")
            dispatches = {str(row[0]): str(row[1]) for row in cursor.fetchall()}
        worker.commit()
        with data_rights_worker.cursor() as cursor:
            cursor.execute("SELECT set_config('app.tenant_id', 'site-a', true)")
            cursor.execute("SELECT current_user,current_setting('app.tenant_id', true)")
            assert cursor.fetchone() == (data_rights_user, "site-a")
            # Tenant context alone is never authority. An exact operation and
            # claim token must be bound before any subject or tenant row appears.
            cursor.execute("SELECT tenant_id FROM api_identity_organizations")
            assert cursor.fetchall() == []
            cursor.execute("SELECT user_id FROM api_identity_memberships")
            assert cursor.fetchall() == []
            cursor.execute("SELECT email FROM api_auth_users WHERE id=%s", (str(UUID(int=50)),))
            assert cursor.fetchone() is None
            operation_id = str(UUID(int=52))
            stale_claim = str(UUID(int=55))
            current_claim = str(UUID(int=56))
            assert operation_id in dispatches
            cursor.execute(
                "SELECT * FROM base2_claim_data_rights_operation(%s,%s,%s)",
                (operation_id, dispatches[operation_id], stale_claim),
            )
            assert cursor.fetchone()[-1] == stale_claim
            cursor.execute(
                "SELECT set_config('app.data_rights_operation_id', %s, true),"
                "set_config('app.data_rights_claim_token', %s, true)",
                (operation_id, stale_claim),
            )
            cursor.execute("SELECT tenant_id FROM api_identity_organizations")
            assert cursor.fetchall() == [("site-a",)]
            cursor.execute("SELECT user_id FROM api_identity_memberships")
            assert cursor.fetchall() == [(str(UUID(int=50)),)]
            cursor.execute("SELECT email FROM api_auth_users WHERE id=%s", (str(UUID(int=50)),))
            assert cursor.fetchone() == ("rights@example.invalid",)
            cursor.execute("SELECT id,title,query FROM sitecontent_savedview ORDER BY id")
            assert cursor.fetchall() == [(privacy_saved_view_id, "Privacy view", {})]
            cursor.execute("SELECT email FROM api_auth_users WHERE id=%s", (str(UUID(int=53)),))
            assert cursor.fetchone() is None, "data_rights_cross_tenant_user_read_was_not_blocked"
            cursor.execute("SELECT email FROM api_auth_users WHERE id=%s", (str(UUID(int=57)),))
            assert cursor.fetchone() is None, "data_rights_same_tenant_other_subject_read_was_not_blocked"
            cursor.execute("SAVEPOINT direct_write_denial")
            try:
                cursor.execute(
                    "UPDATE api_auth_users SET display_name='blocked' WHERE id=%s",
                    (str(UUID(int=50)),),
                )
            except errors.InsufficientPrivilege:
                cursor.execute("ROLLBACK TO SAVEPOINT direct_write_denial")
            else:
                raise AssertionError("data_rights_direct_subject_update_was_not_blocked")
            cursor.execute("RELEASE SAVEPOINT direct_write_denial")
            cursor.execute("SAVEPOINT direct_delete_denial")
            try:
                cursor.execute(
                    "DELETE FROM api_identity_memberships WHERE organization_id=%s AND user_id=%s",
                    (str(UUID(int=51)), str(UUID(int=50))),
                )
            except errors.InsufficientPrivilege:
                cursor.execute("ROLLBACK TO SAVEPOINT direct_delete_denial")
            else:
                raise AssertionError("data_rights_direct_subject_delete_was_not_blocked")
            cursor.execute("RELEASE SAVEPOINT direct_delete_denial")
            cursor.execute("SELECT set_config('app.tenant_id', 'site-b', true)")
            cursor.execute("SELECT tenant_id FROM api_identity_organizations")
            assert cursor.fetchall() == [], "claim_tenant_switch_was_not_blocked"
            cursor.execute("SELECT set_config('app.tenant_id', 'site-a', true)")
            data_rights_worker.commit()
            with owner.cursor() as owner_cursor:
                owner_cursor.execute(
                    "UPDATE api_data_rights_operations SET claim_expires_at=NOW()-INTERVAL '1 second' "
                    "WHERE id=%s AND status='running' AND claim_token=%s",
                    (operation_id, stale_claim),
                )
            owner.commit()
            cursor.execute(
                "SELECT set_config('app.tenant_id', 'site-a', true),"
                "set_config('app.data_rights_operation_id', %s, true),"
                "set_config('app.data_rights_claim_token', %s, true)",
                (operation_id, stale_claim),
            )
            cursor.execute("SELECT email FROM api_auth_users WHERE id=%s", (str(UUID(int=50)),))
            assert cursor.fetchone() is None, "expired_claim_subject_read_was_not_blocked"
            cursor.execute(
                "SELECT base2_finalize_data_rights_operation(%s,%s,'failed','','','synthetic',"
                "'','00000000-0000-0000-0000-000000000000','')",
                (operation_id, stale_claim),
            )
            assert cursor.fetchone() == (False,), "expired_claim_finalize_was_not_blocked"
            with worker.cursor() as dispatch_cursor:
                dispatch_cursor.execute("SELECT * FROM base2_list_due_data_rights_operations(25)")
                refreshed_dispatches = {
                    str(row[0]): str(row[1]) for row in dispatch_cursor.fetchall()
                }
            worker.commit()
            cursor.execute(
                "SELECT * FROM base2_claim_data_rights_operation(%s,%s,%s)",
                (operation_id, refreshed_dispatches[operation_id], current_claim),
            )
            assert cursor.fetchone()[-1] == current_claim
            cursor.execute(
                "SELECT set_config('app.data_rights_claim_token', %s, true)", (current_claim,)
            )
            cursor.execute("SELECT email FROM api_auth_users WHERE id=%s", (str(UUID(int=50)),))
            assert cursor.fetchone() == (
                "rights@example.invalid",
            ), "reclaimed_subject_access_was_not_restored"
            cursor.execute(
                "SELECT base2_finalize_data_rights_operation(%s,%s,'failed','','','synthetic',"
                "'','00000000-0000-0000-0000-000000000000','')",
                (operation_id, current_claim),
            )
            assert cursor.fetchone() == (True,)
        data_rights_worker.rollback()
        deletion_id = str(UUID(int=58))
        deletion_claim = str(UUID(int=59))
        with data_rights_worker.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM base2_claim_data_rights_operation(%s,%s,%s)",
                (deletion_id, dispatches[deletion_id], deletion_claim),
            )
            assert cursor.fetchone()[-1] == deletion_claim
            cursor.execute(
                "SELECT base2_apply_data_rights_subject_action(%s,%s,'deletion','{}'::jsonb)",
                (deletion_id, deletion_claim),
            )
            closure = cursor.fetchone()[0]
            assert closure["tenant_membership_deleted"] is True
            assert closure["global_account_deleted"] is False
        data_rights_worker.commit()
        with owner.cursor() as cursor:
            cursor.execute("SELECT is_active FROM api_auth_users WHERE id=%s", (str(UUID(int=50)),))
            assert cursor.fetchone() == (True,)
            cursor.execute(
                "SELECT organization_id FROM api_identity_memberships WHERE user_id=%s ORDER BY organization_id",
                (str(UUID(int=50)),),
            )
            assert cursor.fetchall() == [(str(UUID(int=54)),)]
        owner.rollback()
        global_deletion_id = str(UUID(int=60))
        global_deletion_claim = str(UUID(int=61))
        with owner, owner.cursor() as cursor:
            cursor.execute(
                """INSERT INTO sitecontent_savedview
                   (id,site_id,definition_id,owner_ref,title,query,visibility,shared_roles,
                    schema_version,lock_version,created_at,updated_at)
                   VALUES (%s,'site-a',%s,%s,'Orphaned historical view','{}','private','[]',
                           1,1,NOW(),NOW())""",
                (str(UUID(int=62)), str(UUID(int=1)), str(UUID(int=50))),
            )
            cursor.execute(
                "INSERT INTO api_data_rights_operations "
                "(id,tenant_id,user_id,kind,status,request_ciphertext,retention_until) "
                "VALUES (%s,'site-a',%s,'global_deletion','queued','ciphertext',"
                "NOW()+INTERVAL '1 day')",
                (global_deletion_id, str(UUID(int=50))),
            )
        with worker.cursor() as cursor:
            cursor.execute("SELECT * FROM base2_list_due_data_rights_operations(25)")
            global_dispatches = {str(row[0]): str(row[1]) for row in cursor.fetchall()}
        worker.commit()
        with data_rights_worker.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM base2_claim_data_rights_operation(%s,%s,%s)",
                (
                    global_deletion_id,
                    global_dispatches[global_deletion_id],
                    global_deletion_claim,
                ),
            )
            assert cursor.fetchone()[-1] == global_deletion_claim
            cursor.execute(
                "SELECT base2_apply_data_rights_subject_action(%s,%s,'global_deletion','{}'::jsonb)",
                (global_deletion_id, global_deletion_claim),
            )
            closure = cursor.fetchone()[0]
            assert closure["global_account_deleted"] is True
        data_rights_worker.commit()
        with owner.cursor() as cursor:
            cursor.execute(
                "SELECT email,is_active,password_hash FROM api_auth_users WHERE id=%s",
                (str(UUID(int=50)),),
            )
            deleted_user = cursor.fetchone()
            assert deleted_user[0].endswith('@deleted.invalid')
            assert deleted_user[1:] == (False, '')
            cursor.execute(
                "SELECT 1 FROM api_identity_memberships WHERE user_id=%s", (str(UUID(int=50)),)
            )
            assert cursor.fetchone() is None
            cursor.execute(
                "SELECT 1 FROM sitecontent_savedview WHERE id=%s", (str(UUID(int=62)),)
            )
            assert cursor.fetchone() is None, "global_closure_missed_orphaned_subject_tenant"
            cursor.execute(
                "DELETE FROM api_data_rights_operations WHERE id=%s", (global_deletion_id,)
            )
        owner.commit()
        with owner.cursor() as cursor:
            cursor.execute(
                "SELECT table_name,column_name FROM sitecontent_subjectdataregistry "
                "ORDER BY table_name,column_name"
            )
            registered = set(cursor.fetchall())
            cursor.execute(
                "SELECT table_name,column_name FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name LIKE 'sitecontent\\_%' ESCAPE '\\' "
                "AND column_name IN ('owner_ref','requester_ref','actor_ref','audience_ref',"
                "'subject_ref','reporter_ref','reviewer_ref','appellant_ref','approver_ref',"
                "'target_owner_ref')"
            )
            discovered = set(cursor.fetchall())
            assert registered == discovered, (
                f"subject_inventory_drift:missing={sorted(discovered-registered)}:"
                f"stale={sorted(registered-discovered)}"
            )
        owner.rollback()
        with content_worker.cursor() as cursor:
            cursor.execute("SELECT set_config('app.tenant_id', 'site-a', true)")
            cursor.execute(
                "UPDATE sitecontent_contenttypedefinition SET name='blocked' WHERE site_id='site-b'"
            )
            assert cursor.rowcount == 0, "content_worker_cross_tenant_update_was_not_blocked"
            cursor.execute("DELETE FROM sitecontent_contenttypedefinition WHERE site_id='site-b'")
            assert cursor.rowcount == 0, "content_worker_cross_tenant_delete_was_not_blocked"
            try:
                cursor.execute(
                    """INSERT INTO sitecontent_contenttypedefinition
                       (id,site_id,type_key,version,name,description,status,preset_id,
                        preset_version,compatibility,migration_digest,lock_version,
                        created_by,updated_by,created_at,updated_at)
                       VALUES (%s,'site-b','blocked-content',1,'Blocked','','draft','custom',1,
                               'additive','',1,'','','2026-09-08','2026-09-08')""",
                    (str(UUID(int=301)),),
                )
            except errors.InsufficientPrivilege:
                content_worker.rollback()
            else:
                raise AssertionError("content_worker_cross_tenant_insert_was_not_blocked")
        assert_permission_denied(
            lambda: operations_count(content_worker, None),
            content_worker,
            "content_worker_operations_read_was_not_blocked",
        )
        assert_permission_denied(
            lambda: quota_count(content_worker, "site-a"),
            content_worker,
            "content_worker_quota_read_was_not_blocked",
        )
        assert_permission_denied(
            lambda: outbox_count(content_worker),
            content_worker,
            "content_worker_outbox_read_was_not_blocked",
        )
        assert operations_count(worker, None) == 0
        worker.rollback()
        assert operations_count(worker, "site-a") == 1
        worker.rollback()
        assert quota_count(worker, None) == 0
        worker.rollback()
        assert quota_count(worker, "site-a") == 1
        worker.rollback()
        assert count(runtime, "site-a") == 1
        runtime.rollback()
        assert operations_count(runtime, "site-a") == 1
        runtime.rollback()
        assert quota_count(runtime, "site-a") == 1
        runtime.rollback()
        assert quota_count(runtime, "site-b") == 1
        runtime.rollback()
        with email_worker.cursor() as cursor:
            cursor.execute("SELECT status FROM api_email_outbox WHERE id=%s", (str(UUID(int=40)),))
            assert cursor.fetchone() == ("queued",)
            cursor.execute(
                "UPDATE api_email_outbox SET status='sending' WHERE id=%s", (str(UUID(int=40)),)
            )
            assert cursor.rowcount == 1
        email_worker.commit()
        migrated_email = create_outbox_email(
            to_email="migration-proof@example.invalid",
            subject="Migration proof",
            body_text="Body",
        )
        assert migrated_email.delivery_key == str(migrated_email.id)
        assert_permission_denied(
            lambda: count(email_worker, None),
            email_worker,
            "email_worker_content_read_was_not_blocked",
        )
        assert_permission_denied(
            lambda: operations_count(email_worker, None),
            email_worker,
            "email_worker_operations_read_was_not_blocked",
        )
        assert_permission_denied(
            lambda: insert_outbox(email_worker),
            email_worker,
            "email_worker_outbox_insert_was_not_blocked",
        )
        created = enqueue_job(
            tenant_id="site-a",
            owner_ref="owner",
            job_type="search.reindex",
            payload_digest="d" * 64,
            payload_schema=1,
            idempotency_key="search.reindex-001",
            available_at=datetime.now(UTC),
        )
        replayed = enqueue_job(
            tenant_id="site-a",
            owner_ref="owner",
            job_type="search.reindex",
            payload_digest="d" * 64,
            payload_schema=1,
            idempotency_key="search.reindex-001",
            available_at=datetime.now(UTC),
        )
        assert replayed == {**created, "replayed": True}
        claimed = claim_jobs(tenant_id="site-a", worker="worker-one", now=datetime.now(UTC))
        assert len(claimed) == 1 and claimed[0]["jobId"] == created["jobId"]
        assert claim_jobs(tenant_id="site-b", worker="worker-one", now=datetime.now(UTC)) == []
        assert (
            settle_job(
                tenant_id="site-a",
                job_id=UUID(created["jobId"]),
                worker="worker-one",
                lease_token=UUID(claimed[0]["leaseToken"]),
                generation=claimed[0]["generation"],
                outcome="succeeded",
                now=datetime.now(UTC),
                result_digest="e" * 64,
            )
            == "succeeded"
        )
        with runtime.cursor() as cursor:
            cursor.execute("SET LOCAL enable_seqscan=off")
            cursor.execute(
                """EXPLAIN SELECT id FROM sitecontent_contenttypedefinition
                   WHERE site_id='site-a' AND type_key='article' AND status='draft'
                   ORDER BY version,id LIMIT 25"""
            )
            plan = "\n".join(row[0] for row in cursor.fetchall())
            assert "sitecontent_type_version_uq" in plan and "Index Scan" in plan, plan
        runtime.rollback()
        assert count(runtime, "site-b") == 1
        runtime.rollback()
        with runtime.cursor() as cursor:
            cursor.execute("SELECT set_config('app.tenant_id', 'site-a', true)")
            try:
                cursor.execute(
                    """INSERT INTO sitecontent_contenttypedefinition
                       (id,site_id,type_key,version,name,description,status,preset_id,
                        preset_version,compatibility,migration_digest,lock_version,
                        created_by,updated_by,created_at,updated_at)
                       VALUES (%s,'site-b','blocked',1,'Blocked','','draft','custom',1,
                               'additive','',1,'','','2026-09-02','2026-09-02')""",
                    (str(UUID(int=3)),),
                )
            except errors.InsufficientPrivilege:
                runtime.rollback()
            else:
                raise AssertionError("cross_tenant_insert_was_not_blocked")
        assert count(runtime, None) == 0
        runtime.rollback()
        with runtime.cursor() as cursor:
            cursor.execute("SELECT set_config('app.tenant_id', 'site-a', true)")
            try:
                cursor.execute(
                    """INSERT INTO sitecontent_operationsservice
                       (id,site_id,service_key,environment,enabled,release_id,
                        created_at,updated_at)
                       VALUES (%s,'site-b','blocked.health','staging',true,'',NOW(),NOW())""",
                    (str(UUID(int=22)),),
                )
            except errors.InsufficientPrivilege:
                runtime.rollback()
            else:
                raise AssertionError("operations_cross_tenant_insert_was_not_blocked")
        assert operations_count(runtime, None) == 0
        runtime.rollback()

        with runtime.cursor() as cursor:
            cursor.execute("SELECT set_config('app.tenant_id', 'site-a', true)")
            try:
                cursor.execute(
                    """INSERT INTO sitecontent_tenantquotareservation
                       (id,site_id,reservation_id,amount,state,quota_id,created_at,updated_at)
                       VALUES (%s,'site-b','job.blocked',1,'reserved',%s,NOW(),NOW())""",
                    (str(UUID(int=32)), str(UUID(int=31))),
                )
            except errors.InsufficientPrivilege:
                runtime.rollback()
            else:
                raise AssertionError("quota_cross_tenant_insert_was_not_blocked")

        quota_reservation_race()
        with owner, owner.cursor() as cursor:
            cursor.execute(
                """SELECT used,reserved,revision FROM sitecontent_tenantquota
                   WHERE site_id='site-a' AND quota_key='jobs'"""
            )
            assert cursor.fetchone() == (0, 6, 2)
            cursor.execute(
                """SELECT COUNT(*) FROM sitecontent_tenantquotareservation
                   WHERE site_id='site-a' AND state='reserved'"""
            )
            assert cursor.fetchone()[0] == 1

        observed = datetime.now(UTC)
        failed = record_probe_batch(
            tenant_id="site-a",
            environment="staging",
            now=observed,
            results=[
                {
                    "probeId": "api.health",
                    "state": "unavailable",
                    "code": "api.unavailable",
                    "latencyMs": 5,
                    "observedAt": observed.isoformat(),
                    "expiresAt": (observed + timedelta(minutes=3)).isoformat(),
                }
            ],
        )
        assert failed == {"samples": 1, "opened": 1, "resolved": 0, "alerts": 1}
        due = due_alert_deliveries(tenant_id="site-a", now=observed, limit=25)
        assert len(due) == 1 and due[0]["summaryCode"] == "api.unavailable"
        recovered_at = observed + timedelta(seconds=10)
        recovered = record_probe_batch(
            tenant_id="site-a",
            environment="staging",
            now=recovered_at,
            results=[
                {
                    "probeId": "api.health",
                    "state": "healthy",
                    "code": "api.ready",
                    "latencyMs": 3,
                    "observedAt": recovered_at.isoformat(),
                    "expiresAt": (recovered_at + timedelta(minutes=3)).isoformat(),
                }
            ],
        )
        assert recovered == {"samples": 1, "opened": 0, "resolved": 1, "alerts": 0}
        with owner, owner.cursor() as cursor:
            cursor.execute(
                """SELECT state,occurrence_count,resolved_at IS NOT NULL
                   FROM sitecontent_operationsincident WHERE site_id='site-a'"""
            )
            assert cursor.fetchone() == ("resolved", 1, True)
            cursor.execute(
                "SELECT COUNT(*) FROM sitecontent_operationsalertdelivery WHERE site_id='site-a'"
            )
            assert cursor.fetchone()[0] == 1

        with owner.cursor() as cursor:
            try:
                cursor.execute(
                    """INSERT INTO sitecontent_operationshealthsample
                       (id,site_id,service_id,state,code,latency_ms,dimensions,
                        observed_at,expires_at,created_at,updated_at)
                       VALUES (%s,'site-b',%s,'healthy','api.ready',1,'{}',
                               NOW(),NOW()+INTERVAL '1 minute',NOW(),NOW())""",
                    (str(UUID(int=23)), str(UUID(int=20))),
                )
            except errors.ForeignKeyViolation:
                owner.rollback()
            else:
                raise AssertionError("operations_cross_tenant_link_was_not_blocked")

        optimistic_race(
            runtime_user=runtime_user,
            runtime_password=runtime_password,
            statement="""UPDATE sitecontent_contenttypedefinition
                         SET status='published', lock_version=lock_version+1, published_at=NOW()
                         WHERE id=%s AND site_id='site-a' AND status='draft' AND lock_version=1""",
            parameters=(str(UUID(int=1)),),
        )
        optimistic_race(
            runtime_user=runtime_user,
            runtime_password=runtime_password,
            statement="""UPDATE sitecontent_contentrecord
                         SET title='Mutated', version=version+1, updated_at=NOW()
                         WHERE id=%s AND site_id='site-a' AND version=1""",
            parameters=(record_mutation_id,),
        )
        optimistic_race(
            runtime_user=runtime_user,
            runtime_password=runtime_password,
            statement="""UPDATE sitecontent_contentrecord
                         SET state='in_review', version=version+1, updated_at=NOW()
                         WHERE id=%s AND site_id='site-a' AND state='draft' AND version=1""",
            parameters=(record_transition_id,),
        )
        optimistic_race(
            runtime_user=runtime_user,
            runtime_password=runtime_password,
            statement="""UPDATE sitecontent_savedview
                         SET title='Updated', lock_version=lock_version+1, updated_at=NOW()
                         WHERE id=%s AND site_id='site-a' AND lock_version=1""",
            parameters=(saved_view_id,),
        )
        optimistic_race(
            runtime_user=runtime_user,
            runtime_password=runtime_password,
            statement="""UPDATE sitecontent_importjob
                         SET status='committing', updated_at=NOW()
                         WHERE id=%s AND site_id='site-a' AND status='validated'""",
            parameters=(import_job_id,),
        )
        optimistic_race(
            runtime_user=runtime_user,
            runtime_password=runtime_password,
            statement="""UPDATE sitecontent_contentrecord
                         SET state='published', publish_at=NULL, schedule_timezone='',
                             published_at=NOW(), version=version+1, updated_at=NOW()
                         WHERE id=%s AND site_id='site-a' AND state='scheduled'
                           AND publish_at <= NOW() AND version=1""",
            parameters=(scheduled_record_id,),
        )

        service_file = Path('/tmp/base2-backup-concurrency-pg-service.conf')
        service_file.write_text(
            '[base2_acceptance]\n'
            f'host={os.environ["DB_HOST"]}\nport={os.environ.get("DB_PORT", "5432")}\n'
            f'dbname={os.environ["DB_NAME"]}\nuser={owner_user}\npassword={owner_password}\n',
            encoding='utf-8',
        )
        service_file.chmod(0o600)
        try:
            with _repeatable_read_snapshot(
                {'pgService': 'base2_acceptance', 'pgServiceFile': str(service_file)}
            ) as snapshot:
                snapshot_before = snapshot['references']
                generation_before = snapshot['referenceGeneration']
                updater = connect(owner_user, owner_password)
                try:
                    with updater.cursor() as cursor:
                        cursor.execute(
                            "SELECT source_object_key,source_sha256 FROM sitecontent_importjob WHERE id=%s",
                            (import_job_id,),
                        )
                        original_key, original_digest = cursor.fetchone()
                        cursor.execute(
                            "SELECT storage_key,sha256 FROM sitecontent_mediavariant WHERE id=%s",
                            (str(UUID(int=71)),),
                        )
                        variant_key, variant_digest = cursor.fetchone()
                        cursor.execute(
                            "SELECT storage_key,sha256 FROM sitecontent_mediaobjectversion WHERE id=%s",
                            (str(UUID(int=72)),),
                        )
                        version_key, version_digest = cursor.fetchone()
                        cursor.execute(
                            "UPDATE sitecontent_importjob SET source_object_key=%s,source_sha256=%s "
                            "WHERE id=%s",
                            ('media/site-a/concurrent-object', 'c' * 64, import_job_id),
                        )
                        cursor.execute(
                            "UPDATE sitecontent_mediavariant SET storage_key=%s,sha256=%s WHERE id=%s",
                            ('media/site-a/concurrent-variant', 'f' * 64, str(UUID(int=71))),
                        )
                        cursor.execute(
                            "UPDATE sitecontent_mediaobjectversion SET storage_key=%s,sha256=%s WHERE id=%s",
                            ('media/site-a/concurrent-version', 'f' * 64, str(UUID(int=72))),
                        )
                    updater.commit()
                    with updater.cursor() as cursor:
                        cursor.execute(
                            "UPDATE sitecontent_importjob SET source_object_key=%s,source_sha256=%s "
                            "WHERE id=%s",
                            (original_key, original_digest, import_job_id),
                        )
                        cursor.execute(
                            "UPDATE sitecontent_mediavariant SET storage_key=%s,sha256=%s WHERE id=%s",
                            (variant_key, variant_digest, str(UUID(int=71))),
                        )
                        cursor.execute(
                            "UPDATE sitecontent_mediaobjectversion SET storage_key=%s,sha256=%s WHERE id=%s",
                            (version_key, version_digest, str(UUID(int=72))),
                        )
                    updater.commit()
                finally:
                    updater.close()
                after_state = snapshot['afterState']()
                assert after_state['references'] == snapshot_before, 'backup_aba_fixture_not_restored'
                assert after_state['generation'] > generation_before, (
                    'backup_generation_fence_missed_real_aba_cycle'
                )
        finally:
            service_file.unlink(missing_ok=True)

        with owner, owner.cursor() as cursor:
            cursor.execute(
                """INSERT INTO sitecontent_contenttypedefinition
                   (id,site_id,type_key,version,name,description,status,preset_id,
                    preset_version,compatibility,migration_digest,lock_version,
                    created_by,updated_by,created_at,updated_at)
                   VALUES (%s,'site-a','article',1,'duplicate','','draft','custom',1,
                           'additive','',1,'','','2026-09-02','2026-09-02')""",
                (str(UUID(int=4)),),
            )
    except errors.UniqueViolation:
        owner.rollback()
    else:
        raise AssertionError("same_tenant_composite_uniqueness_not_enforced")
    finally:
        api_runtime.close()
        runtime.close()
        content_worker.close()
        worker.close()
        email_worker.close()
        data_rights_worker.close()
        owner.close()
    print("Workspace PostgreSQL RLS acceptance: PASS")


if __name__ == "__main__":
    main()
