# Master Task List — Traefik + React + FastAPI + Django (Option 1)  
## FastAPI Option B: Traefik strips `/api` prefix before forwarding to FastAPI

**Goal (Option 1)**  
- **Django** owns schema + migrations + admin UI (guarded).  
- **FastAPI** is the public API runtime and talks to Postgres directly (NO dependency on Django).  
- **React** is the public frontend and calls API at `https://${WEBSITE_DOMAIN}/api/...` (but FastAPI itself serves routes without `/api` because Traefik strips it).  
- **Traefik** is the only public entry (ports 80/443 only).  
- **All services are isolated; no host ports** on api/django/postgres/redis/celery/pgadmin/nginx-static/flower (Traefik only).  
- **Staging-only ACME resolver** (no production issuance).

---

## Global Routing Contract (Updated)

### Public
- `https://${WEBSITE_DOMAIN}/` and `https://www.${WEBSITE_DOMAIN}/` → **React**
- `https://${WEBSITE_DOMAIN}/api/*` → **FastAPI** (Traefik strips `/api`, FastAPI receives `/...`)
- `https://${DJANGO_ADMIN_DNS_LABEL}.${WEBSITE_DOMAIN}/` → **Django Admin** (guarded)
- `https://${TRAEFIK_DNS_LABEL}.${WEBSITE_DOMAIN}/` → **Traefik dashboard** (guarded)
- `https://${PGADMIN_DNS_LABEL}.${WEBSITE_DOMAIN}/` → **pgAdmin** (guarded, optional)
- `https://${FLOWER_DNS_LABEL}.${WEBSITE_DOMAIN}/` → **Flower** (guarded, optional)
- `https://${WEBSITE_DOMAIN}/static/*` → **nginx-static** serving Django collected static (internal-only; routed through Traefik)

### Internal
- Postgres/Redis/Celery are internal-only and never exposed via host ports.

---

# Phase 0: Mandatory Baseline Review (New, required)

- [ ] T000 Inventory & sanity pass (before any changes)
  - Review and snapshot current:
    - `local.docker.yml` (ports, networks, volumes, labels)
    - `traefik/traefik.yml` and `traefik/dynamic.yml`
    - `scripts/deploy.ps1`, `scripts/test.ps1`, `scripts/validate-predeploy.ps1`
    - `api/app/main.py` routes + health endpoint paths
    - `django/project/settings.py` + `urls.py` + migration flow
    - `nginx/nginx-django-static.conf`
  - Confirm current FastAPI health endpoint:
    - internal: `/health` (target for container healthcheck)
    - external: `/api/health` (via Traefik stripPrefix)
  - Deliverable: `shared/docs/current_state.md` summarizing current behavior and risks.

---

# Phase 1: Setup (Shared Infrastructure) — UPDATED

- [X] T001 Add env keys to `.env` for FastAPI/Django
  - `FASTAPI_PYTHON_VERSION`, `FASTAPI_PORT`, `DJANGO_PYTHON_VERSION`, `DJANGO_PORT`, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`
  - **Update**: ensure these also exist and are correct in `.env.example` (see T040/T063)

- [X] T002 Update React config to use `REACT_APP_API_URL=https://${WEBSITE_DOMAIN}/api`
  - Verify usage in `react-app` fetches
  - **Update**: React continues to call `/api`, but FastAPI does NOT include `/api` in its route definitions (Traefik strips).

- [X] T003 [P] Document staging-only certificate policy in `specs/001-fastapi-django-deploy/quickstart.md`

---

# Phase 2: Foundational (Blocking Prerequisites) — UPDATED FOR OPTION 1 + OPTION B

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 [P] Compose integration: ensure `api` and `django` services build and start via deploy automation
  - Validate through `deploy.ps1` remote artifacts and service states (no local compose runs)

- [ ] T004.1 FIX `local.docker.yml` YAML correctness (New, blocking)
  - Fix indentation error: `react-app` has `volumes:` incorrectly nested under `labels:`
  - Remove irrelevant volume mount: `react-app` must NOT mount `traefik_acme`
  - Acceptance: compose parses cleanly and `docker compose config` succeeds.

