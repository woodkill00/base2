#!/usr/bin/env python3
from __future__ import annotations

import os
import threading
from uuid import UUID

import psycopg2
from psycopg2 import errors


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


def main() -> None:
    owner_user = os.environ["DB_USER"]
    owner_password = os.environ["DB_PASSWORD"]
    runtime_user = os.environ["WORKSPACE_DB_USER"]
    runtime_password = os.environ["WORKSPACE_DB_PASSWORD"]
    worker_user = os.environ["WORKSPACE_WORKER_DB_USER"]
    worker_password = os.environ["WORKSPACE_WORKER_DB_PASSWORD"]
    owner = connect(owner_user, owner_password)
    runtime = connect(runtime_user, runtime_password)
    worker = connect(worker_user, worker_password)
    try:
        with owner, owner.cursor() as cursor:
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
                "SELECT rolbypassrls, rolsuper FROM pg_roles WHERE rolname=%s", (runtime_user,)
            )
            assert cursor.fetchone() == (False, False)
            cursor.execute(
                "SELECT rolbypassrls, rolsuper FROM pg_roles WHERE rolname=%s", (worker_user,)
            )
            assert cursor.fetchone() == (False, False)
            cursor.execute(
                """SELECT COUNT(*) FROM pg_policies
                   WHERE schemaname='public' AND tablename='sitecontent_contenttypedefinition'"""
            )
            assert cursor.fetchone()[0] == 1
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
                   VALUES (%s,'site-a',%s,'owner','View','{}','private','[]',1,1,NOW(),NOW())""",
                (saved_view_id, str(UUID(int=1))),
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

        assert count(runtime, None) == 0
        runtime.rollback()
        assert count(worker, None) == 2
        worker.rollback()
        assert count(runtime, "site-a") == 1
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
        runtime.close()
        worker.close()
        owner.close()
    print("Workspace PostgreSQL RLS acceptance: PASS")


if __name__ == "__main__":
    main()
