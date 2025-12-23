# Master Task List — Traefik + React + FastAPI + Django (Option 1)
## FastAPI Option B: Traefik strips `/api` prefix before forwarding to FastAPI

**Goal (Option 1)**  
- **Django** owns schema + migrations + admin UI (guarded).  
- **FastAPI** is the public API runtime and talks to Postgres directly (**NO dependency on Django**).  
- **React** is the public frontend and calls API at `https://${WEBSITE_DOMAIN}/api/...` (**FastAPI itself serves routes without `/api`** because Traefik strips it).  
- **Traefik** is the only public entry (**host ports 80/443 only**).  
- **All services are isolated; no host ports** on api/django/postgres/redis/celery/pgadmin/nginx-static/flower/nginx (Traefik only).  
- **Staging-only ACME resolver** (no production issuance).

---

## Global Routing Contract (Authoritative)

### Public
- `https://${WEBSITE_DOMAIN}/` and `https://www.${WEBSITE_DOMAIN}/` → **React** (`react-app:8080`)
- `https://${WEBSITE_DOMAIN}/api/*` → **FastAPI** (`api:${FASTAPI_PORT}`; Traefik strips `/api`)
- `https://${DJANGO_ADMIN_DNS_LABEL}.${WEBSITE_DOMAIN}/` → **Django Admin** (`django:${DJANGO_PORT}`; guarded)
- `https://${TRAEFIK_DNS_LABEL}.${WEBSITE_DOMAIN}/` → **Traefik dashboard** (`api@internal`; guarded)
- `https://${PGADMIN_DNS_LABEL}.${WEBSITE_DOMAIN}/` → **pgAdmin** (`pgadmin:${PGADMIN_PORT}`; guarded, optional)
- `https://${FLOWER_DNS_LABEL}.${WEBSITE_DOMAIN}/` → **Flower** (`flower:5555`; guarded, optional)
- `https://${WEBSITE_DOMAIN}/static/*` → **nginx-static** (`nginx-static:8081`) serving Django collected static

### Internal
- Postgres/Redis/Celery are internal-only and never exposed via host ports.

---


# Phase 0: Mandatory Baseline Review (Required)

- [X] T000 Inventory & sanity pass (before any changes)
  - Review and snapshot current:
    - `local.docker.yml` (ports, networks, volumes, labels)
    - `traefik/traefik.yml` and `traefik/dynamic.yml`
    - `digital_ocean/scripts/powershell/deploy.ps1`, `digital_ocean/scripts/powershell/test.ps1`, `digital_ocean/scripts/powershell/validate-predeploy.ps1`
    - `nginx/nginx.conf` and `nginx/nginx-django-static.conf`
    - `backend/**` (Node) **for deprecation plan**
    - `digital_ocean/**` (deploy orchestration and docs)
    - `.github/workflows/**` and root `package.json`
  - Confirm **current** API implementation (Node) and its routing rules.
  - Confirm current FastAPI health endpoint plan:
    - internal: `/health` (container healthcheck target)
    - external: `/api/health` (via Traefik stripPrefix)
  - Deliverable: `shared/docs/current_state.md` summarizing current behavior, drift risks, and what will change.

---

# Phase 1: Setup (Shared Infrastructure)

- [X] T001 Update `.env.example` and `.env` to fully cover the stack (no missing keys)
  - FastAPI:
    - `FASTAPI_PYTHON_VERSION`, `FASTAPI_PORT`, `JWT_SECRET`, `JWT_EXPIRE`
  - Django:
    - `DJANGO_PYTHON_VERSION`, `DJANGO_PORT`, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`
    - Optional bootstrap: `DJANGO_SUPERUSER_NAME`, `DJANGO_SUPERUSER_EMAIL`, `DJANGO_SUPERUSER_PASSWORD`
  - Traefik:
    - `TRAEFIK_LOG_LEVEL`, `TRAEFIK_PORT`, `TRAEFIK_API_PORT`, `TRAEFIK_API_ENTRYPOINT`, `TRAEFIK_CERT_EMAIL`
    - `TRAEFIK_DNS_LABEL`, `TRAEFIK_DASH_BASIC_USERS`
  - Public subdomains:
    - `DJANGO_ADMIN_DNS_LABEL`, `DJANGO_ADMIN_ALLOWLIST`
    - `PGADMIN_DNS_LABEL`, `PGADMIN_ALLOWLIST`
    - `FLOWER_DNS_LABEL`, `FLOWER_ALLOWLIST`, `FLOWER_BASIC_USERS`
  - DB:
    - `POSTGRES_VERSION`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_PORT`
  - React:
    - `REACT_APP_NODE_VERSION`, `REACT_APP_API_URL=https://${WEBSITE_DOMAIN}/api`
  - Acceptance:
    - `digital_ocean/scripts/powershell/validate-predeploy.ps1` can validate required vars (see T037).
    - `.env.example` is the contract; `.env` matches in deploy environments.

