#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

import psycopg2

TABLES = (
    "sitecontent_contenttypedefinition",
    "sitecontent_contentrecord",
    "sitecontent_importjob",
    "sitecontent_exportjob",
    "sitecontent_mediaasset",
    "sitecontent_workspaceauditevent",
)


def main() -> None:
    expected = sys.argv[1] if len(sys.argv) == 2 else ""
    if expected not in {"reversed", "forward", "api-reversed", "api-forward"}:
        raise SystemExit(
            "usage: run_workspace_role_migration_checks.py "
            "reversed|forward|api-reversed|api-forward"
        )
    connection = psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )
    try:
        with connection.cursor() as cursor:
            if expected.startswith("api-"):
                api_role = os.environ["API_RUNTIME_DB_USER"]
                forward = expected == "api-forward"
                cursor.execute(
                    "SELECT has_table_privilege(%s,'api_email_outbox','SELECT'),"
                    "has_table_privilege(%s,'api_email_outbox','UPDATE')",
                    (api_role, api_role),
                )
                assert cursor.fetchone() == (False, False)
                cursor.execute(
                    "SELECT has_table_privilege(%s,'django_migrations','SELECT'),"
                    "has_table_privilege(%s,'sitecontent_contentrecord','SELECT'),"
                    "has_schema_privilege(%s,'public','CREATE')",
                    (api_role, api_role, api_role),
                )
                assert cursor.fetchone() == ((forward), False, False)
                cursor.execute(
                    "SELECT rolsuper,rolcreatedb,rolcreaterole,rolbypassrls "
                    "FROM pg_roles WHERE rolname=%s",
                    (api_role,),
                )
                assert cursor.fetchone() == (False, False, False, False)
                cursor.execute(
                    "SELECT COUNT(*) FROM pg_proc WHERE proname='base2_enqueue_email'"
                )
                assert (cursor.fetchone()[0] == 1) is forward
                if forward:
                    cursor.execute(
                        "SELECT has_function_privilege(%s,"
                        "'base2_enqueue_email(uuid,text,text,text,text)','EXECUTE')",
                        (api_role,),
                    )
                    assert cursor.fetchone()[0] is True
                cursor.execute(
                    "SELECT COUNT(*) FROM pg_policies "
                    "WHERE policyname='api_runtime_tenant_scope'"
                )
                assert (cursor.fetchone()[0] == 7) is forward
                cursor.execute(
                    "SELECT relrowsecurity,relforcerowsecurity FROM pg_class "
                    "WHERE oid='api_user_preferences'::regclass"
                )
                assert cursor.fetchone() == ((True, True) if forward else (False, False))
                if forward:
                    cursor.execute(
                        "SELECT EXISTS (SELECT 1 FROM django_migrations "
                        "WHERE app='sitecontent' AND name='0033_api_schema_readiness')"
                    )
                    assert cursor.fetchone()[0] is True
                    cursor.execute(
                        "SELECT EXISTS (SELECT 1 FROM api_schema_migrations "
                        "WHERE version='013_add_global_data_rights_operations')"
                    )
                    assert cursor.fetchone()[0] is True
                print(f"API runtime migration {expected}: PASS")
                return
            cursor.execute("SELECT COUNT(*) FROM sitecontent_contenttypedefinition")
            assert cursor.fetchone()[0] == 2
            cursor.execute("SELECT COUNT(*) FROM sitecontent_contentrecord")
            assert cursor.fetchone()[0] == 3
            worker = os.environ["WORKSPACE_WORKER_DB_USER"]
            runtime = os.environ["WORKSPACE_DB_USER"]
            for table in TABLES:
                cursor.execute(
                    "SELECT has_table_privilege(%s, %s, 'SELECT')", (worker, table)
                )
                assert cursor.fetchone()[0] is (expected == "forward")
                cursor.execute(
                    "SELECT has_table_privilege(%s, %s, 'SELECT')", (runtime, table)
                )
                assert cursor.fetchone()[0] is True
            cursor.execute(
                """SELECT qual FROM pg_policies
                   WHERE schemaname='public'
                     AND tablename='sitecontent_contenttypedefinition'
                     AND policyname='sitecontent_contenttypedefinition_tenant_scope'"""
            )
            policy = str(cursor.fetchone()[0])
            assert (worker in policy) is (expected == "forward")
    finally:
        connection.close()
    print(f"Workspace worker-role migration {expected}: PASS")


if __name__ == "__main__":
    main()
