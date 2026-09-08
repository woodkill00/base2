#!/usr/bin/env python3
"""Verify the previous application contract across the additive schema window."""

from __future__ import annotations

import os
import sys
from uuid import UUID

import psycopg2


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"old", "new"}:
        raise SystemExit("usage: run_mixed_version_postgres_checks.py old|new")
    connection = psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=os.environ["DB_PORT"],
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )
    try:
        with connection, connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('sitecontent_operationsservice') IS NOT NULL")
            assert cursor.fetchone()[0] is True
            cursor.execute("SELECT to_regclass('sitecontent_tenantquota') IS NOT NULL")
            quota_exists = cursor.fetchone()[0]
            if sys.argv[1] == "old":
                assert quota_exists is False
                cursor.execute(
                    """INSERT INTO sitecontent_operationsservice
                       (id,site_id,service_key,environment,enabled,release_id,created_at,updated_at)
                       VALUES (%s,'mixed-version','api.health','staging',true,'release-old',NOW(),NOW())""",
                    (str(UUID(int=106)),),
                )
            else:
                assert quota_exists is True
                cursor.execute(
                    """SELECT enabled,release_id FROM sitecontent_operationsservice
                       WHERE site_id='mixed-version' AND service_key='api.health'"""
                )
                assert cursor.fetchone() == (True, "release-old")
    finally:
        connection.close()
    print(f"mixed-version-{sys.argv[1]}: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
