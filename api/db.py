import os
from contextlib import contextmanager, suppress
import threading

from psycopg2.pool import ThreadedConnectionPool

from api.settings import settings


_pool: ThreadedConnectionPool | None = None
_pool_lock = threading.Lock()


def _build_dsn() -> str:
    # Prefer an explicit DATABASE_URL if provided
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    host = os.getenv("DB_HOST", "postgres")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    if not all([name, user, password]):
        raise RuntimeError("Missing DB_NAME/DB_USER/DB_PASSWORD")
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


def _get_pool() -> ThreadedConnectionPool:
    global _pool
    if _pool is not None:
        return _pool

    with _pool_lock:
        if _pool is not None:
            return _pool

        dsn = _build_dsn()
        options = f"-c statement_timeout={settings.DB_STATEMENT_TIMEOUT_MS}"
        _pool = ThreadedConnectionPool(
            minconn=settings.DB_POOL_MIN,
            maxconn=settings.DB_POOL_MAX,
            dsn=dsn,
            connect_timeout=settings.DB_CONNECT_TIMEOUT_SEC,
            options=options,
            application_name="base2-api",
        )
        return _pool


def _get_conn() -> object:
    pool = _get_pool()
    # Try a few times in case the pool contains closed connections from a prior bug.
    for _ in range(3):
        conn = pool.getconn()
        try:
            if getattr(conn, "closed", 0):
                with suppress(Exception):
                    pool.putconn(conn, close=True)
                continue
            return conn
        except Exception:
            # If inspection fails, try again
            with suppress(Exception):
                pool.putconn(conn, close=True)
            continue
    # As a fallback, reset the pool and get a fresh connection.
    close_pool()
    pool = _get_pool()
    return pool.getconn()


@contextmanager
def db_conn():
    pool = _get_pool()
    conn = _get_conn()
    try:
        yield conn
    finally:
        with suppress(Exception):
            pool.putconn(conn)


def close_pool() -> None:
    global _pool
    if _pool is None:
        return
    try:
        _pool.closeall()
    finally:
        _pool = None


def db_ping() -> bool:
    try:
        with db_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return True
    except Exception:
        return False
