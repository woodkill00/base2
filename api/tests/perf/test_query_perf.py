import os
import time
from typing import Tuple, List

import psycopg2
import pytest

# These perf tests query Postgres directly and require the service.
# Mark as integration so unit-only runs skip them unless services are available.
pytestmark = [pytest.mark.perf, pytest.mark.integration]


def _get_db_conn_params() -> Tuple[str, int, str, str, str]:
    host = os.getenv("DB_HOST", os.getenv("POSTGRES_HOST", "postgres"))
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    db = os.getenv("POSTGRES_DB", "mydatabase")
    user = os.getenv("DB_USER", os.getenv("POSTGRES_USER", "myuser"))
    password = os.getenv("DB_PASSWORD", os.getenv("POSTGRES_PASSWORD", "mypassword"))
    return host, port, db, user, password


def _connect():
    host, port, db, user, password = _get_db_conn_params()
    return psycopg2.connect(host=host, port=port, dbname=db, user=user, password=password)


def _table_exists(conn, table_name: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT EXISTS (
              SELECT 1
              FROM information_schema.tables
              WHERE table_schema='public' AND table_name=%s
            )
            """,
            (table_name,),
        )
        return bool(cur.fetchone()[0])


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT EXISTS (
              SELECT 1
              FROM information_schema.columns
              WHERE table_schema='public' AND table_name=%s AND column_name=%s
            )
            """,
            (table_name, column_name),
        )
        return bool(cur.fetchone()[0])


def _explain_analyze(conn, sql: str, params: Tuple = ()) -> str:
    with conn.cursor() as cur:
        cur.execute("EXPLAIN (ANALYZE, BUFFERS) " + sql, params)
        plan_rows = cur.fetchall()
        # plan rows are tuples with single text column per row; join into single string
        return "\n".join(r[0] for r in plan_rows)


@pytest.mark.perf
def test_auth_user_lookup_uses_index():
    conn = _connect()
    try:
        if not _table_exists(conn, "auth_user"):
            pytest.skip("auth_user table not present; skipping index check")
        # Prefer username; fall back to email if present
        check_cols = ["username", "email"]
        target_col = None
        for c in check_cols:
            if _column_exists(conn, "auth_user", c):
                target_col = c
                break
        if not target_col:
            pytest.skip("auth_user has no username/email columns; skipping index check")

        plan = _explain_analyze(
            conn,
            f"SELECT id FROM auth_user WHERE {target_col} = %s",
            ("__perf_nonexistent__",),
        )
        # Ensure we are not performing a sequential scan for point lookup
        assert "Seq Scan" not in plan, f"Expected index usage, got plan:\n{plan}"
        assert ("Index Scan" in plan) or ("Bitmap Index Scan" in plan), (
            f"Expected index scan on auth_user({target_col}); plan was:\n{plan}"
        )
    finally:
        conn.close()


@pytest.mark.perf
def test_db_count_latency_p95_within_budget():
    conn = _connect()
    try:
        if not _table_exists(conn, "auth_user"):
            pytest.skip("auth_user table not present; skipping latency budget check")
        samples = int(os.getenv("PERF_DB_SAMPLES", "10"))
        budget_ms = float(os.getenv("PERF_P95_DB_MS", "2000"))
        latencies_ms: List[float] = []
        with conn.cursor() as cur:
            for _ in range(samples):
                start = time.perf_counter()
                cur.execute("SELECT COUNT(*) FROM auth_user")
                _ = cur.fetchone()[0]
                latencies_ms.append((time.perf_counter() - start) * 1000.0)
        latencies_ms.sort()
        # p95 via simple percentile index (conservative for small samples)
        idx = max(0, min(len(latencies_ms) - 1, int(round(0.95 * len(latencies_ms) - 1))))
        p95 = latencies_ms[idx]
        assert p95 <= budget_ms, f"p95 {p95:.2f}ms exceeds budget {budget_ms}ms"
    finally:
        conn.close()
