Here’s a ready-to-drop-in markdown document you can save as e.g. `fastapi-django-extension.md` in your repo.

---

# FastAPI + Django Extension for `base2` Stack

This document describes how to extend the existing `base2` stack to:

* keep **Traefik** as the only public entrypoint (80/443),
* keep **React** served via **Nginx** (or the existing `react-app` container),
* **replace the Node backend with a FastAPI API service**, and
* **add a Django service** as an internal backend / business-logic layer.

The primary goals are:

* strong separation of concerns,
* minimal attack surface,
* secure defaults for TLS, headers, and networking.

---

## 1. High-level Architecture

### 1.1 Existing `base2` Components (Simplified)

* **Traefik** (edge reverse proxy)

  * Listens on host ports `80` and `443`.
  * Handles TLS (Let’s Encrypt), HTTP→HTTPS redirect, routing.
* **react-app** (React SPA + internal Nginx)

  * Builds React app and serves it via Nginx on internal port `8080`.
  * Traefik routes `Host(${WEBSITE_DOMAIN})` → `react-app`.
* **backend** (Node/Express API) – this will be replaced.
* **postgres** and **pgadmin** – internal DB and admin interface.
* **nginx** (extra reverse proxy for SPA) – optional; can be reused or removed.

### 1.2 Target Architecture After Extension

After the modifications:

* **Traefik** (unchanged externally)

  * Exposed on `80` and `443` only.
  * Routes:

    * `Host(${WEBSITE_DOMAIN})` → React SPA (`react-app`).
    * `Host(${WEBSITE_DOMAIN}) && PathPrefix(/api)` → **FastAPI** (`api` service).
    * (Optionally) `Host(${WEBSITE_DOMAIN}) && PathPrefix(/admin)` → Django admin, behind extra protection.
  * Applies TLS, HTTP→HTTPS redirect, security headers, rate limiting.

* **react-app** (React SPA)

  * Still builds and serves the static SPA using internal Nginx.
  * Uses `REACT_APP_API_URL=https://${WEBSITE_DOMAIN}/api` to call the API.

* **api** (FastAPI)

  * New service, replacing the Node/Express backend.
  * Exposed internally on port `${FASTAPI_PORT}` (e.g. `8000`).
  * Traefik routes `/api/**` to this service.
  * Talks to:

    * **Postgres** directly (for some data), or
    * **Django** (via internal HTTP calls) for more complex business logic.

* **django** (Django application)

  * New service, internal-only (not directly exposed to Traefik by default).
  * Exposed internally on port `${DJANGO_PORT}` (e.g. `8001`).
  * Owns core models, business rules, admin, etc.
  * Uses Postgres via environment-based configuration.

* **postgres** / **pgadmin**

  * Same as before: Postgres used by both FastAPI and Django.
  * **Not** exposed outside the Docker network.

* **Networks**

  * The existing Docker network (e.g. `base2_network`) is used.
  * All services (Traefik, React, FastAPI, Django, Postgres) join this network.
  * Only Traefik is bound to host ports.

---

## 2. Environment Variables (`.env`)

Start from the existing `.env.example` and add/modify the following.

### 2.1 Keep / Adjust These

* **React API URL**
  Update it to use the Traefik `/api` path:

```env
REACT_APP_API_URL=https://${WEBSITE_DOMAIN}/api
```

Make sure the frontend uses `process.env.REACT_APP_API_URL` and never hard-codes `http://localhost:...`.

* **Postgres & networking**
  Keep the existing vars for Postgres, network, and Traefik; just ensure:

```env
NETWORK_NAME=base2_network          # must match
TRAEFIK_DOCKER_NETWORK=base2_network
```

### 2.2 Replace Node Backend Variables with FastAPI

Remove / ignore the Node-specific backend vars:

```env
BACKEND_NODE_VERSION=18-alpine
BACKEND_PORT=5001
BACKEND_HOST_PORT=5001
NODE_ENV=development
```

Add FastAPI-specific variables:

```env
# ============================================
# FastAPI Configuration
# ============================================
FASTAPI_PYTHON_VERSION=3.12-slim
FASTAPI_PORT=8000
FASTAPI_WORKERS=4
ENV=production    # used by FastAPI to control docs visibility
```

You can keep the existing JWT-related settings and re-use them in FastAPI:

```env
JWT_SECRET=change_me
JWT_EXPIRE=7d
RATE_LIMIT_WINDOW_MS=60000
RATE_LIMIT_MAX_REQUESTS=100
```

### 2.3 Add Django-Specific Variables

Add a Django section:

