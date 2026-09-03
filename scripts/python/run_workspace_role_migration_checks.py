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
    if expected not in {"reversed", "forward"}:
        raise SystemExit("usage: run_workspace_role_migration_checks.py reversed|forward")
    connection = psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )
    try:
        with connection.cursor() as cursor:
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
