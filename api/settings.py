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
    ENV: str = getenv("ENV", "development") or "development"

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

    JWT_SECRET: str = getenv("JWT_SECRET", "") or ""
    TOKEN_PEPPER: str = getenv("TOKEN_PEPPER", "") or ""
    JWT_EXPIRE_MINUTES: int = getenv_int("JWT_EXPIRE", 15)
    REFRESH_TOKEN_TTL_DAYS: int = getenv_int("REFRESH_TOKEN_TTL_DAYS", 30)
    FRONTEND_URL: str = getenv("FRONTEND_URL", "") or ""

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

        # Fail-fast only for explicit production deployments.
        # Keep local/dev/test permissive to avoid breaking onboarding and CI.
        if (self.ENV or "").strip().lower() == "production":
            missing = []
            if not self.JWT_SECRET.strip():
                missing.append("JWT_SECRET")
            if not self.TOKEN_PEPPER.strip():
                missing.append("TOKEN_PEPPER")
            if not (self.OAUTH_STATE_SECRET or "").strip():
                missing.append("OAUTH_STATE_SECRET")
            if missing:
                raise RuntimeError("Missing required env var(s): " + ", ".join(missing))

            samesite = (self.COOKIE_SAMESITE or "").strip()
            if samesite not in {"Lax", "Strict", "None"}:
                raise RuntimeError(f"Invalid COOKIE_SAMESITE: {samesite}")

            if self.JWT_EXPIRE_MINUTES < 1:
                raise RuntimeError("JWT_EXPIRE must be a positive integer (minutes)")
            if self.REFRESH_TOKEN_TTL_DAYS < 1:
                raise RuntimeError("REFRESH_TOKEN_TTL_DAYS must be a positive integer")


settings = Settings()