```env
# ============================================
# Django Configuration
# ============================================
DJANGO_PYTHON_VERSION=3.12-slim
DJANGO_PORT=8001
DJANGO_SECRET_KEY=change_me_to_random_long_string
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=${WEBSITE_DOMAIN}
DJANGO_DATABASE_URL=postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:${POSTGRES_PORT}/${POSTGRES_DB}
DJANGO_ADMIN_URL=/admin  # or an obscure path, e.g. /super-secret-admin
```

**Important:**
Generate a strong `DJANGO_SECRET_KEY` and **never** commit your real `.env`.

---

## 3. Docker Compose (`local.docker.yml`) Changes

You’ll modify services to:

1. **Replace** the `backend` (Node) service with an `api` (FastAPI) service.
2. **Add** a `django` service.
3. Keep `react-app`, `traefik`, `postgres`, and `pgadmin` largely as-is.

### 3.1 Replace `backend` Service with `api` (FastAPI)

Locate and remove/replace the existing `backend` service in `local.docker.yml`.

**New `api` service:**

```yaml
  api:
    build:
      context: ./api
      dockerfile: .Dockerfile
      args:
        - PYTHON_VERSION=${FASTAPI_PYTHON_VERSION}
    container_name: ${COMPOSE_PROJECT_NAME}_api
    environment:
      - ENV=production
      - PORT=${FASTAPI_PORT}
      - DB_HOST=postgres
      - DB_PORT=${POSTGRES_PORT}
      - DB_NAME=${POSTGRES_DB}
      - DB_USER=${POSTGRES_USER}
      - DB_PASSWORD=${POSTGRES_PASSWORD}
      - JWT_SECRET=${JWT_SECRET}
      - JWT_EXPIRE=${JWT_EXPIRE}
      - DJANGO_SERVICE_URL=http://django:${DJANGO_PORT}
      - RATE_LIMIT_WINDOW_MS=${RATE_LIMIT_WINDOW_MS}
      - RATE_LIMIT_MAX_REQUESTS=${RATE_LIMIT_MAX_REQUESTS}
    networks:
      - base2_network
    depends_on:
      postgres:
        condition: service_healthy
      django:
        condition: service_started
    restart: unless-stopped
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:${FASTAPI_PORT}/health"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 40s
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api.rule=Host(`${WEBSITE_DOMAIN}`) && PathPrefix(`/api`)"
      - "traefik.http.routers.api.entrypoints=websecure"
      - "traefik.http.routers.api.tls.certresolver=le-staging"
      - "traefik.http.routers.api.middlewares=security-headers,api-ratelimit"
      - "traefik.http.services.api.loadbalancer.server.port=${FASTAPI_PORT}"
```

> Note: `le-staging` can be changed to `le-production` or similar once you are ready for real certificates.

### 3.2 Add `django` Service

Add a new service:

```yaml
  django:
    build:
      context: ./django
      dockerfile: .Dockerfile
      args:
        - PYTHON_VERSION=${DJANGO_PYTHON_VERSION}
    container_name: ${COMPOSE_PROJECT_NAME}_django
    environment:
      - DJANGO_SETTINGS_MODULE=project.settings.production
      - DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
      - DJANGO_DEBUG=${DJANGO_DEBUG}
      - DJANGO_ALLOWED_HOSTS=${DJANGO_ALLOWED_HOSTS}
      - DB_HOST=postgres
      - DB_PORT=${POSTGRES_PORT}
      - DB_NAME=${POSTGRES_DB}
      - DB_USER=${POSTGRES_USER}
      - DB_PASSWORD=${POSTGRES_PASSWORD}
    networks:
      - base2_network
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "manage.py", "check", "--deploy"]
      interval: 60s
      timeout: 10s
      retries: 3
      start_period: 60s
```

**Key points:**

* No `ports:` mapping – Django is not exposed directly.
* No Traefik labels – FastAPI (`api`) is the public entrypoint, Django is internal.

### 3.3 React / Nginx / Traefik / Postgres

* **`react-app`**
  Leave as-is, but make sure it uses the updated `REACT_APP_API_URL`.

* **`traefik`**
  Should already have `80:80` and `443:443` mapped, plus Docker provider enabled. No change needed except for maybe adding security middleware labels (see Section 5).

* **`postgres` and `pgadmin`**
  Leave as-is, confirm they are only on the internal Docker network and not bound to host ports for Postgres.

---

## 4. New Directory Structure and Dockerfiles

You will add two new top-level directories:

```text
api/
django/
```

### 4.1 `api/` (FastAPI) Folder

**Example structure:**

```text
api/
  .Dockerfile
  requirements.txt
  main.py
  app/
    __init__.py
    routes/
      __init__.py
      users.py
    core/
      security.py
      config.py
    models/
      ...
```