- [ ] T004.2 Remove Option-2 coupling from FastAPI (New, blocking)
  - Remove `DJANGO_SERVICE_URL` from api env
  - Remove `depends_on: django` from `api`
  - Ensure API only depends on Postgres (and Redis if Celery enabled)
  - Acceptance: API boots without Django running.

- [X] T005 [P] Traefik routing: verify `/api/**` routes to `api` service
  - **Update**: Must also apply `stripPrefix(/api)` middleware so FastAPI receives `/...`
  - Files: `traefik/dynamic.yml`

- [ ] T005.1 Repair `traefik/dynamic.yml` (New, blocking)
  - Current dynamic.yml is corrupted/invalid:
    - middlewares appear under `entryPoints`
    - duplicated blocks
    - indentation errors
  - Replace with a clean configuration matching:
    - `/api/*` router → stripPrefix(`/api`) → `api:${FASTAPI_PORT}`
    - React router catches all else at lower priority
    - `/static/*` → nginx-static
    - Admin subdomain and/or `/admin` routed to Django admin with auth + allowlist
  - Acceptance: Traefik starts with no dynamic config errors and routers appear in artifacts.

- [ ] T005.2 Decide provider mode (New, blocking)
  - Your `traefik.yml` uses file provider; docker provider is commented.
  - Choose ONE:
    - (Recommended) Keep file provider and remove reliance on per-service Traefik labels
    - OR enable docker provider and move routing to labels
  - Acceptance: routing source of truth is unambiguous and documented.

- [ ] T006 Update API health endpoint behavior (Updated for Option B)
  - FastAPI must serve internal `/health` (no `/api` prefix)
  - Externally it must be reachable at `https://${WEBSITE_DOMAIN}/api/health` via Traefik stripPrefix
  - Files: `api/main.py`, `scripts/test.ps1`, `local.docker.yml` healthcheck
  - Acceptance: container healthcheck uses `/health`, edge check uses `/api/health`.

- [X] T007 Django internal route for FastAPI proxy example
  - **Update**: NOT required for Option 1; must be removed or locked down to internal-only.
  - Files: `django/project/urls.py`
  - Acceptance: No public Django API endpoints exist besides admin/static/health (if used).

- [X] T008 [P] Confirm no host ports on `api`, `django`, `postgres`
  - **Update**: also remove host ports on `nginx-static` (currently exposed at 8081), `pgadmin`, `redis`, `celery-*`, `flower`
  - File: `local.docker.yml`

- [X] T009 [P] Ensure staging cert resolver is used (no production issuance)
  - File: `traefik/traefik.yml` and router tls config

**Checkpoint**: Foundation ready — homepage and `/api/health` reachable; services healthy; Traefik config valid; no unintended host ports.

---

# Phase 3: User Story 1 — One-command cloud deploy (Priority: P1) — UPDATED

**Goal**: Single deploy command provisions/updates, verifies, and saves timestamped artifacts.

**Independent Test**: Homepage over HTTPS and `/api/health` OK; timestamped artifacts saved locally.

- [X] T010 Verify fail-fast behavior when DO credentials missing/invalid
  - File: `scripts/deploy.ps1`

- [X] T011 Confirm remote verification captures required artifacts
  - Files: `scripts/deploy.ps1`
  - Expected artifacts include:
    - `compose-ps.txt`, `traefik-env.txt`, `traefik-static.yml`, `traefik-dynamic.yml`, `traefik-logs.txt`
    - `curl-root.txt`, `curl-api.txt` (must hit `/api/health`)
    - template snapshots

- [X] T012 [P] Ensure timestamped mode writes to per-run subfolder
  - File: `scripts/deploy.ps1`

- [ ] T012.1 Add deploy artifact for migration output (New)
  - Capture:
    - `django-migrate.txt` (or equivalent) during deploy verification
  - Acceptance: migration output is stored per deploy run.

**Checkpoint**: Single deploy produces complete artifact set (including migrations output).

---

# Phase 4: User Story 2 — Update-only redeploy (Priority: P2) — UPDATED