- [X] T002 Update React to use `REACT_APP_API_URL=https://${WEBSITE_DOMAIN}/api`
  - Verify there is no double prefix (`/api/api`) in any API client.
  - Touch files:
    - `react-app/**` (API client code)
    - `react-app/.Dockerfile` (build args)
    - `local.docker.yml` (build args/env for react-app)

- [X] T003 Document staging-only certificate policy
  - Ensure docs explicitly state staging ACME only, no production issuance.
  - Touch files:
    - `specs/**/quickstart.md` (where applicable)
    - `README.md` / `quickstart.md`

---

# Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 Compose validation must pass (BLOCKER)
  - Fix YAML correctness errors in `local.docker.yml`
    - Common issue observed previously: `volumes:` accidentally nested under `labels:` (invalid)
  - Add/keep a script gate:
    - `docker compose -f local.docker.yml config` must succeed
  - Acceptance: compose parses cleanly.

- [X] T004.1 Remove routing split-brain (BLOCKER)
  - Decide provider mode **once**:
    - **Recommended:** File provider only (routing in `traefik/dynamic.yml`)
  - If file provider:
    - remove Traefik routing labels from `react-app` (and any other services)
  - Touch files:
    - `traefik/traefik.yml`
    - `traefik/dynamic.yml`
    - `local.docker.yml`
  - Acceptance: routing source of truth is unambiguous and documented.

- [X] T004.2 Remove Option-2 coupling from FastAPI (BLOCKER)
  - Remove any env/config referencing `DJANGO_SERVICE_URL`
  - Remove `depends_on: django` from `api`
  - Ensure API depends only on Postgres (and Redis if Celery enabled)
  - Touch files:
    - `local.docker.yml`
    - `api/**` (config)
  - Acceptance: API boots and passes health without Django running.

- [X] T005 Repair and replace `traefik/dynamic.yml` (BLOCKER)
  - Current dynamic.yml must be valid YAML and must not place `middlewares` under `entryPoints`.
  - Must include:
    - `/api/*` router → `stripPrefix(/api)` → `api:${FASTAPI_PORT}`
    - React router catch-all (lower priority than /api and /static)
    - `/static/*` → nginx-static
    - Admin subdomain router → Django with auth + allowlist
    - Traefik dashboard router with auth (and optional allowlist)
  - Acceptance:
    - Traefik boots with zero dynamic config errors.
    - Routers appear in Traefik dashboard (or remote artifacts).

- [X] T006 Health endpoints aligned to Option B (BLOCKER)
  - FastAPI:
    - internal: `GET /health` (container healthcheck)
    - external: `GET /api/health` (Traefik stripPrefix)
  - Django:
    - add `GET /health` (recommended) OR keep manage.py check and add runtime smoke test
  - Touch files:
    - `api/app/main.py` (or equivalent)
    - `django/project/urls.py` (+ a view)
    - `local.docker.yml` healthchecks
    - `digital_ocean/scripts/powershell/test.ps1` and deploy curls

- [X] T007 Remove forbidden host ports (BLOCKER)
  - Only Traefik may publish host ports 80/443.
  - Remove `ports:` from:
    - `nginx-static` (common accidental exposure)
    - `pgadmin`
    - `postgres`
    - `api`
    - `django`
    - `redis/celery/flower` (if enabled)
  - Acceptance:
    - `docker compose ps` shows only Traefik published ports.

