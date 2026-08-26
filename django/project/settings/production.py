from .base import *  # noqa
import os

DEBUG = False

# Security headers (controlled via env for internal service calls)
SECURE_SSL_REDIRECT = os.environ.get("DJANGO_SECURE_SSL_REDIRECT", "false").lower() == "true"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_NAME = os.environ.get("SESSION_COOKIE_NAME", "session")
CSRF_COOKIE_NAME = os.environ.get("CSRF_COOKIE_NAME", "csrf")
SESSION_COOKIE_SAMESITE = os.environ.get("COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE = os.environ.get("COOKIE_SAMESITE", "Lax")
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "SAMEORIGIN"

# Build CSRF trusted origins from an explicit deployment boundary when supplied,
# otherwise derive the public HTTPS hosts for backwards compatibility.
_hosts = os.environ.get("DJANGO_ALLOWED_HOSTS", "")
_internal = {"django", "api", "postgres", "pgadmin", "traefik"}
_trusted = os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").strip()
CSRF_TRUSTED_ORIGINS = (
    [origin.strip() for origin in _trusted.split(",") if origin.strip()]
    if _trusted
    else [
        f"https://{h.strip()}"
        for h in _hosts.split(",")
        if h.strip() and ("." in h.strip()) and h.strip().lower() not in _internal
    ]
)

# Internal base URL for reverse proxy integrations
DJANGO_INTERNAL_BASE_URL = os.environ.get("DJANGO_INTERNAL_BASE_URL", "http://django:8000")
