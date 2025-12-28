import os

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "change_me")
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()]
if os.environ.get("DJANGO_ALLOW_ALL_HOSTS", "false").lower() == "true":
    ALLOWED_HOSTS = ["*"]
else:
    # Internal/loopback calls (used by deploy-time probes) should not fail with DisallowedHost.
    # Keep this minimal and safe: only add loopback hosts, and only when not allowing all.
    for _h in ("localhost", "127.0.0.1"):
        if _h not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(_h)

# Trust proxy headers from Traefik and ensure correct scheme/host
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Trust CSRF origins derived from allowed hosts (https)
CSRF_TRUSTED_ORIGINS = [f"https://{h}" for h in ALLOWED_HOSTS if h]

# Fail-fast in non-local environments.
_env = (os.environ.get("ENV", "development") or "development").strip().lower()
if _env in {"staging", "production"}:
    _missing = []
    if not SECRET_KEY.strip() or SECRET_KEY.strip() == "change_me":
        _missing.append("DJANGO_SECRET_KEY")
    for _k in ("DB_NAME", "DB_USER", "DB_PASSWORD"):
        if not (os.environ.get(_k) or "").strip():
            _missing.append(_k)
    if _missing:
        raise RuntimeError("Missing required env var(s): " + ", ".join(_missing))

# Align CSRF header with repo convention: `X-CSRF-Token`
CSRF_HEADER_NAME = "HTTP_X_CSRF_TOKEN"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "phonenumber_field",
    "django_countries",
    "common",
    "users",
    "catalog",
]

# Password hashing: production must not run reduced-iteration hashing.
# Use PBKDF2 with a tunable override that enforces a minimum of Django's default iterations.
PASSWORD_HASHERS = [
    "project.password_hashers.PBKDF2TunablePasswordHasher",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "project.middleware.request_id.RequestIdMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "project.wsgi:application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME"),
        "USER": os.environ.get("DB_USER"),
        "PASSWORD": os.environ.get("DB_PASSWORD"),
        "HOST": os.environ.get("DB_HOST", "postgres"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join("/app", "static")

# ============================================
# Email (SMTP)
# ============================================

EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", os.environ.get("EMAIL_USER", ""))
EMAIL_HOST_PASSWORD = os.environ.get(
    "EMAIL_HOST_PASSWORD", os.environ.get("EMAIL_PASSWORD", "")
)

_email_use_tls = os.environ.get("EMAIL_USE_TLS", "true").lower()
EMAIL_USE_TLS = _email_use_tls in ("1", "true", "yes", "on")

DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL",
    os.environ.get("EMAIL_FROM", os.environ.get("EMAIL_FROM_EMAIL", "noreply@example.com")),
)

# ============================================
# Celery
# ============================================

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/1")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# Keep Celery from overriding Django's logging configuration.
CELERYD_HIJACK_ROOT_LOGGER = False
CELERY_WORKER_HIJACK_ROOT_LOGGER = False

# Explicit default auto field
# Use BigAutoField for new primary keys for consistency
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ============================================
# Logging (structured JSON)
# ============================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "project.logging.JsonFormatter",
            "service": "django",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        }
    },
    "loggers": {
        # Ensure request-scoped logs emitted by RequestIdMiddleware aren't filtered out by
        # Django's default logger configuration.
        "django.request": {
            "handlers": ["console"],
            "level": os.environ.get("DJANGO_REQUEST_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
    },
}