- [X] T008 Ensure staging resolver is used everywhere (BLOCKER)
  - `traefik/traefik.yml`: resolver `le-staging` only
  - `traefik/dynamic.yml`: routers use `certResolver: le-staging`
  - Acceptance:
    - remote artifacts show `le-staging` and not production endpoints.

**Checkpoint**: Foundation ready — homepage and `/api/health` reachable; services healthy; Traefik config valid; no unintended host ports.

---

# Phase 3: User Story 1 — One-command cloud deploy (P1)

**Goal**: Single deploy command provisions/updates, verifies, and saves timestamped artifacts.

- [X] T010 Verify fail-fast behavior when DO credentials missing/invalid
  - Touch file: `digital_ocean/scripts/powershell/deploy.ps1`

- [X] T011 Confirm remote verification captures required artifacts (UPDATED)
  - Touch file: `digital_ocean/scripts/powershell/deploy.ps1`
  - Must capture:
    - `compose-ps.txt`, `traefik-env.txt`, `traefik-static.yml`, `traefik-dynamic.yml`, `traefik-logs.txt`
    - `curl-root.txt`, `curl-api-health.txt` (must hit `/api/health`)
    - If admin enabled: `curl-admin-head.txt` (expect 401/403)
    - template snapshots (if generated)

- [X] T012 Ensure timestamped mode writes to per-run subfolder
  - Touch file: `digital_ocean/scripts/powershell/deploy.ps1`

- [X] T012.1 Add deploy artifact for migration output (New)
  - Capture:
    - `django-migrate.txt` (stdout/stderr from `python manage.py migrate`)
  - Touch files:
    - `digital_ocean/scripts/powershell/deploy.ps1`
    - `django/entrypoint.sh` (if migrations run there)
  - Acceptance: migration output stored per deploy run.

**Checkpoint**: Single deploy produces complete artifact set (including migrations output and `/api/health` verification).

---

# Phase 4: User Story 2 — Update-only redeploy (P2)

- [X] T013 Ensure update-only flag is passed to orchestrator
  - Touch file: `digital_ocean/scripts/powershell/deploy.ps1` (`--update-only`)

- [X] T014 Measure runtime comparison and document ≥30% improvement target
  - Touch file: `specs/**/quickstart.md` (where you keep deploy notes)

---

# Phase 5: User Story 3 — Safe fallback when remote verify unavailable (P3)

- [X] T015 Validate IP discovery fallback (`Get-DropletIp`) and skip path
  - Touch file: `digital_ocean/scripts/powershell/deploy.ps1`

- [X] T016 Confirm warning message and local artifacts exist when remote verify skipped
  - Touch file: `digital_ocean/scripts/powershell/deploy.ps1`

---

# Phase N: Polish & Cross-Cutting Concerns

- [X] T017 Ensure Traefik middlewares attached correctly everywhere
  - Verify no middleware under entryPoints
  - Touch file: `traefik/dynamic.yml`

- [X] T018 Update docs to reflect Option 1 + Option B
  - Touch files:
    - `fastapi-django-extension.md`
    - `README.md`
    - `quickstart.md`

- [X] T019 Operator troubleshooting section
  - Symptoms  cause  fix (routing, certs, healthchecks, allowlists)
  - Touch file: `quickstart.md`

- [X] T020 Add basic tests (smoke)
  - Replace any “Django proxy endpoint” tests with:
    - schema compatibility check (see N007)
  - Touch files:
    - `digital_ocean/scripts/powershell/test.ps1`
    - `scripts/test.sh` (if used)

---

# Phase V: Validation — Ports, Routing, Requirements (Comprehensive)

## Ports & Exposure
- [X] T021 Confirm Traefik is the only publicly exposed service (80/443)
  - Verify `nginx-static` has no `ports:` mapping
  - Evidence: `compose-ps.txt` artifact

- [X] T022 Verify React internal port 8080 and routing is correct
  - Evidence: `traefik-dynamic.yml` service `frontend-react` points to `react-app:8080`

- [X] T023 Verify API internal port matches `${FASTAPI_PORT}`
  - Evidence: `curl-api-health.txt` success + `traefik-dynamic.yml` service url