- [X] T013 Ensure update-only flag is passed to orchestrator
  - File: `scripts/deploy.ps1` (`--update-only`)

- [ ] T014 Measure runtime comparison and document ≥30% improvement target
  - File: `specs/001-fastapi-django-deploy/quickstart.md`

---

# Phase 5: User Story 3 — Safe fallback when remote verify unavailable (Priority: P3)

- [X] T015 Validate IP discovery fallback (`Get-DropletIp`) and skip path
  - File: `scripts/deploy.ps1`

- [X] T016 Confirm warning message and local artifacts exist when remote verify skipped
  - File: `scripts/deploy.ps1`

---

# Phase N: Polish & Cross-Cutting Concerns — UPDATED

- [X] T017 [P] Enhance Traefik middlewares (security headers, rate limit) if needed
  - **Update**: ensure middlewares are attached correctly (not under entryPoints)
  - Files: `traefik/dynamic.yml`

- [X] T018 [P] Update `fastapi-django-extension.md` to reflect current integration specifics
  - **Update**: reflect Option 1 + FastAPI Option B stripPrefix.

- [X] T019 Add operator troubleshooting section to `quickstart.md`

- [X] T020 [P] Optional: add basic tests for API health and Django admin routing
  - **Update**: remove “Django internal proxy endpoint” test; replace with schema-compatibility test (see N004).

---

# Phase V: Validation — Ports, Routing, Requirements (Comprehensive) — UPDATED

## Ports & Exposure (verify via remote artifacts)
- [X] T021 Confirm Traefik is the only publicly exposed service (host ports `80` and `443`)
  - **Update**: remove `ports:` from `nginx-static` (currently violates this)

- [X] T022 Verify `react-app` serves on internal port `8080` and Traefik routes accordingly

- [X] T023 Verify `api` listens on `${FASTAPI_PORT}` and Traefik forwards to this port
  - **Update**: router must also strip `/api` prefix.

- [X] T024 Verify `django` listens on `${DJANGO_PORT}` but is not exposed via Traefik by default
  - **Update**: in this architecture it IS exposed for admin only (guarded), either via `admin.${WEBSITE_DOMAIN}` or `/admin`.
  - Acceptance: no public non-admin Django routes.

## Routing & Middlewares (verify via remote artifacts)
- [X] T025 Validate Traefik routers for frontend and API
  - Frontend: `frontend-react` `Host(${WEBSITE_DOMAIN})` → `react-app`
  - API: `api` `Host(${WEBSITE_DOMAIN}) && PathPrefix(/api)` → `api` **with stripPrefix**
  - Static: `/static` → nginx-static

- [X] T026 Confirm HTTPS redirect middleware for HTTP entrypoint
  - **Update**: centralize to one `http-catchall` router preferred.

- [X] T027 Confirm security headers middleware attached
  - **Update**: verify correct middleware attachment across routers.

- [X] T028 Ensure rate limiting middleware configured and attached to the API router

## Requirements & Environment
- [X] T029 Audit `api/requirements.txt` for necessary packages and remove unused ones
- [X] T030 Audit `django/requirements.txt` for necessary packages
- [X] T031 Verify `.env` includes all required keys and correct values
- [X] T032 Add notes in `quickstart.md` for environment keys and example values

---

# Constitution Compliance (Mandatory) — UPDATED

- [X] T040 Update `.env.example` with all required keys and keep in sync with `.env` usage across scripts and compose

- [X] T041 Define Docker Compose `healthcheck` for `traefik`, `react-app`, `api`, and `django`
  - **Update**:
    - FastAPI: container healthcheck must hit `http://localhost:${FASTAPI_PORT}/health` (internal)
    - Edge tests must hit `https://${WEBSITE_DOMAIN}/api/health`

- [X] T042 Make tests mandatory
  - **Update**: tests must include:
    - `/api/health` via edge (stripPrefix path)
    - Django admin routing (guarded)
    - Static routing (`/static/*`)
    - NO tests for Django internal proxy endpoints

- [X] T043 Verify staging-only certificates are used and no production issuance occurs

