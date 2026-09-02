import os
from contextlib import contextmanager, suppress
import threading
import re

from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extensions import connection as PsycopgConnection

from api.settings import settings
from api.security.tenant_context import canonical_tenant_id


_pool: ThreadedConnectionPool | None = None
_workspace_pool: ThreadedConnectionPool | None = None
_workspace_worker_pool: ThreadedConnectionPool | None = None
_pool_lock = threading.Lock()


def _project_slug() -> str:
    raw = (os.getenv('PROJECT_NAME') or os.getenv('COMPOSE_PROJECT_NAME') or '').strip().lower()
    raw = re.sub(r'[^a-z0-9_-]+', '-', raw).strip('-_')
    return raw or 'app'


def _build_dsn() -> str:
    # Prefer an explicit DATABASE_URL if provided
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        return database_url

    host = os.getenv('DB_HOST', 'postgres')
    port = os.getenv('DB_PORT', '5432')
    name = os.getenv('DB_NAME')
    user = os.getenv('DB_USER')
    password = os.getenv('DB_PASSWORD')
    if not all([name, user, password]):
        raise RuntimeError('Missing DB_NAME/DB_USER/DB_PASSWORD')
    return f'postgresql://{user}:{password}@{host}:{port}/{name}'


def _build_workspace_dsn() -> str:
    host = os.getenv('DB_HOST', 'postgres')
    port = os.getenv('DB_PORT', '5432')
    name = os.getenv('DB_NAME')
    user = os.getenv('WORKSPACE_DB_USER')
    password = os.getenv('WORKSPACE_DB_PASSWORD')
    if not all([name, user, password]):
        raise RuntimeError('Missing WORKSPACE_DB_USER/WORKSPACE_DB_PASSWORD')
    return f'postgresql://{user}:{password}@{host}:{port}/{name}'


def _build_workspace_worker_dsn() -> str:
    host = os.getenv('DB_HOST', 'postgres')
    port = os.getenv('DB_PORT', '5432')
    name = os.getenv('DB_NAME')
    user = os.getenv('WORKSPACE_WORKER_DB_USER')
    password = os.getenv('WORKSPACE_WORKER_DB_PASSWORD')
    if not all([name, user, password]):
        raise RuntimeError('Missing WORKSPACE_WORKER_DB_USER/WORKSPACE_WORKER_DB_PASSWORD')
    return f'postgresql://{user}:{password}@{host}:{port}/{name}'


def _get_pool() -> ThreadedConnectionPool:
    global _pool
    if _pool is not None:
        return _pool
    with _pool_lock:
        if _pool is not None:
            return _pool

        dsn = _build_dsn()
        options = f'-c statement_timeout={settings.DB_STATEMENT_TIMEOUT_MS}'
        _pool = ThreadedConnectionPool(
            minconn=settings.DB_POOL_MIN,
            maxconn=settings.DB_POOL_MAX,
            dsn=dsn,
            connect_timeout=settings.DB_CONNECT_TIMEOUT_SEC,
            options=options,
            application_name=f'{_project_slug()}-api',
        )
        return _pool


def _get_workspace_pool() -> ThreadedConnectionPool:
    global _workspace_pool
    if _workspace_pool is not None:
        return _workspace_pool


def _get_workspace_worker_pool() -> ThreadedConnectionPool:
    global _workspace_worker_pool
    if _workspace_worker_pool is not None:
        return _workspace_worker_pool
    with _pool_lock:
        if _workspace_worker_pool is None:
            options = f'-c statement_timeout={settings.DB_STATEMENT_TIMEOUT_MS}'
            _workspace_worker_pool = ThreadedConnectionPool(
                minconn=settings.DB_POOL_MIN,
                maxconn=settings.DB_POOL_MAX,
                dsn=_build_workspace_worker_dsn(),
                connect_timeout=settings.DB_CONNECT_TIMEOUT_SEC,
                options=options,
                application_name=f'{_project_slug()}-workspace-worker',
            )
        return _workspace_worker_pool
    with _pool_lock:
        if _workspace_pool is None:
            options = f'-c statement_timeout={settings.DB_STATEMENT_TIMEOUT_MS}'
            _workspace_pool = ThreadedConnectionPool(
                minconn=settings.DB_POOL_MIN,
                maxconn=settings.DB_POOL_MAX,
                dsn=_build_workspace_dsn(),
                connect_timeout=settings.DB_CONNECT_TIMEOUT_SEC,
                options=options,
                application_name=f'{_project_slug()}-workspace',
            )
        return _workspace_pool

def _get_conn() -> PsycopgConnection:
    pool = _get_pool()
    # Try a few times in case the pool contains closed connections from a prior bug.
    for _ in range(3):
        conn = pool.getconn()
        try:
            if getattr(conn, 'closed', 0):
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


def _bind_tenant(conn: PsycopgConnection, tenant_id: str) -> None:
    tenant = canonical_tenant_id(tenant_id)
    # Transaction-local state is consumed by PostgreSQL RLS policies. Parameter
    # binding prevents the tenant identifier from becoming executable SQL.
    with conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, true)", (tenant,))


def _reset_connection(conn: PsycopgConnection) -> None:
    """Remove transaction/session state before a pooled connection is reused."""

    with suppress(Exception):
        conn.rollback()
    with suppress(Exception):
        conn.reset()


@contextmanager
def db_conn(*, tenant_id: str | None = None):
    pool = _get_pool()
    conn = _get_conn()
    try:
        if tenant_id is not None:
            _bind_tenant(conn, tenant_id)
        yield conn
    finally:
        _reset_connection(conn)
        with suppress(Exception):
            pool.putconn(conn)


@contextmanager
def workspace_db_conn(*, tenant_id: str):
    """Use the non-owner, RLS-enforced role for workspace repository access."""
    pool = _get_workspace_pool()
    conn = pool.getconn()
    try:
        if getattr(conn, 'closed', 0):
            pool.putconn(conn, close=True)
            conn = pool.getconn()
        _bind_tenant(conn, tenant_id)
        yield conn
    finally:
        _reset_connection(conn)
        with suppress(Exception):
            pool.putconn(conn)


@contextmanager
def workspace_worker_db_conn(*, tenant_id: str | None = None):
    """Use the worker-only role; global discovery never shares API credentials."""
    pool = _get_workspace_worker_pool()
    conn = pool.getconn()
    try:
        if getattr(conn, 'closed', 0):
            pool.putconn(conn, close=True)
            conn = pool.getconn()
        if tenant_id is not None:
            _bind_tenant(conn, tenant_id)
        yield conn
    finally:
        _reset_connection(conn)
        with suppress(Exception):
            pool.putconn(conn)


def close_pool() -> None:
    global _pool, _workspace_pool, _workspace_worker_pool
    for pool in (_pool, _workspace_pool, _workspace_worker_pool):
        if pool is not None:
            pool.closeall()
    _pool = None
    _workspace_pool = None
    _workspace_worker_pool = None


def db_ping() -> bool:
    try:
        with db_conn() as conn, conn.cursor() as cur:
            cur.execute('SELECT 1')
            cur.fetchone()
        return True
    except Exception:
        return False


def db_schema_ready() -> bool:
    """Verify the Django-owned schema exists without mutating it."""
    try:
        with db_conn() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT to_regclass('public.django_migrations'), "
                "to_regclass('public.api_auth_users')"
            )
            row = cur.fetchone()
        return bool(row and all(row))
    except Exception:
        return False