- [X] T024 Verify Django is exposed only for admin, not as general API
  - Evidence:
    - Only admin routers exist for Django host/path
    - No other Django routers in dynamic config

## Routing & Middlewares
- [X] T025 Validate routers:
  - Frontend: Host(domain|www) → react
  - API: Host(domain) && PathPrefix(/api) → api **with stripPrefix**
  - Static: /static → nginx-static
  - Admin: admin subdomain → django with auth+allowlist

- [X] T026 Confirm HTTPS redirect is correct (prefer single http-catchall)
  - Evidence: `curl -I http://domain` shows Location https://...

- [X] T027 Confirm security headers middleware present
  - Evidence: `curl -I https://domain` contains HSTS, X-Content-Type-Options, etc.

- [X] T028 Ensure rate limiting middleware on API router
  - Evidence: `traefik-dynamic.yml` middleware attached

## Requirements & Environment
- [X] T029 Audit `api/requirements.txt` for only used deps
- [X] T030 Audit `django/requirements.txt`
- [X] T031 `.env` keys complete and used consistently in:
  - compose
  - scripts
  - templates
- [X] T032 Document env keys and example values
  - Touch: `quickstart.md`, `.env.example`

---

# Constitution Compliance (Mandatory)

- [X] T040 Keep `.env.example` in sync with actual usage
  - Add new keys as they are introduced in scripts/compose/traefik

- [X] T041 Healthchecks must reflect Option B behavior
  - FastAPI container: `/health`
  - Edge test: `/api/health`

- [X] T042 Tests mandatory
  - Include:
    - `/api/health` via edge
    - Admin routing guarded (expects 401/403)
    - Static routing `/static/*`
    - Port exposure scan

- [X] T043 Staging-only certs (no production)
  - Validate resolver is `le-staging` everywhere

- [X] T044 Failures preserve artifacts
  - Missing creds, SSH blocked, IP discovery failure, etc.

---

# Phase 6: Celery + Redis (P2)

- [X] T046 Add Redis/Celery env keys to `.env.example` and docs
- [X] T047 Scrub secrets from artifacts (deploy/test scripts)
- [X] T048 Add `redis` service (no host ports) and healthcheck
- [X] T049 Add `celery-worker` and optional `celery-beat` (no host ports)
- [X] T051 Healthchecks for redis/celery
- [X] T052 Optional Flower (profile; guarded; no host ports)
- [X] T055 Extend tests to validate celery/flower only when enabled

---

# Phase 7: Repo-wide Seamless Deploy + Logging Updates (New, required)

This phase is the “make it seamless” sweep across scripts, CI, DO orchestrators, and docs so nothing still assumes the Node backend.

- [X] T070 Remove/retire Node backend references everywhere (repo sweep)
  - Replace “backend” runtime assumptions with “api” (FastAPI)
  - Touch files (minimum):
    - `scripts/**` (deploy/test/start/log/status/health/traefik-check/sync-env)
    - `digital_ocean/**` (orchestrators + docs)
    - `.github/workflows/**`
    - root `package.json`
    - `README.md`, `project_overview.md`, `quickstart.md`
  - Acceptance:
    - No script tries to build/run/curl `backend` service.

- [X] T071 Update deploy logging and artifact capture for new services
  - Add explicit sections to artifacts:
    - FastAPI: `curl-api-health.txt`
    - Django: `django-migrate.txt` + optional `django-check-deploy.txt`
    - Traefik: `traefik-logs.txt` + `traefik-dynamic.yml` copy
    - Port exposure report: `published-ports.txt`
  - Touch file: `digital_ocean/scripts/powershell/deploy.ps1`

- [X] T072 Update log check scripts to include api/django
  - Ensure:
    - `scripts/logs.sh` can tail `api`, `django`, `traefik`, `react-app`
    - `scripts/status.sh` prints service health
  - Touch files: `scripts/logs.sh`, `scripts/status.sh`

- [X] T073 Update CI workflow(s) to stop testing Node backend
  - Replace with Python tests (if present) or remove backend steps.
  - Touch files:
    - `.github/workflows/**`
    - root `package.json`

---