**`api/.Dockerfile` example:**

```dockerfile
# api/.Dockerfile
ARG PYTHON_VERSION=3.12-slim
FROM python:${PYTHON_VERSION}

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN useradd -m appuser
USER appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**`api/requirements.txt` (example):**

```txt
fastapi
uvicorn[standard]
httpx
python-jose[cryptography]
passlib[bcrypt]
psycopg2-binary
pydantic
```

**`api/main.py` minimal example:**

```python
from fastapi import FastAPI, HTTPException
import os
import httpx

ENV = os.getenv("ENV", "development")
DJANGO_SERVICE_URL = os.getenv("DJANGO_SERVICE_URL", "http://django:8001")

app = FastAPI(
    title="Base2 API",
    docs_url=None if ENV == "production" else "/docs",
    redoc_url=None if ENV == "production" else "/redoc",
    openapi_url=None if ENV == "production" else "/openapi.json",
)

@app.get("/health")
async def health():
    return {"ok": True, "service": "api"}

@app.get("/api/health")
async def api_health():
    return {"ok": True, "service": "api"}

# Example: proxy call to Django internal route
@app.get("/api/users/me")
async def get_me():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{DJANGO_SERVICE_URL}/internal/users/me")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()
```

You’ll add your actual auth, validation, and business logic on top of this.

---

### 4.2 `django/` Folder

**Example structure:**

```text
django/
  .Dockerfile
  requirements.txt
  manage.py
  project/
    __init__.py
    settings/
      __init__.py
      base.py
      production.py
    urls.py
    wsgi.py
  appname/
    ...
```

You can create it with:

```bash
cd django
django-admin startproject project .
```

**`django/.Dockerfile` example:**

```dockerfile
# django/.Dockerfile
ARG PYTHON_VERSION=3.12-slim
FROM python:${PYTHON_VERSION}

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DJANGO_SETTINGS_MODULE=project.settings.production
ENV PORT=8001

RUN python manage.py collectstatic --noinput

CMD ["gunicorn", "project.wsgi:application", "--bind", "0.0.0.0:8001", "--workers", "3"]
```

**`django/requirements.txt` (example):**

```txt
Django
gunicorn
psycopg2-binary
python-dotenv
```

**`project/settings/production.py` example (partial):**

```python
import os
from .base import *

DEBUG = False

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

ALLOWED_HOSTS = [os.environ.get("DJANGO_ALLOWED_HOSTS", "")]

# Security headers
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "SAMEORIGIN"

CSRF_TRUSTED_ORIGINS = [
    f"https://{os.environ.get('DJANGO_ALLOWED_HOSTS', '')}"
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["DB_NAME"],
        "USER": os.environ["DB_USER"],
        "PASSWORD": os.environ["DB_PASSWORD"],
        "HOST": os.environ["DB_HOST"],
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}
```

You’ll also define internal-only URLs (e.g. `/internal/users/me`) in `project/urls.py` and associated app views.

---

## 5. Traefik Configuration & Security

Traefik is configured via:

* `traefik/traefik.yml` (static config: entrypoints, providers, certresolver)
* `traefik/traefik-config/dynamic.yml` (dynamic config: middlewares, etc.)
* Docker labels on services.

### 5.1 Recommended Approach

Use **Docker labels for routers/services**, and keep `dynamic.yml` for **shared middlewares** like CSRF, HTTPS redirect, security headers, etc.

`dynamic.yml` can be simplified to something like:

```yaml
http:
  middlewares:
    csrf:
      headers:
        hostsProxyHeaders: ["X-CSRFToken"]

    https-redirect:
      redirectScheme:
        scheme: https
        permanent: true

    auth:
      basicAuth:
        users:
          - "testuser:${TRAEFIK_USER}"

    security-headers:
      headers:
        stsSeconds: 31536000
        stsIncludeSubdomains: true
        stsPreload: true
        frameDeny: true
        browserXssFilter: true
        contentTypeNosniff: true
        referrerPolicy: "strict-origin-when-cross-origin"
```

### 5.2 Attaching Middlewares via Labels

Add middleware labels (can be on any service) and attach to routers:

* For **frontend (React SPA)**:

```yaml
  react-app:
    # ...
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.frontend-react.rule=Host(`${WEBSITE_DOMAIN}`)"
      - "traefik.http.routers.frontend-react.entrypoints=websecure"
      - "traefik.http.routers.frontend-react.tls.certresolver=le-staging"
      - "traefik.http.routers.frontend-react.middlewares=security-headers"
