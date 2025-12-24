
# Implementation Plan: Full-stack Baseline (Django + FastAPI + React)

**Branch**: `001-django-fastapi-react` | **Date**: 2025-12-24 | **Spec**: `specs/001-django-fastapi-react/spec.md`
**Input**: Feature specification from `specs/001-django-fastapi-react/spec.md`

## Summary

Deliver a production-like, staging-safe full stack behind Traefik (staging-only ACME) with secure user auth flows (signup/login/logout), CSRF protections for cookie auth, Google sign-in, and deploy/update/test exclusively via `digital_ocean/scripts/powershell/deploy.ps1`.

## Technical Context

**Language/Version**: Python 3.12 (Django + FastAPI), Node 18 (React), PowerShell 5.1 (deploy/test)

**Primary Dependencies**: Docker Compose, Traefik v3.1, Django + Gunicorn, FastAPI + Uvicorn, React 18, Nginx, Postgres 16, Redis 7.2, Celery, Flower

**Storage**: PostgreSQL 16 (service `postgres`; Django migrations are canonical)

**Testing**: PowerShell deploy-time verification (`digital_ocean/scripts/powershell/test.ps1`), React Jest; add pytest for Django/FastAPI unit+integration suites (gated via `deploy.ps1`)

**Target Platform**: Linux Docker host (DigitalOcean droplet) + local dev on Windows

**Project Type**: Multi-service Compose application

**Performance Goals**: Health probes p95 < 5s in staging-like environment

**Constraints**: deploy/update/test via `deploy.ps1`; staging-only ACME; Traefik is the only published port; cookie auth + CSRF; no sensitive browser token storage

**Scale/Scope**: Single droplet, single Postgres, single Redis, low-to-moderate traffic

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

1) **Spec → Plan → Tasks discipline**: PASS (spec exists; this plan stays technical; tasks are explicitly out of scope for `/speckit.plan`).
2) **TDD by default**: PASS (plan requires unit/integration/e2e coverage and deploy gates).
3) **Environment parity**: PASS (staging and local share the same Compose topology; differences explicitly limited to TLS and dev ergonomics).
4) **Container-first, Compose-first**: PASS (all services are Compose services; healthchecks and dependencies documented).
5) **Single-entrypoint operations**: PASS (no alternative deploy path introduced; integrations are via `deploy.ps1`).
6) **Observability/artifacts**: PASS (deploy/test scripts already capture artifacts; plan extends artifacts for OpenAPI and auth flows).
7) **Django is domain source of truth**: PASS (new domain concepts begin in `django/common/models.py`; user-related models may be wrapped/adapted in `django/users/models.py` without forking semantics).
8) **FastAPI mirrors Django semantics**: PASS with explicit plan gates (mirror-contract tests + schema drift checks).
9) **React contract and cookie security**: PASS (plan uses HttpOnly cookies + CSRF; avoids localStorage tokens).
10) **Trust boundaries and internal-only surfaces**: PASS (Traefik is the only published port; admin tools gated by allowlist/auth).
11) **TLS/certs policy**: PASS (Traefik resolver is `le-staging`; `test.ps1` verifies staging resolver usage).

**Repo hygiene note (non-blocking)**: The Spec-Kit scripts warn that multiple specs share prefix `001` (`001-fastapi-django-deploy` and `001-django-fastapi-react`). This plan proceeds on the current branch directory; a future cleanup should renumber one spec directory to avoid tooling ambiguity.

## Project Structure

### Documentation (this feature)

```text
specs/001-django-fastapi-react/
├── plan.md              # This file
├── spec.md              # Feature requirements (user-facing)
├── research.md          # Phase 0 output: decisions + tradeoffs
├── data-model.md        # Phase 1 output: entities + constraints
├── quickstart.md        # Phase 1 output: runnable steps + verification
├── contracts/           # Phase 1 output: OpenAPI contract(s)
└── tasks.md             # Phase 2 output (/speckit.tasks) - NOT created here
```

### Source Code (repository root)

```text
api/                    # FastAPI service (API surface) + Celery app (current)
django/                 # Django service (domain models + migrations + admin)
react-app/              # React SPA (built and served from Nginx runtime image)

traefik/                # Edge proxy config (staging-only ACME)
nginx/                  # Standalone Nginx service (internal; optional proxy role)
postgres/               # DB init scripts
pgadmin/                # pgAdmin config/data volume

digital_ocean/          # Deploy automation (deploy.ps1 is authoritative)
local.docker.yml        # Local/staging-like topology
.env.example            # Required env vars (must remain complete)
```

**Structure Decision**: This repo is a Compose-first web application with explicit service directories (`api/`, `django/`, `react-app/`, infra at root). No new top-level app folders are introduced.

---

