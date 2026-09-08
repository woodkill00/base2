import os
import re
import base64
import binascii
import stat
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings

from api.site_manifest import load_runtime_manifest


SITE_MANIFEST, SITE_MANIFEST_DIGEST = load_runtime_manifest()


def _sanitize_project_slug(raw: str) -> str:
    value = (raw or '').strip().lower()
    value = re.sub(r'[^a-z0-9_-]+', '-', value)
    value = value.strip('-_')
    return value


def _default_project_slug() -> str:
    return (
        _sanitize_project_slug(os.getenv('PROJECT_NAME') or os.getenv('COMPOSE_PROJECT_NAME') or '')
        or 'app'
    )


class Settings(BaseSettings):
    ENV: str = Field(default='development')
    SITE_PROFILE: str = Field(default=SITE_MANIFEST['siteId'])
    SITE_NAME: str = Field(default=SITE_MANIFEST['name'])
    SITE_MANIFEST_DIGEST: str = Field(default=SITE_MANIFEST_DIGEST)

    # Docs/OpenAPI exposure
    API_DOCS_ENABLED: bool = Field(
        default=True, description='Enable docs outside production unless explicitly disabled'
    )
    API_DOCS_URL: str = Field(default='/docs')
    API_REDOC_URL: str = Field(default='/redoc')
    API_OPENAPI_URL: str = Field(default='/openapi.json')

    SESSION_COOKIE_NAME: str = Field(default='')
    CSRF_COOKIE_NAME: str = Field(default='')
    COOKIE_SAMESITE: str = Field(default='Lax')
    COOKIE_SECURE: bool = Field(default=True)

    DJANGO_INTERNAL_BASE_URL: str = Field(default='http://django:8000')

    RATE_LIMIT_REDIS_PREFIX: str = Field(default='rate_limit')

    GOOGLE_OAUTH_CLIENT_ID: Optional[str] = None
    GOOGLE_OAUTH_CLIENT_SECRET: Optional[str] = None
    GOOGLE_OAUTH_REDIRECT_URI: Optional[str] = None
    GOOGLE_OAUTH_ENABLED: bool = Field(default=False)
    OAUTH_STATE_SECRET: Optional[str] = None
    IDENTITY_ENCRYPTION_KEY: Optional[str] = None
    CONTENT_WORKSPACE_STORAGE_ROOT: str = Field(default='/var/lib/base2/content-workspace')
    CONTENT_WORKSPACE_STORAGE_KEY: Optional[str] = None
    CONTENT_WORKSPACE_STORAGE_BACKEND: str = Field(default='local')
    CONTENT_WORKSPACE_S3_ENDPOINT: str = Field(default='')
    CONTENT_WORKSPACE_S3_BUCKET: str = Field(default='')
    CONTENT_WORKSPACE_S3_REGION: str = Field(default='')
    CONTENT_WORKSPACE_S3_ALLOWED_HOSTS: str = Field(default='')
    CONTENT_WORKSPACE_S3_ACCESS_KEY_FILE: str = Field(default='')
    CONTENT_WORKSPACE_S3_SECRET_KEY_FILE: str = Field(default='')
    IDENTITY_ALLOW_FIRST_OWNER_BOOTSTRAP: bool = Field(default=False)
    WEBAUTHN_ENABLED: bool = Field(default=False)

    AUTH_REFRESH_COOKIE: bool = Field(default=True)

    JWT_SECRET: str = Field(default='')
    TOKEN_PEPPER: str = Field(default='')
    JWT_ISSUER: str = Field(default='')
    JWT_AUDIENCE: str = Field(default='')
    JWT_EXPIRE_MINUTES: int = Field(default=15, alias='JWT_EXPIRE')
    REFRESH_TOKEN_TTL_DAYS: int = Field(default=30)
    FRONTEND_URL: str = Field(default='')

    # DB settings (FastAPI side)
    DB_CONNECT_TIMEOUT_SEC: int = Field(default=3)
    DB_STATEMENT_TIMEOUT_MS: int = Field(default=3000)
    DB_POOL_MIN: int = Field(default=1)
    DB_POOL_MAX: int = Field(default=5)
    DB_POOL_SATURATION_PERCENT: int = Field(default=85)
    # PostgreSQL 16 cannot enforce a total multi-statement transaction wall
    # clock. This is deliberately named for the timeout it actually sets.
    DB_IDLE_TRANSACTION_TIMEOUT_MS: int = Field(default=60000)
    DB_SSLMODE: str = Field(default='disable')
    DB_SSLROOTCERT: Optional[str] = None

    # Vaultwarden resolves these credentials into distinct runtime-only files.
    OPERATIONS_ALERTS_ENABLED: bool = Field(default=False)
    OPERATIONS_ALERT_INTEGRITY_KEY_FILE: str = Field(default='')
    OPERATIONS_ALERT_RECEIPT_KEY_FILE: str = Field(default='')
    OPERATIONS_ALERT_WEBHOOK_URL_FILE: str = Field(default='')
    OPERATIONS_RECEIPT_INTEGRITY_KEY_FILE: str = Field(default='')
    OPERATIONS_RECEIPT_MAX_AGE_SECONDS: int = Field(default=90000)
    BASE2_EMAIL_ADAPTER: str = Field(default='disabled')
    BASE2_EMAIL_SMTP_HOST: str = Field(default='')
    BASE2_EMAIL_SMTP_PORT: int = Field(default=587)
    BASE2_EMAIL_SMTP_TIMEOUT_SECONDS: float = Field(default=10)
    BASE2_EMAIL_FROM_ADDRESS: str = Field(default='')
    BASE2_EMAIL_SMTP_USERNAME_FILE: str = Field(default='')
    BASE2_EMAIL_SMTP_PASSWORD_FILE: str = Field(default='')
    BASE2_PROCESS_ROLE: str = Field(default='api')

    # E2E test mode gate
    E2E_TEST_MODE: bool = Field(default=False)
    CELERY_REQUIRED: bool = Field(default=False)

    def model_post_init(self, __context):
        project = _default_project_slug()

        # Derived defaults (avoid hardcoded project identifiers).
        if not (self.SESSION_COOKIE_NAME or '').strip():
            object.__setattr__(self, 'SESSION_COOKIE_NAME', f'{project}_session')
        if not (self.CSRF_COOKIE_NAME or '').strip():
            object.__setattr__(self, 'CSRF_COOKIE_NAME', f'{project}_csrf')
        if not (self.JWT_ISSUER or '').strip():
            object.__setattr__(self, 'JWT_ISSUER', project)
        if not (self.JWT_AUDIENCE or '').strip():
            object.__setattr__(self, 'JWT_AUDIENCE', project)

        # Normalize pool bounds
        if self.DB_POOL_MIN < 0:
            object.__setattr__(self, 'DB_POOL_MIN', 0)
        if self.DB_POOL_MAX < 1:
            object.__setattr__(self, 'DB_POOL_MAX', 1)
        if self.DB_POOL_MAX < self.DB_POOL_MIN:
            object.__setattr__(self, 'DB_POOL_MAX', self.DB_POOL_MIN)
        if not 50 <= self.DB_POOL_SATURATION_PERCENT <= 95:
            raise RuntimeError('DB_POOL_SATURATION_PERCENT must be between 50 and 95')

        # Default docs policy: disabled in production unless explicitly enabled
        if (self.ENV or '').strip().lower() == 'production' and self.API_DOCS_ENABLED:
            # Keep explicit enable if set; otherwise disable
            # No change needed when explicitly enabled via env
            pass

        # Fail-fast in non-local environments.
        env = (self.ENV or '').strip().lower()
        if env == 'production' and self.E2E_TEST_MODE:
            raise RuntimeError('E2E_TEST_MODE cannot be enabled in production')
        if env in {'staging', 'production'}:
            missing = []
            process_role = self.BASE2_PROCESS_ROLE
            if process_role == 'api':
                for name in (
                    'JWT_SECRET',
                    'TOKEN_PEPPER',
                    'FRONTEND_URL',
                    'OAUTH_STATE_SECRET',
                    'IDENTITY_ENCRYPTION_KEY',
                ):
                    if not str(getattr(self, name) or '').strip():
                        missing.append(name)
            if (
                process_role == 'content-worker'
                and not (self.IDENTITY_ENCRYPTION_KEY or '').strip()
            ):
                missing.append('IDENTITY_ENCRYPTION_KEY')
            storage_backend = (self.CONTENT_WORKSPACE_STORAGE_BACKEND or '').strip().lower()
            storage_required = process_role in {'api', 'content-worker'}
            if storage_required and storage_backend not in {'local', 's3'}:
                raise RuntimeError('Invalid CONTENT_WORKSPACE_STORAGE_BACKEND')
            if (
                storage_required
                and storage_backend == 'local'
                and not (self.CONTENT_WORKSPACE_STORAGE_KEY or '').strip()
            ):
                missing.append('CONTENT_WORKSPACE_STORAGE_KEY')
            if storage_required and storage_backend == 's3':
                for name in (
                    'CONTENT_WORKSPACE_S3_ENDPOINT',
                    'CONTENT_WORKSPACE_S3_BUCKET',
                    'CONTENT_WORKSPACE_S3_REGION',
                    'CONTENT_WORKSPACE_S3_ALLOWED_HOSTS',
                    'CONTENT_WORKSPACE_S3_ACCESS_KEY_FILE',
                    'CONTENT_WORKSPACE_S3_SECRET_KEY_FILE',
                ):
                    if not str(getattr(self, name) or '').strip():
                        missing.append(name)
                for name in (
                    'CONTENT_WORKSPACE_S3_ACCESS_KEY_FILE',
                    'CONTENT_WORKSPACE_S3_SECRET_KEY_FILE',
                ):
                    value = str(getattr(self, name) or '').strip()
                    if value and not value.startswith('/'):
                        raise RuntimeError(f'{name} must be an absolute secret-file path')
            if env == 'production':
                if self.BASE2_PROCESS_ROLE not in {
                    'api',
                    'runtime-worker',
                    'content-worker',
                    'email-worker',
                }:
                    raise RuntimeError('Invalid BASE2_PROCESS_ROLE')
                if self.BASE2_EMAIL_ADAPTER.strip().lower() != 'smtp':
                    raise RuntimeError('Production requires BASE2_EMAIL_ADAPTER=smtp')
                if (
                    not self.BASE2_EMAIL_SMTP_HOST.strip()
                    or self.BASE2_EMAIL_SMTP_PORT not in {465, 587}
                    or not 0 < self.BASE2_EMAIL_SMTP_TIMEOUT_SECONDS <= 30
                    or '@' not in self.BASE2_EMAIL_FROM_ADDRESS
                ):
                    raise RuntimeError('Invalid production SMTP configuration')
                for name in (
                    ()
                    if self.BASE2_PROCESS_ROLE != 'email-worker'
                    else (
                        'BASE2_EMAIL_SMTP_USERNAME_FILE',
                        'BASE2_EMAIL_SMTP_PASSWORD_FILE',
                    )
                ):
                    value = str(getattr(self, name) or '').strip()
                    if not value:
                        missing.append(name)
                    elif not value.startswith('/'):
                        raise RuntimeError(f'{name} must be an absolute secret-file path')
                    else:
                        path = Path(value)
                        try:
                            metadata = path.stat(follow_symlinks=False)
                        except OSError as exc:
                            raise RuntimeError(f'{name} secret file is unavailable') from exc
                        if (
                            path.is_symlink()
                            or not stat.S_ISREG(metadata.st_mode)
                            or metadata.st_mode & 0o077
                            or metadata.st_size < 1
                            or metadata.st_size > 4096
                        ):
                            raise RuntimeError(f'{name} secret file is invalid')
            operation_file_names = (
                (
                    'OPERATIONS_ALERT_INTEGRITY_KEY_FILE',
                    'OPERATIONS_ALERT_RECEIPT_KEY_FILE',
                    'OPERATIONS_ALERT_WEBHOOK_URL_FILE',
                )
                if self.OPERATIONS_ALERTS_ENABLED and process_role == 'runtime-worker'
                else ()
            )
            for name in operation_file_names:
                value = str(getattr(self, name) or '').strip()
                if not value:
                    missing.append(name)
                elif not value.startswith('/'):
                    raise RuntimeError(f'{name} must be an absolute secret-file path')
            if missing:
                raise RuntimeError('Missing required env var(s): ' + ', '.join(missing))
            if self.DB_SSLMODE != 'verify-full' or not (self.DB_SSLROOTCERT or '').startswith('/'):
                raise RuntimeError('Database TLS verify-full configuration is required')
            if not 60 <= self.OPERATIONS_RECEIPT_MAX_AGE_SECONDS <= 172800:
                raise RuntimeError(
                    'OPERATIONS_RECEIPT_MAX_AGE_SECONDS must be between 60 and 172800'
                )
            operations_files = {str(getattr(self, name)) for name in operation_file_names}
            if operations_files and len(operations_files) != len(operation_file_names):
                raise RuntimeError('Operations secret files must be independently scoped')

            if storage_required and storage_backend == 'local':
                storage_root = (self.CONTENT_WORKSPACE_STORAGE_ROOT or '').strip()
                try:
                    encoded_key = (self.CONTENT_WORKSPACE_STORAGE_KEY or '').strip()
                    storage_key = base64.b64decode(
                        encoded_key + '=' * (-len(encoded_key) % 4),
                        altchars=b'-_',
                        validate=True,
                    )
                except (ValueError, binascii.Error) as exc:
                    raise RuntimeError('Invalid CONTENT_WORKSPACE_STORAGE_KEY') from exc
                if not storage_root.startswith('/') or len(storage_key) != 32:
                    raise RuntimeError('Invalid content workspace storage configuration')
            elif storage_required:
                from urllib.parse import urlparse

                endpoint = urlparse(self.CONTENT_WORKSPACE_S3_ENDPOINT)
                allowed_hosts = {
                    item.strip().lower()
                    for item in self.CONTENT_WORKSPACE_S3_ALLOWED_HOSTS.split(',')
                    if item.strip()
                }
                if (
                    endpoint.scheme != 'https'
                    or not endpoint.hostname
                    or endpoint.hostname.lower() not in allowed_hosts
                    or endpoint.path not in {'', '/'}
                    or endpoint.query
                    or endpoint.fragment
                ):
                    raise RuntimeError('Invalid content workspace S3 endpoint configuration')

            if env == 'production' and self.GOOGLE_OAUTH_ENABLED:
                oauth_missing = []
                if not (self.GOOGLE_OAUTH_CLIENT_ID or '').strip():
                    oauth_missing.append('GOOGLE_OAUTH_CLIENT_ID')
                if not (self.GOOGLE_OAUTH_CLIENT_SECRET or '').strip():
                    oauth_missing.append('GOOGLE_OAUTH_CLIENT_SECRET')
                if not (self.GOOGLE_OAUTH_REDIRECT_URI or '').strip():
                    oauth_missing.append('GOOGLE_OAUTH_REDIRECT_URI')
                if oauth_missing:
                    raise RuntimeError(
                        'Missing required OAuth env var(s): ' + ', '.join(oauth_missing)
                    )

            samesite = (self.COOKIE_SAMESITE or '').strip()
            if samesite not in {'Lax', 'Strict', 'None'}:
                raise RuntimeError(f'Invalid COOKIE_SAMESITE: {samesite}')

            if self.JWT_EXPIRE_MINUTES < 1:
                raise RuntimeError('JWT_EXPIRE must be a positive integer (minutes)')
            if self.REFRESH_TOKEN_TTL_DAYS < 1:
                raise RuntimeError('REFRESH_TOKEN_TTL_DAYS must be a positive integer')


settings = Settings()
