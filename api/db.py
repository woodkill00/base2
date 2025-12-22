import os
from contextlib import contextmanager

import psycopg2


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


@contextmanager
def db_conn():
    dsn = _build_dsn()
    conn = psycopg2.connect(dsn, connect_timeout=3)
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass


def db_ping() -> bool:
    try:
        with db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return True
    except Exception:
        return False