```

* For **API (FastAPI)** (already in Section 3.1):

```yaml
      - "traefik.http.routers.api.rule=Host(`${WEBSITE_DOMAIN}`) && PathPrefix(`/api`)"
      - "traefik.http.routers.api.entrypoints=websecure"
      - "traefik.http.routers.api.tls.certresolver=le-staging"
      - "traefik.http.routers.api.middlewares=security-headers,api-ratelimit"
```

Configure `api-ratelimit` middleware via labels as well:

```yaml
      - "traefik.http.middlewares.api-ratelimit.ratelimit.average=50"
      - "traefik.http.middlewares.api-ratelimit.ratelimit.burst=100"
```

If you expose **Django admin**, create a dedicated router with IP-whitelist or basic auth:

```yaml
  django:
    # ...
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.django-admin.rule=Host(`${WEBSITE_DOMAIN}`) && PathPrefix(`${DJANGO_ADMIN_URL}`)"
      - "traefik.http.routers.django-admin.entrypoints=websecure"
      - "traefik.http.routers.django-admin.tls.certresolver=le-staging"
      - "traefik.http.routers.django-admin.middlewares=security-headers,admin-ipwhitelist"

      - "traefik.http.middlewares.admin-ipwhitelist.ipwhitelist.sourcerange=1.2.3.4/32,5.6.7.8/32"
```

(Replace IPs with your real admin IP addresses.)

---

## 6. React Frontend Adjustments

In the frontend:

1. Make sure **all API requests** use `REACT_APP_API_URL`:

   ```js
   const API_URL = process.env.REACT_APP_API_URL;

   export async function getCurrentUser() {
     const res = await fetch(`${API_URL}/users/me`, {
       credentials: "include",
       headers: {
         "Content-Type": "application/json",
       },
     });

     if (!res.ok) {
       throw new Error("Failed to fetch user");
     }

     return res.json();
   }
   ```

2. Rebuild the React app with the new `.env`:

   ```bash
   docker compose -f local.docker.yml build react-app
   ```

---

## 7. Deployment & Smoke Test Checklist

Use this as a step-by-step reference when bringing up the new stack.

### 7.1 One-time Setup

1. Copy `.env.example` to `.env` and fill in:

   * `WEBSITE_DOMAIN`, `TRAEFIK_CERT_EMAIL`, DB creds.
   * `FASTAPI_*` and `DJANGO_*` vars.
   * `REACT_APP_API_URL` pointing to `https://${WEBSITE_DOMAIN}/api`.
2. Create `api/` and `django/` directories with their Dockerfiles, code, and requirements.
3. Modify `local.docker.yml`:

   * Remove/replace `backend` with `api`.
   * Add `django` service.
   * Confirm `base2_network` used consistently.

### 7.2 Build and Run

```bash
docker compose -f local.docker.yml build
docker compose -f local.docker.yml up -d
```

### 7.3 Verify Services

From the host:

* Check containers:

  ```bash
  docker ps
  ```

* Check Traefik (HTTP→HTTPS redirect):

  ```bash
  curl -I http://localhost:${TRAEFIK_HOST_PORT}/
  # Expect 301/302 redirect to https
  ```

* Check API health:

  ```bash
  curl https://${WEBSITE_DOMAIN}/api/health -k
  # (use -k if using staging cert)
  ```

* Check React SPA in browser:
  `https://${WEBSITE_DOMAIN}`

* Check Django migrations & health:

  ```bash
  docker exec -it ${COMPOSE_PROJECT_NAME}_django python manage.py migrate
  docker exec -it ${COMPOSE_PROJECT_NAME}_django python manage.py check --deploy
  ```

### 7.4 Security Quick Audit

* Only Traefik has host ports (80, 443).
* No `ports:` on `api`, `django`, or `postgres`.
* HSTS, X-Frame-Options, Content-Type-Options, etc. active via Traefik and Django.
* Rate limiting attached to `/api`.
* Admin routes (if exposed) are behind IP whitelist and/or strong auth.

---

## 8. Summary

With these changes:

* **All external traffic** hits **Traefik** on `80/443`.
* Traefik routes `/` to the React SPA and `/api/**` to **FastAPI**.
* FastAPI processes requests, handles auth, and calls **Django** or **Postgres** as needed.
* Django remains **internal-only** by default, acting as your core backend/service layer.
* Security is enforced at:

  * **Edge level**: TLS, HTTPS redirect, headers, rate limiting, IP whitelist.
  * **App level**: FastAPI validation, Django secure settings, non-root containers, read-only filesystems.

You can now iteratively refine:

* API schemas and endpoints in FastAPI.
* Business logic and admin interface in Django.
* Frontend flows and UX in the React app.

Save this file as something like `fastapi-django-extension.md` in your repo and use it as your blueprint for the build.