- [X] T044 Validate failure messaging and artifact persistence on common failures

---

# Phase 6: Celery + Redis (P2) — UPDATED (No change in concept, but ensure no host ports)

- [X] T046 Add Redis/Celery env keys to `.env.example` and document in quickstart
- [X] T047 [P] Validate no secrets leak into saved artifacts; scrub as needed in `deploy.ps1`
- [X] T048 Add `redis` service to `local.docker.yml` (no host ports)
- [X] T049 Add `celery-worker` service(s) consuming app image and env; depend on `redis`
- [X] T050 Optional: add `celery-beat` scheduler
- [X] T051 Define healthchecks for `redis`, `celery-worker`, and `celery-beat`
- [X] T052 Add `flower` service (disabled by default) and Traefik router guarded by basic auth + allowlist
- [X] T053 Create `scripts/update-flower-allowlist.ps1`
- [X] T054 Extend `traefik/dynamic.yml` with optional Flower router + middlewares; ensure absent when envs unset
- [X] T055 Extend `scripts/test.ps1` with `-CheckCelery` flag
- [X] T056 Wire `-CheckCelery` into `scripts/deploy.ps1` behind opt-in switch
- [X] T057 Update docs for Redis/Celery usage
- [X] T058 Cross-link to `docs/STACK.md`
- [X] T059 CI/test report includes celery checks when enabled
- [X] T060 No host ports opened for redis/celery/flower

---

# Phase 7: Full Stack Role Realignment — UPDATED FOR OPTION 1 + OPTION B

- [X] T061 Audit current Compose and Traefik configs for Node.js backend references
- [X] T062 Document endpoints/domains served by Django, FastAPI, React
- [X] T063 Define environment variables for Django, FastAPI, React (add to .env.example)
- [ ] T064 Update architecture diagrams and stack documentation
  - **Update**: diagrams must show Traefik stripPrefix `/api` → FastAPI routes.

## Compose
- [X] T065 Remove Node.js backend service from Compose
- [X] T066 Add Django service (internal; admin routed only)
- [X] T067 Add FastAPI service
- [X] T068 Ensure React service only serves frontend (port 8080)
- [X] T069 Update Traefik service volumes/config
- [ ] T070 Ensure all services are on the correct Docker network(s)
- [ ] T071 Remove any host port exposure except Traefik (80/443)
  - **Update**: remove `ports` from nginx-static (currently exposed)

## Traefik
- [ ] T072 Add router for Django admin (admin subdomain) → Django:8000
- [ ] T073 Add router for FastAPI (host + `/api`) → FastAPI:5001
  - **Update**: MUST include stripPrefix(`/api`) middleware (Option B)
- [ ] T074 Ensure React router only serves main domain and www, lower priority than /api and /static
- [ ] T075 Remove Node.js backend routers/services
- [ ] T076 Add/adjust middlewares as needed (security, rate limit)
- [ ] T077 Validate all routers and services in Traefik config

## Django
- [ ] T078 Create or migrate Django project
- [ ] T079 Configure settings.py (allowed hosts, DB, static/media, admin URL)
- [ ] T080 Add Dockerfile for Django (deps, collectstatic, migrations, gunicorn)
- [ ] T081 Add requirements.txt
- [ ] T082 Add entrypoint/migrate script
- [ ] T083 Add HTTP health endpoint (optional but recommended)

## FastAPI (Option B specific)
- [ ] T084 Create or migrate FastAPI project
- [ ] T085 Add Dockerfile for FastAPI
- [ ] T086 Add requirements.txt for FastAPI
- [ ] T087 Add entrypoint script if needed
- [ ] T088 Add internal `/health` endpoint (NOT `/api/health`)
  - Edge must still serve `/api/health` via Traefik stripPrefix.

## React
- [ ] T089 Ensure React only serves frontend assets
- [ ] T090 Remove any backend logic or API proxying from React
- [ ] T091 Build React for production and serve with nginx or similar

## DB & deps
- [ ] T092 Ensure Postgres is available and configured for Django and FastAPI
- [ ] T093 Ensure Redis is available if using Celery
- [ ] T094 Update env vars for DB/Redis/etc.

