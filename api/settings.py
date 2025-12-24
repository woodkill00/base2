import os
from typing import Optional


def getenv_bool(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return str(v).strip().lower() in {"1", "true", "yes", "on"}


def getenv(name: str, default: Optional[str] = None) -> Optional[str]:
    return os.environ.get(name, default)


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


settings = Settings()
