from .base import *  # noqa
import os

DEBUG = False

# Security headers (controlled via env for internal service calls)
SECURE_SSL_REDIRECT = os.environ.get("DJANGO_SECURE_SSL_REDIRECT", "false").lower() == "true"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "SAMEORIGIN"

# Build CSRF trusted origins from comma-separated hosts
_hosts = os.environ.get("DJANGO_ALLOWED_HOSTS", "")
_internal = {"django", "api", "postgres", "pgadmin", "traefik"}
CSRF_TRUSTED_ORIGINS = [
    f"https://{h.strip()}"
    for h in _hosts.split(",")
    if h.strip() and ("." in h.strip()) and h.strip().lower() not in _internal
]