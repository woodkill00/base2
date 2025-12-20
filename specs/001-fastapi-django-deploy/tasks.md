# Tasks: FastAPI + Django Automated Deployment

**Input**: Design documents from `/specs/001-fastapi-django-deploy/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.
**Reference**: See [docs/STACK.md](docs/STACK.md) for the end-to-end stack and guardrails.

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Add env keys to `.env` for FastAPI/Django
  - `FASTAPI_PYTHON_VERSION`, `FASTAPI_PORT`, `DJANGO_PYTHON_VERSION`, `DJANGO_PORT`, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`
- [X] T002 Update React config to use `REACT_APP_API_URL=https://${WEBSITE_DOMAIN}/api`
  - Verify usage in `react-app` fetches
- [X] T003 [P] Document staging-only certificate policy in `specs/001-fastapi-django-deploy/quickstart.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 [P] Compose integration: ensure `api` and `django` services build and start via deploy automation
  - Validate through `deploy.ps1` remote artifacts and service states (no local compose runs)
- [X] T005 [P] Traefik routing: verify `/api/**` routes to `api` service
  - Labels in `local.docker.yml`
- [X] T006 API health endpoint reachable via edge
  - Files: `api/main.py` (`/api/health`)
- [X] T007 Django internal route for FastAPI proxy example
  - Files: `django/project/urls.py` (`internal/users/me`)
- [X] T008 [P] Confirm no host ports on `api`, `django`, `postgres`
  - File: `local.docker.yml`
- [X] T009 [P] Ensure staging cert resolver is used (no production issuance)
  - File: `local.docker.yml` labels

**Checkpoint**: Foundation ready — homepage and `/api/health` reachable; services healthy.

---

## Phase 3: User Story 1 — One-command cloud deploy (Priority: P1)

**Goal**: Run single deploy command to provision/update, verify, and save timestamped artifacts.

**Independent Test**: Homepage over HTTPS and `/api/health` OK; timestamped artifacts saved locally.

### Implementation

- [X] T010 Verify fail-fast behavior when DO credentials missing/invalid
  - File: `scripts/deploy.ps1` (pre-cloud action check)
- [X] T011 Confirm remote verification captures required artifacts
  - Files: `scripts/deploy.ps1` (scp outputs under `local_run_logs/<timestamp>/`)
  - Expected: `compose-ps.txt`, `traefik-env.txt`, `traefik-static.yml`, `traefik-dynamic.yml`, `traefik-ls.txt`, `traefik-logs.txt`, `curl-root.txt`, `curl-api.txt`, template snapshots
- [X] T012 [P] Ensure timestamped mode writes to per-run subfolder
  - File: `scripts/deploy.ps1` (`-Timestamped` behavior)

**Checkpoint**: Single deploy produces complete artifact set.

---

## Phase 4: User Story 2 — Update-only redeploy (Priority: P2)

**Goal**: Faster redeploy without full rebuild; preserve data and produce artifact set.

**Independent Test**: Reduced runtime vs full deploy; complete artifacts present.

### Implementation

- [X] T013 Ensure update-only flag is passed to orchestrator
  - File: `scripts/deploy.ps1` (`--update-only`)
- [ ] T014 Measure runtime comparison and document ≥30% improvement target
  - File: `specs/001-fastapi-django-deploy/quickstart.md` (notes/results)

**Checkpoint**: Update-only consistently faster with full artifacts.

---

## Phase 5: User Story 3 — Safe fallback when remote verify unavailable (Priority: P3)

**Goal**: Complete local steps and warn clearly when remote verification is skipped; still save logs.

**Independent Test**: Missing IP/SSH → local completion with warning + partial artifacts.

### Implementation

- [X] T015 Validate IP discovery fallback (`Get-DropletIp`) and skip path
  - File: `scripts/deploy.ps1`
- [X] T016 Confirm warning message and local artifacts exist when remote verify skipped
  - File: `scripts/deploy.ps1`

**Checkpoint**: Fallback path produces useful artifacts and guidance.

---

## Phase N: Polish & Cross-Cutting Concerns

- [X] T017 [P] Enhance Traefik middlewares (security headers, rate limit) if needed
  - Files: `local.docker.yml`, `traefik/dynamic.yml`
- [X] T018 [P] Update `fastapi-django-extension.md` to reflect current integration specifics
- [X] T019 Add operator troubleshooting section to `quickstart.md`
- [X] T020 [P] Optional: add basic tests for API health and Django internal endpoint

---

## Phase V: Validation — Ports, Routing, Requirements (Comprehensive)

**Goal**: Ensure all services, ports, routing rules, and package requirements are correct and consistent across files, verified via remote artifacts collected by `deploy.ps1`.

### Ports & Exposure (verify via remote artifacts)
- [X] T021 Confirm Traefik is the only publicly exposed service (host ports `80` and `443`)
  - Artifacts: `traefik-static.yml` (entrypoints `web` and `websecure`), `curl-root.txt`/`curl-api.txt` reachable over HTTPS
  - Ensure `traefik-dynamic.yml` has no public routers for `django` or `postgres`
- [X] T022 Verify `react-app` serves on internal port `8080` and Traefik routes accordingly
  - Artifacts: `traefik-dynamic.yml` service `frontend-react` with `loadbalancer.server.port=8080`; `curl-root.txt` 200
- [X] T023 Verify `api` listens on `${FASTAPI_PORT}` and Traefik forwards to this port
  - Artifacts: `traefik-dynamic.yml` service `api` `loadbalancer.server.port=${FASTAPI_PORT}`; `curl-api.txt` 200
- [X] T024 Verify `django` listens on `${DJANGO_PORT}` but is not exposed via Traefik by default
  - Artifacts: Absence of `django` router in `traefik-dynamic.yml`; internal-only access via `DJANGO_SERVICE_URL`

### Routing & Middlewares (verify via remote artifacts)
- [X] T025 Validate Traefik routers for frontend and API
  - Frontend: `frontend-react` `Host(${WEBSITE_DOMAIN})` → `react-app`
  - API: `api` `Host(${WEBSITE_DOMAIN}) && PathPrefix(/api)` → `api`
  - Artifacts: `traefik-dynamic.yml` router definitions and rules
- [X] T026 Confirm HTTPS redirect middleware for HTTP entrypoint
  - Artifacts: `traefik-dynamic.yml` middleware `redirect-to-https` on HTTP router; `curl` of `http://<domain>/` shows `Location: https://`
- [X] T027 Confirm security headers middleware attached (if using `dynamic.yml`)
  - Artifacts: `traefik-dynamic.yml` headers middleware and `curl-root.txt` contains HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy
- [X] T028 Ensure rate limiting middleware configured and attached to the API router (if desired)
  - Artifacts: `traefik-dynamic.yml` contains rate limit middleware (e.g., `api-ratelimit`) attached to `api` router; optional headers observed in `curl-api.txt`

### Requirements & Environment (verify via preflight and remote artifacts)
- [X] T029 Audit `api/requirements.txt` for necessary packages and remove unused ones
  - Ensure `fastapi`, `uvicorn[standard]`, `httpx`, `psycopg2-binary`, `pydantic`, `passlib[bcrypt]`, `python-jose[cryptography]` are justified
- [X] T030 Audit `django/requirements.txt` for necessary packages
  - Ensure `Django`, `gunicorn`, `psycopg2-binary`, `python-dotenv` are justified
- [X] T031 Verify `.env` includes all required keys and correct values
  - `FASTAPI_*`, `DJANGO_*`, `REACT_APP_API_URL`, `POSTGRES_*`, `JWT_*`, `RATE_LIMIT_*`, `WEBSITE_DOMAIN`, Traefik-related
- [X] T032 Add notes in `quickstart.md` for environment keys and example values

### Documentation Expansion — Detailed Usage & Use Cases
- [X] T033 Expand `fastapi-django-extension.md` with a Ports & Routing Matrix and end-to-end flow descriptions
- [X] T034 Add step-by-step use cases: full deploy, update-only, remote verify failure path, optional Django admin exposure (non-production)
- [X] T035 Add troubleshooting scenarios with concrete symptoms and resolutions
- [X] T036 Add validation checklist for operators before running deploy (pre-flight)

### Automated Preflight Script (Optional)
- [X] T037 [P] Implement `scripts/validate-predeploy.ps1` to lint `.env`, verify compose labels/ports, and check required files
  - Usage:
    - Non-strict, human-readable: `./scripts/validate-predeploy.ps1 -EnvPath ./.env -ComposePath ./local.docker.yml`
    - Strict + JSON: `./scripts/validate-predeploy.ps1 -EnvPath ./.env -ComposePath ./local.docker.yml -Strict -Json`
- [X] T038 [P] Add quickstart section: “Preflight Validation” with script usage and expected outcomes
- [X] T039 Optional: Wire into `deploy.ps1` as an opt-in preflight step (e.g., `-Preflight`) that fails-fast on invalid config

### Post-Deploy Verification
- [X] T045 Add `scripts/test.ps1` to verify remote artifacts and run local smoke tests
  - Verify presence of artifact files, staging resolver (`le-staging`), security headers, and API health
  - Optional: integrate with `deploy.ps1` via `-RunTests` to execute automatically
  - Add CI-friendly JSON output (`-Json`) for machine parsing

**Checkpoint**: Ports, routing, requirements, and documentation validated — operators have clear, detailed guidance.

## Constitution Compliance (Mandatory)

- [X] T040 Update `.env.example` with all required keys and keep in sync with `.env` usage across scripts and compose
  - Keys: `FASTAPI_*`, `DJANGO_*`, `REACT_APP_API_URL`, `POSTGRES_*`, `JWT_*`, `RATE_LIMIT_*`, `WEBSITE_DOMAIN`, Traefik-related
  - Validate: preflight script and manual review confirm no missing/unused variables
- [X] T041 Define Docker Compose `healthcheck` for `traefik`, `react-app`, `api`, and `django` services
  - Ensure containers report `healthy` prior to readiness; verify via `compose-ps.txt`
- [X] T042 Make tests mandatory: add test-first tasks for API health via edge, Django internal route, Traefik routing and security headers
  - Initial tests fail before implementation; pass after changes; include in CI or script-based runs
- [X] T043 Verify staging-only certificates are used and no production issuance occurs
  - Inspect remote artifacts for resolver/issuer; document verification in quickstart
- [X] T044 Validate failure messaging and artifact persistence on common failures
  - Scenarios: missing DO credentials, IP discovery failure, SSH blocked; assert clear messages and local artifacts are saved

## Dependencies & Execution Order

- Setup → Foundational → US1 (MVP) → US2 → US3 → Polish
- Parallel opportunities marked [P]

---

## Phase 6: Celery + Redis (P2)

**Goal**: Introduce Redis and Celery workers aligned to the reference, keep zero public exposure by default. Optional Flower dashboard only when explicitly enabled and strictly guarded (basic auth + IP allowlist).

### Environment & Security
- [X] T046 Add Redis/Celery env keys to `.env.example` and document in quickstart
  - `REDIS_VERSION`, `REDIS_PORT`, `REDIS_PASSWORD` (optional), `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `CELERY_CONCURRENCY`, `CELERY_LOG_LEVEL`
  - Optional Flower: `FLOWER_DNS_LABEL`, `FLOWER_BASIC_USERS` (htpasswd), `FLOWER_ALLOWLIST`
- [X] T047 [P] Validate no secrets leak into saved artifacts; scrub as needed in `deploy.ps1`

### Compose & Services
- [X] T048 Add `redis` service to `local.docker.yml` (no host ports)
- [X] T049 Add `celery-worker` service(s) consuming app image and env; depend on `redis`
- [X] T050 Optional: add `celery-beat` scheduler (if used); depend on `redis`
- [X] T051 Define `healthcheck`s for `redis`, `celery-worker`, and `celery-beat`

### Optional Flower (non-production only)
- [X] T052 Add `flower` service (disabled by default) and Traefik router guarded by basic auth + allowlist under `${FLOWER_DNS_LABEL}.${WEBSITE_DOMAIN}`
- [X] T053 Create `scripts/update-flower-allowlist.ps1` mirroring the Django admin allowlist script
- [X] T054 Extend `traefik/dynamic.yml` with an optional Flower router + middlewares; ensure absent when envs unset

### Tests & Automation
- [X] T055 Extend `scripts/test.ps1` with `-CheckCelery` flag
  - Enqueue a lightweight test task via API/Django (when available); verify completion via a poll or health endpoint; otherwise, verify Flower guarded route only when enabled
- [X] T056 Wire `-CheckCelery` into `scripts/deploy.ps1` behind an opt-in switch; persist results in JSON

### Documentation
- [X] T057 Update `fastapi-django-extension.md` and `quickstart.md` to cover Redis/Celery usage, non-production Flower enablement, and security posture
- [X] T058 Cross-link to [docs/STACK.md](docs/STACK.md) and document trust boundaries and exposure rules

### Acceptance
- [X] T059 CI/test report includes `celery` checks section when `-CheckCelery` is used
- [X] T060 No host ports opened for `redis`, `celery-*`, or `flower` services; Flower only reachable through Traefik when enabled and guarded

---

## Phase 7: Security & Compliance Implementation (Audit Coverage)

- [ ] T061 [P] Research FastAPI login/session proxy issues and document in docs/fastapi_login_proxy.md
- [ ] T062 [P] Research JWT/session/cookie best practices and document in docs/jwt_session_best_practices.md
- [ ] T063 [P] Research secret management options (Vault, AWS Secrets Manager, Docker secrets) and document in docs/secret_management.md
- [ ] T064 [P] Audit CORS and CSRF settings in FastAPI and Django, document findings in docs/cors_csrf_audit.md
- [ ] T065 [P] Review container security (Dockerfile, Compose, user permissions, resource limits) and document in docs/container_security.md
- [ ] T066 [P] Audit database security (SSL, password policy, pg_hba.conf, backups) and document in docs/database_security.md
- [ ] T067 [P] Research rate limiting/throttling (FastAPI, Django, Traefik) and document in docs/rate_limiting.md
- [ ] T068 [P] Document logging and monitoring requirements in docs/logging_monitoring.md

- [ ] T069 Define step-by-step fixes for each researched area in docs/fix_proposals.md
- [ ] T070 Propose configuration changes and code patches, mapping to specific files in docs/config_patch_map.md

### Implementation Tasks
- [ ] T071 [P] Implement strong secret generation scripts in scripts/generate-passwords.sh
- [ ] T072 [P] Update .env.example with secure template and instructions
- [ ] T073 [P] Integrate secret management solution (Vault/AWS/Docker secrets) in backend/.env, api/.env, django/.env
- [ ] T074 [P] Enforce strong password policy in postgres/postgresql.conf
- [ ] T075 [P] Implement password complexity validator in api/auth/password_validator.py
- [ ] T076 [P] Implement account lockout logic in api/auth/lockout.py
- [ ] T077 [P] Update traefik/traefik.yml for secure TLS config
- [ ] T078 [P] Update nginx/nginx.conf for SSL redirect and secure ciphers
- [ ] T079 [P] Test SSL/TLS config using scripts/test_ssl.sh
- [ ] T080 [P] Update FastAPI CORS config in api/main.py
- [ ] T081 [P] Install and configure django-cors-headers in django/settings.py
- [ ] T082 [P] Update .env.example for allowed origins and trusted origins
- [ ] T083 [P] Generate and install SSL certs for Postgres in postgres/server.crt and postgres/server.key
- [ ] T084 [P] Update postgres/postgresql.conf and pg_hba.conf for SSL and authentication
- [ ] T085 [P] Implement SQL injection prevention in api/database.py and relevant endpoints
- [ ] T086 [P] Create backup script in scripts/backup-db.sh
- [ ] T087 [P] Update api/Dockerfile to run as non-root, set resource limits, and health checks
- [ ] T088 [P] Update local.docker.yml for security options, resource limits, and secrets
- [ ] T089 [P] Add container security scan workflow in .github/workflows/security-scan.yml
- [ ] T090 [P] Implement RSA key pair generation in scripts/generate-jwt-keys.sh
- [ ] T091 [P] Refactor JWT handling to use RS256 in api/auth/jwt_handler.py
- [ ] T092 [P] Implement token blacklisting and refresh logic in api/auth/jwt_handler.py
- [ ] T093 [P] Add/extend Pydantic models for validation in api/models/validators.py
- [ ] T094 [P] Add request size limit middleware in api/main.py
- [ ] T095 [P] Audit and update Django form validation in django/forms.py
- [ ] T096 [P] Implement FastAPI rate limiting with slowapi in api/main.py
- [ ] T097 [P] Implement Django rate limiting with django-ratelimit in django/views.py
- [ ] T098 [P] Add Traefik rate limiting config in traefik/dynamic/rate-limit.yml
- [ ] T099 [P] Update local.docker.yml for network segmentation
- [ ] T100 [P] Create firewall setup script in scripts/setup-firewall.sh
- [ ] T101 [P] Implement structured logging with structlog in api/logging_config.py
- [ ] T102 [P] Add security event monitoring middleware in api/middleware/security_logger.py

### Validation & Review
- [ ] T103 Validate each fix with tests/manual checks, document in docs/validation_results.md
- [ ] T104 Review all changes for constitution/audit compliance, update docs/audit_checklist.md
- [ ] T105 Update README.md with security checklist and process documentation

