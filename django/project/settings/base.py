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

# Performance: Django's default PBKDF2 iterations can be too slow on 1vCPU droplets,
# causing login requests to exceed our verification SLO. Keep PBKDF2 but tune iterations.
PASSWORD_HASHERS = [
    "project.password_hashers.PBKDF2FastPasswordHasher",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
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

# Explicit default auto field
# Use BigAutoField for new primary keys for consistency
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
