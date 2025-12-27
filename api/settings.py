import os
from typing import Optional


def getenv_bool(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return str(v).strip().lower() in {"1", "true", "yes", "on"}


def getenv(name: str, default: Optional[str] = None) -> Optional[str]:
    return os.environ.get(name, default)


def getenv_int(name: str, default: int) -> int:
    v = os.environ.get(name)
    if v is None:
        return default
    try:
        return int(str(v).strip())
    except Exception:
        return default


class Settings:
    SESSION_COOKIE_NAME: str = getenv("SESSION_COOKIE_NAME", "base2_session")
    CSRF_COOKIE_NAME: str = getenv("CSRF_COOKIE_NAME", "base2_csrf")
    COOKIE_SAMESITE: str = getenv("COOKIE_SAMESITE", "Lax")
    COOKIE_SECURE: bool = getenv_bool("COOKIE_SECURE", True)

    DJANGO_INTERNAL_BASE_URL: str = getenv("DJANGO_INTERNAL_BASE_URL", "http://django:8000")

    RATE_LIMIT_REDIS_PREFIX: str = getenv("RATE_LIMIT_REDIS_PREFIX", "rate_limit")

    GOOGLE_OAUTH_CLIENT_ID: Optional[str] = getenv("GOOGLE_OAUTH_CLIENT_ID")
    GOOGLE_OAUTH_CLIENT_SECRET: Optional[str] = getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    GOOGLE_OAUTH_REDIRECT_URI: Optional[str] = getenv("GOOGLE_OAUTH_REDIRECT_URI")
    OAUTH_STATE_SECRET: Optional[str] = getenv("OAUTH_STATE_SECRET")

    AUTH_REFRESH_COOKIE: bool = getenv_bool("AUTH_REFRESH_COOKIE", True)

    # DB settings (FastAPI side)
    DB_CONNECT_TIMEOUT_SEC: int = getenv_int("DB_CONNECT_TIMEOUT_SEC", 3)
    DB_STATEMENT_TIMEOUT_MS: int = getenv_int("DB_STATEMENT_TIMEOUT_MS", 3000)
    DB_POOL_MIN: int = getenv_int("DB_POOL_MIN", 1)
    DB_POOL_MAX: int = getenv_int("DB_POOL_MAX", 5)

    def __init__(self) -> None:
        if self.DB_POOL_MIN < 0:
            self.DB_POOL_MIN = 0
        if self.DB_POOL_MAX < 1:
            self.DB_POOL_MAX = 1
        if self.DB_POOL_MAX < self.DB_POOL_MIN:
            self.DB_POOL_MAX = self.DB_POOL_MIN


settings = Settings()
