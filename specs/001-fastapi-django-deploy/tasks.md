# Tasks: FastAPI + Django Automated Deployment

**Input**: Design documents from `/specs/001-fastapi-django-deploy/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Phase 1: Setup (Shared Infrastructure)

- [ ] T001 Add env keys to `.env` for FastAPI/Django
  - `FASTAPI_PYTHON_VERSION`, `FASTAPI_PORT`, `DJANGO_PYTHON_VERSION`, `DJANGO_PORT`, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`
- [ ] T002 Update React config to use `REACT_APP_API_URL=https://${WEBSITE_DOMAIN}/api`
  - Verify usage in `react-app` fetches
- [ ] T003 [P] Document staging-only certificate policy in `specs/001-fastapi-django-deploy/quickstart.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 [P] Compose integration: ensure `api` and `django` services build and start
  - Files: `local.docker.yml`, `api/.Dockerfile`, `django/.Dockerfile`
- [ ] T005 [P] Traefik routing: verify `/api/**` routes to `api` service
  - Labels in `local.docker.yml`
- [ ] T006 API health endpoint reachable via edge
  - Files: `api/main.py` (`/api/health`)
- [ ] T007 Django internal route for FastAPI proxy example
  - Files: `django/project/urls.py` (`internal/users/me`)
- [ ] T008 [P] Confirm no host ports on `api`, `django`, `postgres`
  - File: `local.docker.yml`
- [ ] T009 [P] Ensure staging cert resolver is used (no production issuance)
  - File: `local.docker.yml` labels

**Checkpoint**: Foundation ready — homepage and `/api/health` reachable; services healthy.

---

## Phase 3: User Story 1 — One-command cloud deploy (Priority: P1)

**Goal**: Run single deploy command to provision/update, verify, and save timestamped artifacts.

**Independent Test**: Homepage over HTTPS and `/api/health` OK; timestamped artifacts saved locally.

### Implementation

- [ ] T010 Verify fail-fast behavior when DO credentials missing/invalid
  - File: `scripts/deploy.ps1` (pre-cloud action check)
- [ ] T011 Confirm remote verification captures required artifacts
  - Files: `scripts/deploy.ps1` (scp outputs under `local_run_logs/<timestamp>/`)
  - Expected: `compose-ps.txt`, `traefik-env.txt`, `traefik-static.yml`, `traefik-dynamic.yml`, `traefik-ls.txt`, `traefik-logs.txt`, `curl-root.txt`, `curl-api.txt`, template snapshots
- [ ] T012 [P] Ensure timestamped mode writes to per-run subfolder
  - File: `scripts/deploy.ps1` (`-Timestamped` behavior)

**Checkpoint**: Single deploy produces complete artifact set.

---

## Phase 4: User Story 2 — Update-only redeploy (Priority: P2)

**Goal**: Faster redeploy without full rebuild; preserve data and produce artifact set.

**Independent Test**: Reduced runtime vs full deploy; complete artifacts present.

### Implementation

- [ ] T013 Ensure update-only flag is passed to orchestrator
  - File: `scripts/deploy.ps1` (`--update-only`)
- [ ] T014 Measure runtime comparison and document ≥30% improvement target
  - File: `specs/001-fastapi-django-deploy/quickstart.md` (notes/results)

**Checkpoint**: Update-only consistently faster with full artifacts.

---

## Phase 5: User Story 3 — Safe fallback when remote verify unavailable (Priority: P3)

**Goal**: Complete local steps and warn clearly when remote verification is skipped; still save logs.

**Independent Test**: Missing IP/SSH → local completion with warning + partial artifacts.

### Implementation

- [ ] T015 Validate IP discovery fallback (`Get-DropletIp`) and skip path
  - File: `scripts/deploy.ps1`
- [ ] T016 Confirm warning message and local artifacts exist when remote verify skipped
  - File: `scripts/deploy.ps1`

**Checkpoint**: Fallback path produces useful artifacts and guidance.

---

## Phase N: Polish & Cross-Cutting Concerns

- [ ] T017 [P] Enhance Traefik middlewares (security headers, rate limit) if needed
  - Files: `local.docker.yml`, `traefik/dynamic.yml`
- [ ] T018 [P] Update `fastapi-django-extension.md` to reflect current integration specifics
- [ ] T019 Add operator troubleshooting section to `quickstart.md`
- [ ] T020 [P] Optional: add basic tests for API health and Django internal endpoint

---

## Phase V: Validation — Ports, Routing, Requirements (Comprehensive)

**Goal**: Ensure all services, ports, routing rules, and package requirements are correct and consistent across files.

### Ports & Exposure
- [ ] T021 Confirm Traefik is the only publicly exposed service (host ports `80` and `443`)
  - File: `local.docker.yml` (`traefik` `ports:`); ensure `api`, `django`, `postgres` have no `ports:`
- [ ] T022 Verify `react-app` serves on internal port `8080` and Traefik routes accordingly
  - File: `local.docker.yml` labels; ensure service port `8080`
- [ ] T023 Verify `api` listens on `${FASTAPI_PORT}` and Traefik forwards to this port
  - File: `local.docker.yml` labels `loadbalancer.server.port=${FASTAPI_PORT}`; env `PORT=${FASTAPI_PORT}`
- [ ] T024 Verify `django` listens on `${DJANGO_PORT}` but is not exposed via Traefik by default
  - File: `local.docker.yml` environment and absence of Traefik labels/host `ports:`

### Routing & Middlewares
- [ ] T025 Validate Traefik routers for frontend and API
  - Frontend: `frontend-react` `Host(${WEBSITE_DOMAIN})` → `react-app`
  - API: `api` `Host(${WEBSITE_DOMAIN}) && PathPrefix(/api)` → `api`
  - File: `local.docker.yml`
- [ ] T026 Confirm HTTPS redirect middleware for HTTP entrypoint
  - File: `local.docker.yml` labels `redirect-to-https`
- [ ] T027 Confirm security headers middleware attached (if using `dynamic.yml`)
  - File: `traefik/dynamic.yml` and service labels
- [ ] T028 Ensure rate limiting middleware configured and attached to the API router (if desired)
  - File: `local.docker.yml` labels (e.g., `api-ratelimit`) and definitions

### Requirements & Environment
- [ ] T029 Audit `api/requirements.txt` for necessary packages and remove unused ones
  - Ensure `fastapi`, `uvicorn[standard]`, `httpx`, `psycopg2-binary`, `pydantic`, `passlib[bcrypt]`, `python-jose[cryptography]` are justified
- [ ] T030 Audit `django/requirements.txt` for necessary packages
  - Ensure `Django`, `gunicorn`, `psycopg2-binary`, `python-dotenv` are justified
- [ ] T031 Verify `.env` includes all required keys and correct values
  - `FASTAPI_*`, `DJANGO_*`, `REACT_APP_API_URL`, `POSTGRES_*`, `JWT_*`, `RATE_LIMIT_*`, `WEBSITE_DOMAIN`, Traefik-related
- [ ] T032 Add notes in `quickstart.md` for environment keys and example values

### Documentation Expansion — Detailed Usage & Use Cases
- [ ] T033 Expand `fastapi-django-extension.md` with a Ports & Routing Matrix and end-to-end flow descriptions
- [ ] T034 Add step-by-step use cases: full deploy, update-only, remote verify failure path, optional Django admin exposure (non-production)
- [ ] T035 Add troubleshooting scenarios with concrete symptoms and resolutions
- [ ] T036 Add validation checklist for operators before running deploy (pre-flight)

### Automated Preflight Script (Optional)
- [ ] T037 [P] Implement `scripts/validate-predeploy.ps1` to lint `.env`, verify compose labels/ports, and check required files
  - Usage:
    - Non-strict, human-readable: `./scripts/validate-predeploy.ps1 -EnvPath ./.env -ComposePath ./local.docker.yml`
    - Strict + JSON: `./scripts/validate-predeploy.ps1 -EnvPath ./.env -ComposePath ./local.docker.yml -Strict -Json`
- [ ] T038 [P] Add quickstart section: “Preflight Validation” with script usage and expected outcomes
- [ ] T039 Optional: Wire into `deploy.ps1` as an opt-in preflight step (e.g., `-Preflight`) that fails-fast on invalid config

**Checkpoint**: Ports, routing, requirements, and documentation validated — operators have clear, detailed guidance.

## Dependencies & Execution Order

- Setup → Foundational → US1 (MVP) → US2 → US3 → Polish
- Parallel opportunities marked [P]