# NEW Option-1 + Option-B Critical Additions (Must Add)

- [X] N001 Remove FastAPI→Django coupling (code + env)
  - Delete any `DJANGO_SERVICE_URL` usage
  - Remove any FastAPI code that calls Django endpoints

- [X] N002 Implement FastAPI DB layer mirroring Django schema (Option 1)
  - Ensure table names match Django migrations (use explicit `db_table` in Django where needed)
  - Add a minimal schema drift check (see N007)

- [X] N003 Add Traefik middleware `strip-api-prefix` and attach to API router
  - Middleware: `stripPrefix` with `prefixes: [/api]`

- [X] N004 Update tests to validate stripPrefix end-to-end
  - `curl https://${WEBSITE_DOMAIN}/api/health` must reach FastAPI internal `/health`

- [X] N005 Replace corrupted `dynamic.yml` with clean YAML (no duplication, no indentation issues)

- [X] N006 Remove `ports` from `nginx-static` and any other non-traefik service
  - Verify with compose output and deploy artifacts

- [X] N007 Add “Schema compatibility” check post-migration
  - A lightweight check that required tables/columns exist (fails fast on drift)
  - Run in deploy verification and save to artifacts

- [X] N008 Add migration logging to deploy artifacts
  - Capture `python manage.py migrate` output and store per run

---

# Diff-Style Mini-Checklist — Apply Against Your Exact Files

**Scope**: `local.docker.yml`, `traefik/traefik.yml`, `traefik/dynamic.yml`  
**Target**: Option 1 + FastAPI Option B stripPrefix  
**Rule**: Only Traefik exposes host ports 80/443.

## A) `local.docker.yml`
- [X] A1 Fix YAML correctness (BLOCKER)
- [X] A2 Remove accidental Traefik ACME volume from react (if present)
- [X] A3 Remove FastAPI→Django coupling (env + depends_on)
- [X] A4 Align FastAPI healthcheck to internal `/health`
- [X] A5 Add Django runtime health endpoint and align healthcheck
- [X] A6 Remove host ports from all services except Traefik (BLOCKER)
- [X] A7 Ensure Traefik publishes only 80/443

## B) `traefik/traefik.yml`
- [X] B1 Choose provider mode (file provider recommended) (BLOCKER)
- [X] B2 Ensure dynamic file exists at `/etc/traefik/dynamic/dynamic.yml`
- [X] B3 Ensure entrypoints and `le-staging` resolver configured correctly

## C) `traefik/dynamic.yml`
- [X] C1 Replace corrupted config (BLOCKER)
- [X] C2 Add `strip-api-prefix` and attach to API router
- [X] C3 Ensure router priorities: `/api`, `/static`, `/admin` > frontend
- [X] C4 Ensure admin + dashboard guarded by auth/allowlist
- [X] C5 Ensure pgadmin/flower routers guarded (if enabled)

## D) Artifact-driven verification
- [X] D1 `curl-root.txt` returns 200
- [X] D2 `curl-api-health.txt` hits `/api/health` and returns FastAPI JSON
- [X] D3 `traefik-dynamic.yml` artifact shows stripPrefix attached
- [X] D4 `compose-ps.txt` shows only Traefik published ports
- [X] D5 admin/dashboard are blocked from non-allowlisted IPs

---

# Final Acceptance Criteria

- [X] `https://${WEBSITE_DOMAIN}/` loads React; deep-link refresh works  
- [X] `https://${WEBSITE_DOMAIN}/api/health` returns 200 JSON  
  - FastAPI internal route is `/health` (Option B)  

- [X] Django admin available only on `https://${DJANGO_ADMIN_DNS_LABEL}.${WEBSITE_DOMAIN}/admin/` (and optional `${WEBSITE_DOMAIN}/admin`) and guarded  
- [X] `/static/*` served via Traefik → nginx-static, with **no host port exposure**  
- [X] **Only Traefik** binds host ports 80/443  
- [X] FastAPI has **NO dependency on Django**; both talk directly to Postgres  
- [X] Deploy artifacts prove router rules, middlewares, and staging cert resolver usage  
- [X] Tests cover edge routing + stripPrefix + headers + port exposure + schema check  

---