## Persistence
- [ ] T095 Map volumes for Django static/media
- [ ] T096 Map volumes for Traefik ACME and logs
- [ ] T097 Map volumes for Postgres data

## Healthchecks
- [ ] T098 Add healthchecks for Django, FastAPI, React, Postgres, Redis
  - **Update**: FastAPI healthcheck uses `/health` internal.

## Env vars
- [ ] T099 Set all required env vars for all services

## CI/CD & scripts
- [ ] T100 Update deploy scripts to build Django/FastAPI images
- [ ] T101 Update orchestration scripts to handle new services

## Docs
- [ ] T102 Update README and docs

## Testing
- [ ] T103 Add/adjust tests for Django/FastAPI/React
- [ ] T104 Ensure integration tests cover routing and boundaries
  - **Update**: include stripPrefix behavior.

## Security
- [ ] T105 Add/adjust Traefik middlewares
- [ ] T106 Ensure Django/FastAPI hardened

## DNS
- [ ] T107 Ensure DNS records point admin subdomain to Traefik
- [ ] T108 Ensure website and www point to Traefik

---

# NEW Option-1 + Option-B Critical Additions (Must Add)

- [ ] N001 Remove FastAPI→Django coupling
  - Delete `DJANGO_SERVICE_URL` usage in code and env.
  - Remove any proxy calls from FastAPI to Django.

- [ ] N002 Implement FastAPI DB layer (SQLAlchemy) mirroring Django schema
  - Create `api/app/db/session.py` and `api/app/db/models.py`
  - Ensure `__tablename__` matches Django table names (prefer explicit `db_table` in Django).

- [ ] N003 Add Traefik middleware `strip-api-prefix` and attach to API router
  - Middleware:
    - `stripPrefix` with `prefixes: [/api]`

- [ ] N004 Update tests to validate stripPrefix
  - `curl https://${WEBSITE_DOMAIN}/api/health` must reach FastAPI internal `/health`.

- [ ] N005 Fix dynamic.yml correctness and remove duplication
  - Replace corrupted config with clean YAML.

- [ ] N006 Remove `ports` from `nginx-static` and any other non-traefik service
  - Verify via `compose-ps.txt` artifacts.

- [ ] N007 Add “Schema compatibility” check post-migration
  - A lightweight check that required tables/columns exist (fails fast if drift).

- [ ] N008 Add migration logging to deploy artifacts
  - Capture `python manage.py migrate` output.

---
# Diff-Style Mini-Checklist — Apply Against Your Exact Files
**Scope**: `local.docker.yml`, `traefik.yml`, `dynamic.yml`  
**Target**: Option 1 (Django owns schema/migrations) + FastAPI Option B (Traefik strips `/api`)  
**Rule**: Only Traefik exposes host ports 80/443. Everything else is internal.

---

## A) `local.docker.yml` — Required Diffs

### A1 — Fix YAML correctness (BLOCKER)
- [ ] **A1.1** Fix indentation: `react-app` has `volumes:` nested under `labels:` (invalid YAML / wrong structure).
  - **Change**: Move `volumes:` (if any) to the service root level at the same indentation as `labels:`.
  - **Acceptance**: `docker compose -f local.docker.yml config` succeeds.

---

### A2 — React service cleanup (seamless + least surprise)
- [ ] **A2.1** Remove accidental Traefik ACME volume from `react-app`
  - You currently have:
    - `volumes: - traefik_acme:/etc/traefik/acme`
  - **Change**: delete it from `react-app` entirely.
  - **Why**: React does not need ACME storage; reduces risk and confusion.

- [ ] **A2.2** Decide Traefik provider mode and remove conflicting labels
  - **Current**: Traefik `docker` provider is commented in `traefik.yml` but `react-app` has many Traefik labels.
  - **Change (recommended)**: if keeping **file provider**, remove **routing labels** from `react-app` (and other services) to avoid drift and confusion.
  - **Acceptance**: routing is only in `dynamic.yml` and documented.

---

