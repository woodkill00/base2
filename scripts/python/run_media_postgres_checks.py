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
                (list(TABLES),),
            )
            assert all(row[1:] == (True, True) for row in cursor.fetchall())
            cursor.execute(
                """SELECT tablename, policyname FROM pg_policies
                   WHERE schemaname='public' AND tablename = ANY(%s)""",
                (list(TABLES),),
            )
            policies = {table: policy for table, policy in cursor.fetchall()}
            assert set(policies) == set(TABLES), f"media_policy_inventory_mismatch:{policies}"
            for role in (runtime_user, worker_user):
                cursor.execute(
                    "SELECT rolbypassrls, rolsuper, rolcreaterole FROM pg_roles WHERE rolname=%s",
                    (role,),
                )
                assert cursor.fetchone() == (False, False, False)
            cursor.execute("DELETE FROM sitecontent_mediacollection")
            cursor.execute(
                """INSERT INTO sitecontent_mediacollection
                   (id,site_id,title,owner_ref,visibility,shared_roles,lock_version,created_at,updated_at)
                   VALUES (%s,'site-a','Tenant A','owner','private','[]',1,NOW(),NOW()),
                          (%s,'site-b','Tenant B','owner','private','[]',1,NOW(),NOW())""",
                (str(UUID(int=601)), str(UUID(int=602))),
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
        finally:
            runtime.close()
            worker.close()
    finally:
        owner.close()
    print("Media PostgreSQL RLS acceptance: PASS")


if __name__ == "__main__":
    main()
