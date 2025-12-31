from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENV: str = Field(default="development")

    # Docs/OpenAPI exposure
    API_DOCS_ENABLED: bool = Field(default=True, description="Enable docs outside production unless explicitly disabled")
    API_DOCS_URL: str = Field(default="/docs")
    API_REDOC_URL: str = Field(default="/redoc")
    API_OPENAPI_URL: str = Field(default="/openapi.json")

    SESSION_COOKIE_NAME: str = Field(default="base2_session")
    CSRF_COOKIE_NAME: str = Field(default="base2_csrf")
    COOKIE_SAMESITE: str = Field(default="Lax")
    COOKIE_SECURE: bool = Field(default=True)

    DJANGO_INTERNAL_BASE_URL: str = Field(default="http://django:8000")

    RATE_LIMIT_REDIS_PREFIX: str = Field(default="rate_limit")

    GOOGLE_OAUTH_CLIENT_ID: Optional[str] = None
    GOOGLE_OAUTH_CLIENT_SECRET: Optional[str] = None
    GOOGLE_OAUTH_REDIRECT_URI: Optional[str] = None
    OAUTH_STATE_SECRET: Optional[str] = None

    AUTH_REFRESH_COOKIE: bool = Field(default=True)

    JWT_SECRET: str = Field(default="")
    TOKEN_PEPPER: str = Field(default="")
    JWT_ISSUER: str = Field(default="base2")
    JWT_AUDIENCE: str = Field(default="base2")
    JWT_EXPIRE_MINUTES: int = Field(default=15, alias="JWT_EXPIRE")
    REFRESH_TOKEN_TTL_DAYS: int = Field(default=30)
    FRONTEND_URL: str = Field(default="")

    # DB settings (FastAPI side)
    DB_CONNECT_TIMEOUT_SEC: int = Field(default=3)
    DB_STATEMENT_TIMEOUT_MS: int = Field(default=3000)
    DB_POOL_MIN: int = Field(default=1)
    DB_POOL_MAX: int = Field(default=5)

    # E2E test mode gate
    E2E_TEST_MODE: bool = Field(default=False)

    def model_post_init(self, __context):
        # Normalize pool bounds
        if self.DB_POOL_MIN < 0:
            object.__setattr__(self, "DB_POOL_MIN", 0)
        if self.DB_POOL_MAX < 1:
            object.__setattr__(self, "DB_POOL_MAX", 1)
        if self.DB_POOL_MAX < self.DB_POOL_MIN:
            object.__setattr__(self, "DB_POOL_MAX", self.DB_POOL_MIN)

        # Default docs policy: disabled in production unless explicitly enabled
        if (self.ENV or "").strip().lower() == "production" and self.API_DOCS_ENABLED:
            # Keep explicit enable if set; otherwise disable
            # No change needed when explicitly enabled via env
            pass

        # Fail-fast in non-local environments.
        env = (self.ENV or "").strip().lower()
        if env in {"staging", "production"}:
            missing = []
            if not (self.JWT_SECRET or "").strip():
                missing.append("JWT_SECRET")
            if not (self.TOKEN_PEPPER or "").strip():
                missing.append("TOKEN_PEPPER")
            if not (self.FRONTEND_URL or "").strip():
                missing.append("FRONTEND_URL")
            if not (self.OAUTH_STATE_SECRET or "").strip():
                missing.append("OAUTH_STATE_SECRET")
            if missing:
                raise RuntimeError("Missing required env var(s): " + ", ".join(missing))

            if env == "production":
                oauth_missing = []
                if not (self.GOOGLE_OAUTH_CLIENT_ID or "").strip():
                    oauth_missing.append("GOOGLE_OAUTH_CLIENT_ID")
                if not (self.GOOGLE_OAUTH_CLIENT_SECRET or "").strip():
                    oauth_missing.append("GOOGLE_OAUTH_CLIENT_SECRET")
                if not (self.GOOGLE_OAUTH_REDIRECT_URI or "").strip():
                    oauth_missing.append("GOOGLE_OAUTH_REDIRECT_URI")
                if oauth_missing:
                    raise RuntimeError("Missing required OAuth env var(s): " + ", ".join(oauth_missing))

            samesite = (self.COOKIE_SAMESITE or "").strip()
            if samesite not in {"Lax", "Strict", "None"}:
                raise RuntimeError(f"Invalid COOKIE_SAMESITE: {samesite}")

            if self.JWT_EXPIRE_MINUTES < 1:
                raise RuntimeError("JWT_EXPIRE must be a positive integer (minutes)")
            if self.REFRESH_TOKEN_TTL_DAYS < 1:
                raise RuntimeError("REFRESH_TOKEN_TTL_DAYS must be a positive integer")


settings = Settings()