## 1) Authoritative Service Inventory (full stack)

This inventory MUST match `local.docker.yml`, Traefik dynamic routing, deploy orchestration, and `.env.example`.

### 1.1 Edge + routing

**traefik**
- Public edge entrypoint (ports 80/443)
- Responsibilities: TLS termination, host/path routing, security headers middleware, coarse rate limiting, retries
- TLS policy: staging-only cert issuance via resolver `le-staging` (enforced in `traefik/traefik.yml` and verified in deploy tests)
- Provider: file provider only (dynamic config in `traefik/dynamic.yml`)

### 1.2 Web serving

**react-app**
- React SPA built in container, served by Nginx runtime on port 8080 (internal-only behind Traefik)

**nginx**
- Standalone internal Nginx (present in compose). Used only if needed for internal proxying; must never become a second public edge.

**nginx-static**
- Serves Django-collected static files (volume `django_static`), exposed internally at port 8081 and routed only for Django admin static.

### 1.3 Application services

**api (FastAPI)**
- Primary API surface (external paths are under `/api/*` as seen by clients; Traefik strips `/api` before forwarding)
- Owns: OpenAPI exposure, auth/session endpoints, CSRF enforcement, OAuth handshake endpoints, health probes, Celery helper endpoints

**django**
- Canonical domain models, migrations, and Django admin
- Runs `migrate`, `check --deploy`, `collectstatic` during container start (also re-run by deploy script)

### 1.4 Data & messaging

**postgres**
- Primary database
- Internal-only; healthchecked via `pg_isready`

**redis**
- Internal-only ephemeral store
- Used for: Celery broker (+ optional result backend), rate-limit counters (recommended), optional session-related state

### 1.5 Background processing and admin UIs

**celery-worker**
- Executes async jobs
- Current wiring uses the `api/` image and Celery app in `api/tasks.py`

**celery-beat**
- Schedules periodic jobs (same Celery app)

**flower**
- Celery monitoring UI
- Internal-only by default; if routed, must be gated (basic auth + allowlist in Traefik)

**pgadmin**
- DB admin UI
- Internal-only by default; if routed, must be gated (basic auth + allowlist in Traefik)

---

## 2) Topology Diagram (text)

### 2.1 Request flows

```text
Internet
  |
  v
[traefik] (public edge; TLS; headers; rate limit; retry)
  |------------------ host: WEBSITE_DOMAIN, path: /        -> [react-app]
  |------------------ host: WEBSITE_DOMAIN, path: /api/*   -> [api]   (Traefik strips /api)
  |
  |-- host: admin.<domain> or /admin (guarded)             -> [django]
  |-- host: admin.<domain>, path: /static/*                -> [nginx-static]
  |-- host: pgadmin.<domain> (guarded)                     -> [pgadmin]
  |-- host: flower.<domain> (guarded)                      -> [flower]
  |-- host: traefik.<domain> (guarded)                     -> [traefik dashboard]
  |
  +-- internal network only -------------------------------> [postgres]
  +-- internal network only -------------------------------> [redis]
  +-- internal network only -------------------------------> [celery-worker]
  +-- internal network only -------------------------------> [celery-beat]
```

### 2.2 Background job flows

```text
[api] -> enqueue -> [redis broker] -> [celery-worker]
[celery-beat] -> schedule -> [redis broker] -> [celery-worker]
[flower] -> reads -> [redis] + worker state
```

---

## 3) Environment Parity & Compose Discipline

### 3.1 Local (`local.docker.yml`)

- Local runs the same service set as staging-like deploy, including edge, app services, DB, Redis, and admin UIs.
- Healthchecks are mandatory and used as the primary readiness signal.
- Dependency ordering uses `depends_on: condition: service_healthy` where applicable.

### 3.2 Staging-like droplet

- Deployed via `digital_ocean/scripts/powershell/deploy.ps1`.
- Uses the same compose file (`local.docker.yml`) on the droplet to enforce parity.
- TLS issuance MUST remain staging-only (`le-staging`), verified in `digital_ocean/scripts/powershell/test.ps1`.

---

## 4) Traefik Routing, Middleware, and TLS Policy

### 4.1 Routing rules (authoritative)

- Web UI: `Host(WEBSITE_DOMAIN|www.WEBSITE_DOMAIN) && PathPrefix(/)` -> `react-app:8080`
- API: `Host(WEBSITE_DOMAIN) && PathPrefix(/api)` -> `api:FASTAPI_PORT` with `stripPrefix(/api)`
- Django admin: subdomain or path, gated by basic auth + allowlist
- Admin UIs (pgAdmin/Flower/Traefik dashboard): subdomain routes gated by basic auth + allowlist

### 4.2 Middleware policy

