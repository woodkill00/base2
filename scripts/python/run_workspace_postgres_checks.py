#!/usr/bin/env python3
from __future__ import annotations

import os
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


def main() -> None:
    owner_user = os.environ["DB_USER"]
    owner_password = os.environ["DB_PASSWORD"]
    runtime_user = os.environ["WORKSPACE_DB_USER"]
    runtime_password = os.environ["WORKSPACE_DB_PASSWORD"]
    owner = connect(owner_user, owner_password)
    runtime = connect(runtime_user, runtime_password)
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

        assert count(runtime, None) == 0
        runtime.rollback()
        assert count(runtime, "site-a") == 1
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
        owner.close()
    print("Workspace PostgreSQL RLS acceptance: PASS")


if __name__ == "__main__":
    main()