### A3 — FastAPI service changes for Option 1 + Option B (BLOCKER)
- [ ] **A3.1** Remove FastAPI → Django coupling (Option 1)
  - **Delete** from `api.environment`:
    - `DJANGO_SERVICE_URL=http://django:${DJANGO_PORT}`
  - **Delete** from `api.depends_on`:
    - the `django:` dependency
  - **Why**: Option 1 means FastAPI reads/writes DB directly; Django is not a data service.

- [ ] **A3.2** Align FastAPI healthcheck to internal `/health` (Option B)
  - **Current**:
    - healthcheck hits `http://localhost:${FASTAPI_PORT}/health` ✅ (good baseline)
  - **Verify**:
    - FastAPI actually exposes `/health` internally (NOT `/api/health`)
  - **Edge** will be `/api/health` via Traefik stripPrefix.

- [ ] **A3.3** Ensure `PORT=${FASTAPI_PORT}` matches FastAPI server bind
  - Verify FastAPI container listens on `${FASTAPI_PORT}` inside container.
  - If your app binds to 8000 or 5001 fixed, ensure env wiring matches.

---

### A4 — Django service changes (seamless admin + migrations)
- [ ] **A4.1** Ensure Django is “admin-only public surface”
  - No Traefik labels needed if using file provider.
  - Ensure Django starts gunicorn/uvicorn on `${DJANGO_PORT}`.
- [ ] **A4.2** Add a real HTTP health endpoint (recommended)
  - Current healthcheck is `python manage.py check --deploy` (config check, not runtime)
  - Prefer runtime health:
    - `curl -fsS http://localhost:${DJANGO_PORT}/health`
  - If you keep `check --deploy`, add a separate runtime smoke in `scripts/test.ps1`.

---

### A5 — Remove forbidden host ports (BLOCKER)
- [ ] **A5.1** Remove host port mapping from `nginx-static`
  - **Current**:
    ```yml
    ports:
      - "8081:8081"
    ```
  - **Change**: delete `ports:` entirely.
  - **Why**: Traefik should route to `nginx-static` internally; only Traefik exposes host ports.

- [ ] **A5.2** Confirm no other services have `ports:` besides Traefik
  - Verify `postgres`, `pgadmin`, `redis`, `celery-*`, `flower` have no host ports.
  - **Acceptance**: `compose-ps.txt` shows only Traefik published ports.

---

### A6 — Traefik service host ports sanity
- [ ] **A6.1** Ensure Traefik publishes exactly host 80 and 443
  - Current:
    - `${TRAEFIK_HOST_PORT}:${TRAEFIK_PORT}`
    - `443:443`
  - **Verify**:
    - `${TRAEFIK_HOST_PORT}` must be `80`
    - `${TRAEFIK_PORT}` must be `80` inside container (common)
  - If you’re intentionally using non-80, document it and ensure redirects/ACME expectations match.

---

## B) `traefik.yml` — Provider Mode + Entrypoints

### B1 — Choose routing source of truth (BLOCKER)
- [ ] **B1.1** Decide and enforce provider strategy:
  - **Recommended** (given your setup): **File provider only**
    - Keep `providers.file` enabled
    - Keep `providers.docker` disabled
    - Remove reliance on service labels for routing
  - **Alternative**: Docker provider only
    - Enable docker provider
    - Move all routing into labels
    - Remove file provider routing

- [ ] **B1.2** Ensure Traefik actually has `dynamic.yml` at:
  - `/etc/traefik/dynamic/dynamic.yml`
  - Your `traefik.yml` references:
    ```yml
    file:
      filename: /etc/traefik/dynamic/dynamic.yml
    ```
  - **Verify** the Traefik Docker image:
    - either bakes it into the image at build time
    - or generates it at container start
  - **Acceptance**: `traefik-dynamic.yml` artifact matches expected content and Traefik logs show no file-provider errors.

---

### B2 — EntryPoints correctness
- [ ] **B2.1** Confirm entrypoints:
  - `web` is bound to `:${TRAEFIK_PORT}` and redirects to `websecure`
  - `websecure` is bound to `:443`