- Security headers applied to all public routes.
- Admin/ops routes use a no-HSTS variant suitable for staging.
- Coarse rate limiting at the edge for burst control (auth endpoints included).

### 4.3 Staging-only TLS guardrails

- Traefik certificates resolver is `le-staging` with `caServer` pointing at the staging directory.
- Deploy verification MUST fail if production ACME endpoints are configured.

---

## 5) Static Asset Strategy

### 5.1 React assets

- Build-time: React production build created in `react-app/.Dockerfile`.
- Runtime: Nginx serves static files at port 8080.
- Cache policy (already aligned with current image):
  - Hashed assets: `Cache-Control: public, immutable` with long expiry
  - HTML entrypoint: no immutable caching (ensures deploy updates take effect)

### 5.2 Django static

- Django collects static to `django_static` volume.
- `nginx-static` serves `/static/*` and is only routed for admin subdomain.

---

## 6) Auth, Sessions, CSRF, and OAuth

### 6.1 Cookie-based auth approach (baseline)

To satisfy the constitution (no browser token storage) while keeping implementation feasible in FastAPI:

- Use **HttpOnly, Secure, SameSite** cookies as the primary credential carrier.
- Use a CSRF protection mechanism appropriate for SPA + cookie auth:
  - double-submit cookie (non-HttpOnly CSRF cookie) + `X-CSRF-Token` header, OR
  - per-session CSRF token issued on login and required on state-changing requests.

### 6.2 Signup/login/logout and enumeration resistance

- Signup returns generic errors for duplicate email/username.
- Login returns generic errors for invalid credentials.
- Rate limit login and signup (edge + app-level counters in Redis).
- Password hashing uses a modern slow hash (bcrypt already present; argon2 may be introduced later if desired).

### 6.3 “Current user” and profile settings

- Provide a `/api/users/me` endpoint sufficient for React to render auth state.
- Provide an update endpoint for allowed profile fields (display name, avatar URL, bio).

### 6.4 Google sign-in

- Implement Authorization Code flow with strict redirect allowlist.
- Link external identity to a single local user record (existing Django model `OAuthAccount` is the intended canonical store).
- On success, create the same cookie-based session state as email/password login.

---

## 7) FastAPI ↔ Django Mirror Contract Strategy

### 7.1 Canonical data model

- Django models are canonical.
- FastAPI must not silently diverge in validation or semantics.

### 7.2 Mirror enforcement (gates)

- **Schema drift gate (DB)**: keep running `python manage.py schema_compat_check` during deploy (already implemented in `deploy.ps1`).
- **Contract gate (API)**:
  - Maintain an explicit OpenAPI contract under `specs/001-django-fastapi-react/contracts/openapi.yaml`.
  - FastAPI runtime OpenAPI (`/openapi.json` in non-production modes) must match the committed contract (tolerating ordering/metadata differences).
  - Add a CI/deploy-time check that diffs normalized OpenAPI schemas and fails on breaking drift.

---

## 8) Testing Strategy (unit → integration → deploy gates)

### 8.1 Unit tests

- Django: model constraints, migration behavior, auth-related helpers, audit-event creation
- FastAPI: auth endpoints, CSRF enforcement, error envelopes, rate limiting behavior
- React: protected routing, auth flows, settings updates, OAuth happy-path and cancel-path

### 8.2 Integration tests (Compose)

- Bring up stack with `local.docker.yml`.
- Verify:
  - health endpoints
  - migrations applied + `schema_compat_check` passes
  - signup/login/logout
  - CSRF rejection on missing token
  - internal-only services not exposed
  - celery ping + result flow works

### 8.3 Deploy-time gates

- `deploy.ps1 -AllTests` runs the post-deploy verification suite (`test.ps1`).
- Add/extend checks so the deploy report includes:
  - OpenAPI snapshot capture
  - auth guarded endpoint checks (401/403 without credentials)
  - explicit confirmation of staging-only ACME resolver

---

## 9) Deploy.ps1 Integration Points (must remain stable)

- Deploy/update must be idempotent and safe.
- Verification must always run and always capture artifacts.
- Artifact capture must redact secrets.
- Existing artifact contracts (e.g., `schema-compat-check.*`, `traefik-*.yml`, `api-health.*`, `celery-*.json`) remain stable to avoid breaking `test.ps1`.

---

## 10) Documentation Deliverables (repo location)

- `docs/stack-overview.md` (service inventory + topology)
- `docs/local-dev.md` (local compose usage)
- `docs/deploy.md` (deploy.ps1 usage, flags, artifacts)
- `docs/configuration.md` (env vars; update policy)
- `docs/security.md` (auth, CSRF, headers, allowlists)
- `docs/oauth.md` (Google sign-in flow)

## Complexity Tracking

No constitution violations are required for this feature; the stack is already multi-service and Compose-first.