- [ ] **B2.2** Confirm TLS resolver is staging-only (`le-staging`) everywhere
  - Ensure no accidental prod resolver exists.

---

## C) `dynamic.yml` — Replace Corrupted Config with Correct Option B Routing (BLOCKER)

### C1 — Replace entire file (recommended)
- [ ] **C1.1** Delete current `dynamic.yml` contents (it is malformed)
  - Issues include:
    - middleware names under `entryPoints`
    - broken indentation
    - duplicated middleware blocks
    - routers missing names or mixed content

- [ ] **C1.2** Replace with a clean config including stripPrefix middleware
  - Must include:
    - `http-catchall` → redirect to https
    - `api` router: Host(`${WEBSITE_DOMAIN}`) && PathPrefix(`/api`)
      - middlewares: `strip-api-prefix`, `security-headers`, `rate-limit`, `retry`
      - service: `api`
    - `strip-api-prefix` middleware: `stripPrefix` with `prefixes: [/api]`
    - React router with lower priority
    - `/static` router to `django-static`
    - admin subdomain router to `django-admin` guarded
  - **Acceptance**: Traefik logs show routers loaded; `curl https://${WEBSITE_DOMAIN}/api/health` returns FastAPI `/health` result.

---

### C2 — Explicit required items for Option B
- [ ] **C2.1** Add `strip-api-prefix` middleware
  - Example:
    ```yml
    strip-api-prefix:
      stripPrefix:
        prefixes:
          - /api
    ```
- [ ] **C2.2** Attach `strip-api-prefix` to the API router
- [ ] **C2.3** Ensure router priorities:
  - `/api` router priority > frontend router priority
  - `/static` and `/admin` priority > frontend router priority

---

## D) Sanity Verification Tasks (post-change, artifact-driven)

### D1 — Local validation (before deploy)
- [ ] **D1.1** `docker compose -f local.docker.yml config` succeeds
- [ ] **D1.2** No service except Traefik has host `ports:`
- [ ] **D1.3** Traefik config loads without errors:
  - dynamic file exists and is valid YAML

### D2 — Remote artifact validation (after deploy)
- [ ] **D2.1** `curl-root.txt` returns React (200)
- [ ] **D2.2** `curl-api.txt` hits `https://${WEBSITE_DOMAIN}/api/health` and returns FastAPI JSON
- [ ] **D2.3** `traefik-dynamic.yml` artifact shows:
  - API router includes `strip-api-prefix`
- [ ] **D2.4** `compose-ps.txt` shows only Traefik publishes host ports
- [ ] **D2.5** Admin route is guarded:
  - requires auth + allowlist (as configured)

---

## E) Code Alignment Tasks (Option B, minimal but required)

- [ ] **E1** FastAPI must expose internal `/health` (not `/api/health`)
  - Update `api/app/main.py` accordingly.
  - Update any internal clients/tests that reference the old path.

- [ ] **E2** React calls `REACT_APP_API_URL=https://${WEBSITE_DOMAIN}/api`
  - Ensure no double-prefix (`/api/api`) in fetch calls.

- [ ] **E3** Remove any FastAPI code that calls Django endpoints (Option 1)
  - Ensure DB access is direct (SQLAlchemy or equivalent).

---


# Final Acceptance Criteria (Updated)

- ✅ `https://${WEBSITE_DOMAIN}/` loads React; deep-link refresh works  
- ✅ `https://${WEBSITE_DOMAIN}/api/health` returns 200 and JSON  
  - FastAPI internal route is `/health` (Option B)  
- ✅ Django admin available only on `https://${DJANGO_ADMIN_DNS_LABEL}.${WEBSITE_DOMAIN}/admin/` (and optionally `${WEBSITE_DOMAIN}/admin`) and guarded  
- ✅ `/static/*` served via Traefik → nginx-static, with no host port exposure  
- ✅ Only Traefik binds host ports 80/443  
- ✅ FastAPI has NO dependency on Django; both talk directly to Postgres  
- ✅ Deploy artifacts prove router rules, middlewares, and staging cert resolver usage  
- ✅ Tests cover edge routing + stripPrefix + headers + port exposure + schema check  

---
