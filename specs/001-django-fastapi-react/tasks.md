# Tasks: Full-stack Baseline (001-django-fastapi-react)

**Input**: Design documents from `/specs/001-django-fastapi-react/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: INCLUDED (constitution: TDD by default; spec marks “User Scenarios & Testing” as mandatory). Any “done” verification MUST be runnable via `digital_ocean/scripts/powershell/deploy.ps1 -AllTests`.

## Verification Commands (single-entrypoint)

- Iteration (default): `digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests -Timestamped`
- Baseline full deploy (only when necessary): `digital_ocean/scripts/powershell/deploy.ps1 -Full -AllTests -Timestamped`
- When Full is necessary: first deploy (no droplet yet), droplet provisioning/user-data changes, DNS/firewall/VPC changes, or anything that invalidates update-in-place assumptions.
- Compatibility rule: `deploy.ps1 -AllTests` should still work; see T078 to make it prefer UpdateOnly when an environment already exists.

### Pre-Deploy Discipline (UpdateOnly + AllTests)

- Prerequisite: Commit and push any runtime-impacting changes to the droplet-tracked branch before running UpdateOnly. The deploy orchestration hard-resets the remote to `origin/<DO_APP_BRANCH>`, so local edits will not apply unless they are pushed.
- Branch source: Ensure `.env` sets `DO_APP_BRANCH` to the intended branch. Push to `origin/<DO_APP_BRANCH>` prior to invoking `-UpdateOnly -AllTests`.
- Scope: Runtime-impacting files include service code (e.g., `api/`, `django/`, `react-app/`), Dockerfiles, compose files, and Traefik configs. Docs-only changes do not require an UpdateOnly push.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Every task description includes at least one exact file path and a verification hook.

## Path Conventions (this repo)

- FastAPI service: `api/`
- Django service: `django/`
- React SPA: `react-app/`
- Edge proxy: `traefik/`
- Deploy/test entrypoint: `digital_ocean/scripts/powershell/deploy.ps1`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Documentation + baseline test scaffolding + feature hygiene

- [X] T001 [P] Remove duplicated “OAuth Identity” bullet under Key Entities in specs/001-django-fastapi-react/spec.md ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T002 [P] Add feature links to README.md pointing to specs/001-django-fastapi-react/spec.md and specs/001-django-fastapi-react/plan.md ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T003 [P] Create docs/DEPLOY.md documenting “deploy.ps1 is authoritative” and staging-only ACME policy ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T004 [P] Create docs/SECURITY.md documenting cookie auth + CSRF + admin tool gating ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T005 [P] Update docs/STACK.md to include the current service inventory from local.docker.yml ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Environment + configuration

 - [X] T006 Add missing auth/security env vars to .env.example (SESSION_COOKIE_NAME, CSRF_COOKIE_NAME, COOKIE_SAMESITE, COOKIE_SECURE, DJANGO_INTERNAL_BASE_URL, RATE_LIMIT_REDIS_PREFIX, GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, GOOGLE_OAUTH_REDIRECT_URI, OAUTH_STATE_SECRET) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
 - [X] T007 Implement centralized FastAPI settings loader in api/settings.py (read env; validate required values; defaults safe for staging) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
 - [X] T008 [P] Implement request-id middleware in api/middleware/request_id.py and wire it in api/main.py (echo `X-Request-Id`) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
 - [X] T009 [P] Implement standard JSON error handlers in api/middleware/errors.py and wire in api/main.py (ensure consistent `{detail}` shape per contract) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests

### Security primitives (rate limiting + CSRF/cookies)

 - [X] T010 [P] Implement Redis helper in api/redis_client.py (connect, ping, prefixed keys) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
 - [X] T011 Implement app-level rate limiting in api/security/rate_limit.py (Redis counters keyed by IP + endpoint; 429 responses) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
 - [X] T012 [P] Define cookie/CSRF header conventions in specs/001-django-fastapi-react/research.md (cookie names and header name `X-CSRF-Token`) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests

### Traefik exposure hardening

 - [X] T013 Restrict admin subdomain router to only `/admin` paths in traefik/dynamic.yml (avoid exposing any internal endpoints on admin host) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
 - [X] T014 [P] Add a deploy-time probe that admin.<domain> rejects non-/admin paths in digital_ocean/scripts/powershell/test.ps1 (records meta/admin-host-path-guard.json) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests

### Django cookie/CSRF defaults

 - [X] T015 [P] Confirm/adjust cookie + CSRF defaults in django/project/settings/production.py (Secure, HttpOnly for session cookie; SameSite; trusted origins where needed) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests

### Test tooling + deploy orchestration (gated through deploy.ps1)

 - [X] T016 Add pytest tooling deps to api/requirements.txt (pytest, pytest-asyncio, httpx) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
 - [X] T017 Add pytest tooling deps to django/requirements.txt (pytest, pytest-django) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
 - [X] T018 [P] Create api/pytest.ini for test discovery ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
 - [X] T019 [P] Create django/pytest.ini + django/conftest.py configuring pytest-django settings module ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
 - [X] T020 [P] Add a minimal FastAPI test scaffold in api/tests/test_smoke.py (imports app and asserts health route exists) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
 - [X] T021 [P] Add a minimal Django test scaffold in django/tests/test_smoke.py (loads settings; asserts UserProfile model import) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T022 Update digital_ocean/scripts/powershell/deploy.ps1 to run `pytest` inside api container and save output to local_run_logs/<run>/api/pytest.txt ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T023 Update digital_ocean/scripts/powershell/deploy.ps1 to run `pytest` inside django container and save output to local_run_logs/<run>/django/pytest.txt ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T024 Update digital_ocean/scripts/powershell/deploy.ps1 to run `npm run test:ci` in react-app/ and save output to local_run_logs/<run>/react-app/jest.txt ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Production-like deploy verification (Priority: P1) 🎯 MVP

**Goal**: Deploy/update the full stack and always get a clear verification report and artifacts.

**Independent Test**: `digital_ocean/scripts/powershell/deploy.ps1 -Full -AllTests -Timestamped` produces `local_run_logs/<ip>-<timestamp>/meta/post-deploy-report.json` with `success=true`.
**Steady-state Test**: `digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests -Timestamped` produces the same report once an environment exists.

### Tests for User Story 1 (write/extend first) ⚠️

- [X] T025 [P] [US1] Add contract-vs-runtime OpenAPI path check in digital_ocean/scripts/powershell/test.ps1 by parsing specs/001-django-fastapi-react/contracts/openapi.yaml `paths:` keys and verifying they exist in fetched api/openapi.json (write api/openapi-contract-check.json) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T026 [P] [US1] Add guarded endpoint probes in digital_ocean/scripts/powershell/test.ps1 for unauthenticated access (e.g., /api/users/me, /api/users/logout) and write meta/guarded-endpoints.json ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T027 [P] [US1] Add an artifact completeness check in digital_ocean/scripts/powershell/test.ps1 (assert key artifacts exist: openapi.json, openapi-validation.json, schema-compat-check.json, post-deploy-report.json) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests

### Implementation for User Story 1

- [X] T028 [US1] Ensure post-deploy report schema includes new check blocks (openApiContractCheck, guardedEndpointsCheck, artifactCompletenessCheck) in digital_ocean/scripts/powershell/test.ps1 ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T029 [US1] Align specs/001-django-fastapi-react/contracts/openapi.yaml with actual external routes (only change if real implementation differs) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T030 [US1] Expand specs/001-django-fastapi-react/quickstart.md with artifact locations and “how to interpret” guidance for meta/post-deploy-report.json ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests

**Checkpoint**: At this point, US1 is independently verifiable and becomes the deployment safety net for all later stories

---

## Phase 4: User Story 2 - Signup and login/logout (Priority: P2)

**Goal**: Visitor can sign up, log in, log out securely with cookie auth; rate limiting and enumeration resistance are enforced; CSRF blocks state-changing calls without token.

**Independent Test**: `digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests` runs Django + FastAPI + React tests covering signup/login/logout, and post-deploy probes confirm protected endpoints deny unauthenticated access.

### Tests for User Story 2 (write first) ⚠️

- [X] T031 [P] [US2] Add Django tests for internal auth API in django/tests/test_auth_api.py (signup, login, logout, me; duplicate email; generic errors; CSRF rejection) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T032 [P] [US2] Add Django tests for audit events in django/tests/test_audit_events.py (login failure/success actions recorded; secrets not in metadata) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T033 [P] [US2] Add FastAPI proxy tests in api/tests/test_auth_proxy.py (cookie forwarding; header forwarding; error mapping; 429 passthrough) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T034 [P] [US2] Add FastAPI rate limit tests in api/tests/test_rate_limit.py (Redis counter increments; 429 returns {detail}) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests

### Implementation for User Story 2 (Django internal endpoints)

- [X] T035 [US2] Implement internal JSON auth views in django/users/api_views.py (signup/login/logout/me/profile patch) using Django auth + sessions ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T036 [US2] Add internal routes in django/users/api_urls.py and mount under /internal/api in django/project/urls.py ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T037 [US2] Implement CSRF bootstrap view in django/users/api_views.py (ensures CSRF cookie is set; returns `{detail}` or token info) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T038 [US2] Ensure UserProfile auto-creation on signup in django/users/models.py or django/users/signals.py (if not already present) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T039 [US2] Emit AuditEvent records for auth actions in django/users/api_views.py using django/users/models.py::AuditEvent ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests

### Implementation for User Story 2 (FastAPI external surface)

- [X] T040 [US2] Create Django proxy client in api/clients/django_client.py (base URL from api/settings.py; forwards cookies + CSRF header; timeout; error mapping) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T041 [US2] Implement external auth routes in api/routes/auth.py for /users/signup, /users/login, /users/logout and include router in api/main.py ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T042 [US2] Implement external current-user routes in api/routes/users.py for /users/me (GET + PATCH) and include router in api/main.py ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T043 [US2] Apply app-level rate limiting to external signup/login in api/routes/auth.py using api/security/rate_limit.py ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T044 [US2] Update FastAPI OpenAPI metadata in api/main.py (title/version) to remain compatible with specs/001-django-fastapi-react/contracts/openapi.yaml ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests

### React minimal auth UI (US2 scope)

- [X] T045 [P] [US2] Add React tests for login/logout UI in react-app/src/__tests__/auth.test.js (successful login sets authenticated state; logout clears it) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T046 [US2] Implement Login page in react-app/src/pages/Login.jsx (email/password form; calls POST /api/users/login with credentials) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T047 [US2] Implement Signup page in react-app/src/pages/Signup.jsx (email/password; calls POST /api/users/signup) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T048 [US2] Wire routes for /login and /signup in react-app/src/App.js ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests

**Checkpoint**: At this point, a user can sign up, sign in, sign out, and the session cookie auth works end-to-end

---

## Phase 5: User Story 3 - Dashboard and settings (Priority: P3)

**Goal**: Signed-in user sees dashboard and can update profile settings; session expiry redirects to login with friendly messaging.

**Independent Test**: `digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests` passes React tests for protected routes and API tests for profile update; manual staging smoke shows dashboard loads behind auth.

### Tests for User Story 3 (write first) ⚠️

- [X] T049 [P] [US3] Add React tests for protected route gating in react-app/src/__tests__/protected-route.test.js ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T050 [P] [US3] Add React tests for dashboard render in react-app/src/__tests__/dashboard.test.js ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T051 [P] [US3] Add React tests for settings update form in react-app/src/__tests__/settings.test.js ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T052 [P] [US3] Add API integration tests for PATCH /api/users/me allowed fields in api/tests/test_profile_update.py ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests

### Implementation for User Story 3 (React)

- [X] T053 [US3] Create ProtectedRoute component in react-app/src/components/ProtectedRoute.jsx (redirect to /login on 401/unauthenticated) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T054 [US3] Create auth hook in react-app/src/hooks/useAuth.js (loads current user via GET /api/users/me; exposes loading/authenticated/user) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T055 [US3] Create axios wrapper in react-app/src/lib/apiClient.js (withCredentials; attaches X-CSRF-Token when present) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T056 [US3] Implement Dashboard page in react-app/src/pages/Dashboard.jsx (renders email + basic metadata) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T057 [US3] Implement Settings page in react-app/src/pages/Settings.jsx (edit display_name/avatar_url/bio; calls PATCH /api/users/me) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T058 [US3] Wire routes for /dashboard and /settings in react-app/src/App.js using ProtectedRoute ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests

**Checkpoint**: At this point, dashboard + profile update flows are independently testable

---

## Phase 6: User Story 4 - Sign in with Google (Priority: P4)

**Goal**: User can sign in with Google via Authorization Code flow and end in an authenticated cookie session; failures are safe and non-sensitive.

**Independent Test**: `digital_ocean/scripts/powershell/deploy.ps1 -AllTests` passes backend unit tests for OAuth state/redirect validation and React tests for OAuth button + callback handling.

### Tests for User Story 4 (write first) ⚠️

- [X] T059 [P] [US4] Add Django tests for OAuth start/callback in django/tests/test_oauth_google.py (state validation; allowlist; cancel/fail paths; account link) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T060 [P] [US4] Add FastAPI proxy tests for OAuth routes in api/tests/test_oauth_proxy.py ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T061 [P] [US4] Add React tests for OAuth start + callback UX in react-app/src/__tests__/oauth.test.js ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests

### Implementation for User Story 4 (Django + FastAPI + React)

- [X] T062 [US4] Document required Google OAuth env vars in specs/001-django-fastapi-react/quickstart.md (client id/secret/redirect; state secret) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T063 [US4] Ensure OAuthAccount uniqueness constraints align with data-model.md in django/users/models.py (add migration if missing) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T064 [US4] Implement internal OAuth views in django/users/api_views.py (start → auth URL; callback → exchange code; link/create user; create session; audit event) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T065 [US4] Implement external OAuth proxy routes in api/routes/oauth.py (/oauth/google/start and /oauth/google/callback) and include router in api/main.py ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T066 [US4] Add Login page “Sign in with Google” button in react-app/src/pages/Login.jsx (calls POST /api/oauth/google/start then redirects) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T067 [US4] Add OAuth callback page in react-app/src/pages/OAuthCallback.jsx (reads code/state; calls POST /api/oauth/google/callback; redirects to /dashboard; safe error display) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T068 [US4] Wire /oauth/google/callback route in react-app/src/App.js ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests

**Checkpoint**: At this point, OAuth login works end-to-end (or is safely failing with tests proving failure handling)

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T069 [P] Update docs/SECURITY.md to include rate limiting policies (Traefik + app-level) and enumeration-safe error guidance ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T070 [P] Add “quickstart validation checklist” to specs/001-django-fastapi-react/quickstart.md (URLs + artifact files + expected report keys) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T071 [P] Add a note to .specify/scripts/bash/common.sh about Git Bash vs WSL path differences on Windows and recommend Git Bash for prereq checks ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T072 Resolve Spec-Kit numeric-prefix ambiguity by renumbering any conflicting spec directory and updating README.md links (optional, only if another 001-* directory exists) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests

---

## Dependencies & Execution Order

### Dependency Graph (user-story order)

- Phase 1 (Setup) → Phase 2 (Foundational) → US1 (MVP) → US2 → US3 → US4 → Phase 7 (Polish)

### Within-Story Order

- Tests (must fail first) → implementation (models/settings) → routes → integration → deploy.ps1 -AllTests pass

---

## Parallel Execution Examples (per story)

- US1: T025 and T026 can be parallel (separate check blocks in digital_ocean/scripts/powershell/test.ps1).
- US2: T031, T032, T033, T034 can be parallel (tests in different files).
- US3: T049, T050, T051 can be parallel (React tests in separate files).
- US4: T059, T060, T061 can be parallel (tests split across Django/FastAPI/React).

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 + Phase 2
2. Complete US1 (T025–T030)
3. STOP and validate: `digital_ocean/scripts/powershell/deploy.ps1 -Full -AllTests -Timestamped`

### Incremental Delivery

- Add US2 → validate deploy/tests → add US3 → validate → add US4 → validate

---

## Verification Enhancements (Additions)

- [X] T073 [P] [US1] Add explicit staging-only TLS guard verification in digital_ocean/scripts/powershell/test.ps1 (assert ACME uses staging directory; fail if production issuance is configured; write meta/tls-acme-guard.json) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T074 [P] [US1] Add health timing probe in digital_ocean/scripts/powershell/test.ps1 (sample N requests to /api/health; compute p95; enforce SC-002 p95 < 5s; write meta/health-timings.json) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T075 [P] [US1] Add login timing probe in digital_ocean/scripts/powershell/test.ps1 (sample N logins under “normal conditions”; enforce SC-004 99% < 2s; write meta/login-timings.json) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T076 [P] [US1] Add signup-to-dashboard timing probe in digital_ocean/scripts/powershell/test.ps1 (script signup + auth confirmation via /api/users/me; optionally fetch a protected page; enforce SC-003 < 2 minutes; write meta/signup-to-dashboard-timings.json) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [X] T077 [P] [US1] Add health response contract-shape check in digital_ocean/scripts/powershell/test.ps1 (assert /api/health JSON fields minimally: ok/service/db_ok; write meta/health-contract-check.json) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests

### Make AllTests prefer UpdateOnly when possible

- [X] T078 [US1] Update digital_ocean/scripts/powershell/deploy.ps1 so `-AllTests` prefers `-UpdateOnly` automatically when an existing droplet/environment can be resolved and `-Full` was not requested (fallback to full deploy only when needed; log the chosen mode into artifacts) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
---

## Phase 8: Repo Hygiene + Deploy Correctness (Hardening)

**Purpose**: Remove risky artifacts, fix container boot reliability, and ensure local + droplet deploys behave the same.

- [X] T079 Remove committed `./docker-compose` ELF binary from repo and prevent re-introduction.
  - **Why**: It is a platform-specific executable that can confuse tooling, trip scanners, and bloat the repo.
  - **Touch**:
    - `docker-compose` (delete from repo)
    - `.gitignore` (add `/docker-compose` and optionally `/.docker/` artifacts)
    - `README.md` (ensure instructions use `docker compose` v2 syntax, not `./docker-compose`)
    - Optional: `.gitattributes` (mark binaries to avoid diffs if you keep any)
  - **How**:
    1) Remove the file from git history in the current branch: `git rm -f docker-compose`
    2) Add ignore rule so it can exist locally but never be committed again.
    3) Search repo for references to `./docker-compose` and replace with `docker compose`.
    4) Add a CI guard that fails if a tracked file named `docker-compose` reappears (see T089).
  - **Verify**: `digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests`

- [X] T080 Fix Django container entrypoint + remove “truncated CMD” risk in `django/.Dockerfile`.
  - **Touch**:
    - `django/.Dockerfile`
    - `django/entrypoint.sh` (new)
    - `local.docker.yml` / `docker-compose.yml` (where Django service command is set; repo-dependent)
    - `digital_ocean/scripts/powershell/deploy.ps1` (if it assumes a specific container command)
  - **How**:
    1) Create `django/entrypoint.sh`:
       - `set -euo pipefail`
       - Wait for Postgres (reuse existing healthcheck or add `python manage.py check --database default`)
       - Run `python manage.py migrate --noinput` (safe in staging; in prod decide if migrations are separate release step)
       - Run `python manage.py collectstatic --noinput` (only when STATIC_ROOT is configured; no-op otherwise)
       - Exec gunicorn: `exec gunicorn project.wsgi:application --bind 0.0.0.0:8000 --workers ${DJANGO_WORKERS:-2} --timeout ${DJANGO_TIMEOUT:-60}`
    2) In `django/.Dockerfile`, set:
       - `COPY entrypoint.sh /entrypoint.sh && chmod +x /entrypoint.sh`
       - `ENTRYPOINT ["/entrypoint.sh"]`
       - Remove any broken/truncated `CMD`.
    3) Ensure compose uses correct container port and healthcheck endpoint (e.g., `/admin/login/` or a new `/internal/health`).
  - **Verify**: `digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests`

- [X] T081 Add explicit Django internal health endpoint for deploy/test probes (avoid probing admin HTML).
  - **Touch**:
    - `django/project/urls.py` (route)
    - `django/project/views.py` (new) or `django/users/api_views.py`
    - `digital_ocean/scripts/powershell/test.ps1` (probe new endpoint)
  - **How**:
    - Add `/internal/health` returning JSON: `{ "ok": true, "service": "django", "db_ok": true }`.
    - DB check should be a lightweight `connection.ensure_connection()` guarded with try/except.
    - Update `test.ps1` to call this endpoint via the admin host (or internal service hostname depending on topology).
  - **Verify**: `digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests`

---

## Phase 9: Edge Security Headers + TLS Hygiene

**Purpose**: Establish consistent security headers and reduce browser attack surface.

- [X] T082 Centralize Traefik security headers middleware and attach to all public routers (api + spa).
  - **Touch**:
    - `traefik/dynamic.yml` (middlewares + router attachments)
    - `traefik/traefik.yml` (if static config needs header defaults)
    - `docs/SECURITY.md` (document the header policy)
  - **How**:
    1) In `traefik/dynamic.yml`, create a middleware (example name: `security-headers`) with:
       - `stsSeconds` (HSTS; staging may omit or set low)
       - `stsIncludeSubdomains` (prod only)
       - `frameDeny` or frame options
       - `contentTypeNosniff`, `browserXssFilter` (legacy but ok), `referrerPolicy`
       - `customResponseHeaders` for `Permissions-Policy`
    2) Create a second middleware for CSP:
       - For React SPA: `default-src 'self'; script-src 'self' ...; connect-src 'self' https://accounts.google.com ...` (tailor if OAuth or analytics)
       - Keep CSP disabled in local dev if it blocks HMR; enable in staging/prod routers.
    3) Attach `security-headers` middleware to:
       - public web router
       - public api router
       - admin router (optional; keep strict)
  - **Verify**: Extend `digital_ocean/scripts/powershell/test.ps1` to curl headers from `/` and `/api/health` and write `meta/security-headers.json`, then run `digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests`

- [X] T083 Add “TLS mode guard” to ensure production cert issuance cannot be enabled accidentally.
  - **Touch**:
    - `traefik/traefik.yml` (ACME CA server URL)
    - `digital_ocean/scripts/powershell/test.ps1` (assert staging directory)
    - `docs/DEPLOY.md` (explicit warning)
  - **How**:
    - You already have T073; extend it to also assert:
      - `acme.email` is set
      - storage path is not world-readable
      - no “production” resolver present unless `ENV=prod` flag is explicitly set in droplet env.
  - **Verify**: `digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests`

---

## Phase 10: API Runtime + DB Layer Improvements (Stability + Scale)

**Purpose**: Make FastAPI production-ready (process model, timeouts, typed settings, DB pooling).

- [X] T084 Switch FastAPI container to Gunicorn + Uvicorn workers (or uvicorn multi-worker) with sane defaults.
  - **Touch**:
    - `api/Dockerfile` (or `api/.Dockerfile` if present)
    - `api/entrypoint.sh` (new, recommended)
    - `local.docker.yml` / compose service command for `api`
    - `docs/STACK.md` (runtime note)
  - **How**:
    1) Add `gunicorn` to `api/requirements.txt`.
    2) Add `api/entrypoint.sh`:
       - `set -euo pipefail`
       - Optionally run a quick import check: `python -c "import api.main"`
       - `exec gunicorn api.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --workers ${API_WORKERS:-2} --timeout ${API_TIMEOUT:-60} --graceful-timeout ${API_GRACEFUL_TIMEOUT:-30}`
    3) Ensure container healthcheck still hits `/api/health`.
  - **Verify**:
    - Add `api/tests/test_process_model.py` to assert app still serves `/health` under the new command (basic httpx call inside container).
    - `digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests`

- [X] T085 Replace ad-hoc psycopg2 usage with a pooled approach and explicit timeouts.
  - **Touch**:
    - `api/db.py` (or wherever connections are built; currently `api/database.py`-like)
    - `api/settings.py` (pool size + timeouts)
    - `api/routes/health.py` (or `api/main.py` health route)
    - `api/tests/test_db_pooling.py` (new)
  - **How**:
    - Option A (minimal): use `psycopg2.pool.ThreadedConnectionPool` and ensure every request returns connections.
    - Option B (better long-term): migrate to SQLAlchemy engine (sync) and keep Django as schema owner (FastAPI reads only).
    - Add connect and statement timeouts:
      - Postgres `connect_timeout`
      - set `statement_timeout` per connection (or per query) to avoid hanging.
  - **Verify**: `digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests`

---

## Phase 11: CI Guardrails (Prevent regressions)

**Purpose**: Enforce code quality, prevent bad artifacts (like the binary), and ensure OpenAPI remains aligned.

- [ ] T086 Add GitHub Actions workflow: backend lint + typecheck + tests (FastAPI + Django).
  - **Touch**:
    - `.github/workflows/ci-backend.yml` (new)
    - `api/pyproject.toml` (new; ruff config) OR `api/requirements-dev.txt`
    - `django/pyproject.toml` (optional) OR `django/requirements-dev.txt`
  - **How**:
    - Use `ruff` for lint/format and `pytest` for tests.
    - Cache pip.
    - Run matrix jobs: `api` and `django`.
    - Ensure env vars needed for tests are set (use sqlite for Django unit tests if possible, or spin Postgres service).
  - **Verify**: CI green on PR; local still: `digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests`

- [ ] T087 Add GitHub Actions workflow: frontend lint + test + build.
  - **Touch**:
    - `.github/workflows/ci-frontend.yml` (new)
    - `react-app/package.json` (scripts: `lint`, `test:ci`, `build`)
  - **How**:
    - `npm ci`
    - `npm run test:ci`
    - `npm run build`
  - **Verify**: CI green + `deploy.ps1 -AllTests` still passes.

- [ ] T088 Add contract test in CI: OpenAPI contract vs runtime, plus “no missing auth endpoints”.
  - **Touch**:
    - `.github/workflows/ci-contract.yml` (new)
    - Reuse/port logic from `digital_ocean/scripts/powershell/test.ps1` (or write a small Python script in `scripts/contract_check.py`)
  - **How**:
    - Stand up stack in CI with `docker compose up -d`.
    - Fetch `/api/openapi.json` and compare required routes from `specs/.../contracts/openapi.yaml`.
  - **Verify**: CI green.

- [ ] T089 Add a repository guard: fail if forbidden binaries are tracked (docker-compose, *.exe, large blobs).
  - **Touch**:
    - `.github/workflows/ci-repo-guards.yml` (new)
    - `scripts/repo_guard.sh` (new)
  - **How**:
    - Script checks:
      - tracked file named `docker-compose`
      - any tracked file > 5MB unless allowlisted
      - executable binaries in root without allowlist
  - **Verify**: CI green; attempt to commit forbidden files fails in PR.

---

## Phase 12: Feature Expansion (Email Verification + Password Reset + Better Auditing)

**Purpose**: Complete the auth surface React already implies and add expected account-management features.

- [ ] T090 Implement email delivery plumbing via Celery (provider-agnostic) and a safe “outbox” fallback for local.
  - **Touch**:
    - `django/users/emails.py` (new helper: render + send)
    - `django/users/tasks.py` (Celery tasks: send_verification_email, send_password_reset_email)
    - `django/project/celery.py` (if Celery app config lives here; ensure autodiscover)
    - `local.docker.yml` (ensure worker imports Django settings; already exists but confirm)
    - `docs/STACK.md` + `specs/.../quickstart.md` (how to view emails in local)
  - **How**:
    1) Add Django email settings to `.env.example`:
       - SMTP host/port/user/pass OR a provider token
       - `DEFAULT_FROM_EMAIL`
    2) For local dev, implement an “outbox” table:
       - Model `EmailOutbox(to, subject, body, created_at, sent_at, provider_message_id)`
       - If SMTP not configured, write emails to outbox and log.
    3) Celery task:
       - accept `email_outbox_id` or full payload
       - on success, mark `sent_at`
       - on failure, retry with exponential backoff; cap retries.
  - **Verify**:
    - Django tests in `django/tests/test_email_tasks.py`
    - `deploy.ps1 -AllTests`

- [ ] T091 Add Email Verification flow (token issuance + verify endpoint + UI).
  - **Touch**:
    - `django/users/models.py` (new model: `EmailVerificationToken` or generic `OneTimeToken`)
    - `django/users/migrations/*` (new)
    - `django/users/api_views.py` (issue token on signup; verify endpoint)
    - `django/users/api_urls.py` (route `/verify-email`)
    - `api/routes/auth.py` (proxy route `/users/verify-email`)
    - `specs/.../contracts/openapi.yaml` (add endpoints if missing)
    - `react-app/src/pages/VerifyEmail.jsx` (new)
    - `react-app/src/App.js` (route)
  - **How**:
    - Token design:
      - random 32+ bytes (urlsafe), store hash in DB (never store raw token)
      - expiry (e.g., 24h)
      - one-time use: mark consumed
    - On signup:
      - create token
      - enqueue Celery email
      - response should not reveal whether email exists beyond normal signup flow
    - Verify:
      - accept token
      - mark user `email_verified=true`
      - consume token
      - create audit event
  - **Verify**:
    - Django tests: `django/tests/test_email_verification.py`
    - React tests: `react-app/src/__tests__/verify-email.test.js`
    - `deploy.ps1 -AllTests`

- [ ] T092 Add Forgot Password + Reset Password flow (enumeration-safe).
  - **Touch**:
    - `django/users/models.py` (reset token model; can reuse generic token table)
    - `django/users/api_views.py` (`/forgot-password`, `/reset-password`)
    - `api/routes/auth.py` (proxy routes)
    - `react-app/src/pages/ForgotPassword.jsx`, `react-app/src/pages/ResetPassword.jsx`
    - `react-app/src/App.js`
    - `docs/SECURITY.md` (enumeration-safe guidance)
  - **How**:
    - Forgot password:
      - ALWAYS return 200 with generic message
      - if email exists, create token + queue email
      - rate limit heavily (reuse app-level limiter + optionally Django-side)
    - Reset:
      - validate token, expiry, one-time use
      - set password via Django auth APIs
      - rotate session / require re-login (or auto-login if desired, but document)
      - audit event
  - **Verify**:
    - Django tests: `django/tests/test_password_reset.py`
    - FastAPI proxy tests: `api/tests/test_password_reset_proxy.py`
    - React tests: `react-app/src/__tests__/password-reset.test.js`
    - `deploy.ps1 -AllTests`

- [ ] T093 Expand AuditEvent coverage and add an admin-visible audit dashboard in Django Admin.
  - **Touch**:
    - `django/users/models.py` (ensure `AuditEvent` has indexes: actor, action, created_at)
    - `django/users/admin.py` (register AuditEvent with list filters + search)
    - `django/users/api_views.py` (emit events for verify/reset flows)
    - `docs/SECURITY.md` (what is logged and what is explicitly NOT logged)
  - **How**:
    - Make sure metadata never includes secrets:
      - never store raw tokens, passwords, OAuth codes
    - Add admin list display: actor email, action, ip, user_agent, created_at
  - **Verify**: Django admin loads on `admin.<domain>/admin/` and `deploy.ps1 -AllTests`

---

## Phase 13: Observability (Logs, Request IDs, Metrics)

**Purpose**: Make diagnosing issues fast (especially on droplet).

- [ ] T094 Structured JSON logging across Traefik, FastAPI, Django, Celery.
  - **Touch**:
    - `api/main.py` / `api/logging.py` (new)
    - `django/project/settings/*.py` (LOGGING config)
    - `local.docker.yml` (log driver config if needed)
    - `digital_ocean/scripts/powershell/test.ps1` (capture sample logs into artifacts)
  - **How**:
    - Standard fields: `timestamp`, `level`, `service`, `request_id`, `path`, `method`, `status`, `latency_ms`.
    - Propagate request id:
      - Traefik sets `X-Request-Id` if missing; FastAPI echoes; Django forwards/echoes.
    - Ensure Celery tasks log `task_id` and `request_id` if available (pass request_id in task args).
  - **Verify**: Add a probe that makes a request and then `docker logs` grep for the request id; write `meta/request-id-log-propagation.json`; run `deploy.ps1 -AllTests`

- [ ] T095 Add lightweight metrics endpoint(s) (start with app-level timings you already compute).
  - **Touch**:
    - `api/routes/metrics.py` (new, optional)
    - `digital_ocean/scripts/powershell/test.ps1` (collect and store)
  - **How**:
    - Start simple: expose counters/timings you already compute in test harness.
    - If adopting Prometheus later, keep endpoint compatible (`text/plain; version=0.0.4`).
  - **Verify**: `deploy.ps1 -AllTests`

---
---

## Phase 14: Option A Auth (FastAPI owns authentication end-to-end)

**Purpose**: Implement the full auth surface in FastAPI directly (users, sessions/tokens, OAuth, email flows), so React talks only to FastAPI for auth and identity. Django remains optional for admin/schema, but is not in the request path for auth.

### Design constraints (bake into tasks)
- **Single public auth surface**: React calls FastAPI only (`/api/auth/*`).
- **Enumeration-safe**: forgot-password and verify-email do not reveal whether an email exists.
- **Token model**: short-lived access token + long-lived refresh token (rotation) OR secure httpOnly cookie sessions. Pick one and implement consistently.
- **Secret hygiene**: never store raw tokens; store hashes + metadata; rotate keys.

---

### Core auth primitives

- [ ] T096 Define FastAPI auth ownership boundaries and update routing contract
  - **Touch**:
    - `specs/.../contracts/openapi.yaml` (auth endpoints canonical)
    - `react-app/src/services/auth.js` (ensure base paths match)
    - `traefik/dynamic.yml` (ensure `/api` routing does not strip required segments unexpectedly)
    - `docs/STACK.md` (document: “FastAPI owns auth”)
  - **How**:
    1) Choose canonical endpoint prefix: **`/api/auth`** (recommended).
    2) List required endpoints React needs (minimum):
       - `POST /api/auth/login`
       - `POST /api/auth/logout`
       - `POST /api/auth/refresh`
       - `GET  /api/auth/me`
       - `POST /api/auth/register`
       - `POST /api/auth/forgot-password`
       - `POST /api/auth/reset-password`
       - `POST /api/auth/verify-email`
       - `POST /api/auth/oauth/google`
    3) Update OpenAPI contract first (so tests can enforce).
  - **Verify**: contract test (see T088) fails until endpoints exist, then passes.

- [ ] T097 Create FastAPI identity schema + persistence layer (Users + tokens + audit)
  - **Touch**:
    - `api/models/*.py` (new: SQLAlchemy models or equivalent)
    - `api/db.py` (engine + sessions/pool)
    - `api/alembic/*` (new) OR `api/migrations/*` (your chosen migration tool)
    - `api/settings.py` (JWT secrets, token TTLs, bcrypt params)
    - `api/tests/test_user_model.py` (new)
  - **How**:
    - Tables (minimum):
      - `users`: id, email (unique, indexed), password_hash, is_active, is_email_verified, created_at, updated_at
      - `refresh_tokens`: id, user_id, token_hash, created_at, expires_at, revoked_at, replaced_by_token_id, user_agent, ip
      - `one_time_tokens`: id, user_id (nullable), token_hash, type (`verify_email`, `reset_password`), expires_at, consumed_at
      - `audit_events`: id, user_id nullable, action, ip, user_agent, metadata_json, created_at
    - Password hashing:
      - `bcrypt` or `argon2` (argon2 preferred if you already use it; otherwise bcrypt is fine).
    - Token hashing:
      - store `sha256(token + pepper)` (pepper in env) rather than raw token.
  - **Verify**:
    - unit tests: unique email constraint, token hash not raw, expiry behavior.

- [ ] T098 Implement FastAPI auth service layer (hashing, token creation, rotation, verification)
  - **Touch**:
    - `api/services/auth_service.py` (new)
    - `api/services/token_service.py` (new)
    - `api/services/audit_service.py` (new)
    - `api/tests/test_token_rotation.py` (new)
  - **How**:
    - Access tokens:
      - JWT with `sub=user_id`, `email`, `iat`, `exp`, `jti`.
      - TTL: 10–20 minutes.
    - Refresh tokens:
      - Random 32+ bytes, stored hashed in DB.
      - Rotate on every refresh:
        - revoke old token, create new token, link with `replaced_by_token_id`.
      - Detect reuse:
        - if a revoked token is used again → revoke entire token family for that user (log audit).
  - **Verify**:
    - tests: refresh rotates, revoked refresh fails, reuse triggers family revoke.

---

### API endpoints

- [ ] T099 Build FastAPI `/api/auth/register` + `/api/auth/me`
  - **Touch**:
    - `api/routes/auth.py` (new or expand)
    - `api/main.py` (router include)
    - `api/deps/auth.py` (new dependency: current_user)
    - `react-app/src/pages/Register.jsx` (if exists; wire)
  - **How**:
    - Register:
      - validate email/password
      - create user (email lowercased)
      - emit audit event `user.register`
      - issue auth response (either tokens immediately or require verify first)
    - Me:
      - requires access token
      - returns user profile fields used by UI.
  - **Verify**: `GET /api/auth/me` returns 401 without token, 200 with token.

- [ ] T100 Build FastAPI login/logout/refresh endpoints (token-based auth)
  - **Touch**:
    - `api/routes/auth.py`
    - `api/services/auth_service.py`
    - `react-app/src/services/auth.js` (ensure refresh logic)
    - `react-app/src/providers/AuthProvider.jsx` (if used)
  - **How**:
    - Login:
      - verify password
      - create refresh token row + access JWT
      - return tokens (and optionally set refresh as httpOnly cookie)
      - audit `user.login`
    - Logout:
      - revoke refresh token (current session) + audit
    - Refresh:
      - validate refresh token hash exists and not revoked/expired
      - rotate token + return new access and refresh
  - **Verify**:
    - Integration: login → refresh → old refresh fails → logout prevents future refresh.

---

### Email verification + password reset (FastAPI-owned)

- [ ] T101 Implement FastAPI email sending abstraction (Celery task) + local outbox
  - **Touch**:
    - `api/tasks/email_tasks.py` (new Celery tasks)
    - `api/services/email_service.py` (new)
    - `api/models/email_outbox.py` (optional local outbox table)
    - `api/celery_app.py` (ensure autodiscover)
    - `local.docker.yml` (worker imports api app)
    - `docs/STACK.md` (how to inspect local emails)
  - **How**:
    - Same pattern as Django variant, but owned in `api/`.
    - If SMTP/provider config missing → write to outbox and log.
  - **Verify**:
    - tests: sending creates outbox row; worker marks sent.

- [ ] T102 Implement FastAPI verify-email issuance + verify endpoint
  - **Touch**:
    - `api/routes/auth.py`
    - `api/models/one_time_tokens.py`
    - `api/services/token_service.py`
    - `react-app/src/pages/VerifyEmail.jsx`
  - **How**:
    - On register (or explicit resend):
      - create `one_time_tokens` row type `verify_email`, hashed token, expiry
      - send email with link containing raw token
    - Verify endpoint:
      - accept token
      - lookup by hash; ensure not expired/consumed
      - set `users.is_email_verified=true`
      - mark token consumed; audit `user.verify_email`
  - **Verify**: verify consumes token (second use fails).

- [ ] T103 Implement FastAPI forgot-password + reset-password endpoints (enumeration-safe)
  - **Touch**:
    - `api/routes/auth.py`
    - `api/models/one_time_tokens.py`
    - `api/services/auth_service.py`
    - `react-app/src/pages/ForgotPassword.jsx`
    - `react-app/src/pages/ResetPassword.jsx`
    - `docs/SECURITY.md`
  - **How**:
    - Forgot:
      - Always return 200 “If account exists…”
      - If user exists → create reset token + send email
      - Rate limit by IP + email hash (see T106)
    - Reset:
      - validate token, expiry, one-time use
      - update password hash
      - revoke all refresh tokens for user (force re-login)
      - audit `user.reset_password`
  - **Verify**: old refresh tokens stop working after reset.

---

### OAuth (Google) + session linkage

- [ ] T104 Implement Google OAuth login in FastAPI (`/api/auth/oauth/google`)
  - **Touch**:
    - `api/routes/oauth.py` (new or inside auth)
    - `api/services/oauth_google.py` (new)
    - `api/settings.py` (GOOGLE_CLIENT_ID)
    - `react-app/src/pages/Login.jsx` (wire to endpoint)
  - **How**:
    - Frontend obtains credential (ID token) from Google Sign-In.
    - Backend verifies ID token:
      - validate signature and audience matches your client id
      - extract email + sub
    - If user exists:
      - link provider if not linked
      - login (issue tokens)
    - If user does not exist:
      - create user with `is_email_verified=true` (if Google email is verified) and link provider
  - **Verify**: unit test by mocking verifier; integration in staging with real credentials.

- [ ] T105 Add provider linking table + account merge rules
  - **Touch**:
    - `api/models/oauth_accounts.py` (new)
    - `api/services/oauth_google.py`
    - `docs/SECURITY.md` (merge policy)
  - **How**:
    - Table: `oauth_accounts(user_id, provider, provider_sub, email_at_provider, created_at)`
    - Merge policy: if email matches an existing local account, only allow linking if user proves control (already logged in or email verified).
  - **Verify**: attempts to link provider to a different user are rejected and audited.

---

### Security hardening around auth

- [ ] T106 Add rate limiting for auth endpoints (login, register, forgot-password, oauth)
  - **Touch**:
    - `api/middleware/rate_limit.py` (new) OR integrate an existing limiter
    - `api/main.py` (middleware)
    - `redis` (reuse existing) for counters
    - `docs/SECURITY.md` (document limits)
  - **How**:
    - Simple token-bucket or fixed-window counters in Redis keyed by:
      - `ip:<ip>:login`
      - `email:<sha256(email)>:forgot`
    - Return 429 with `Retry-After`.
  - **Verify**: test that 6th login attempt in a minute returns 429.

- [ ] T107 Add secure cookie mode option (optional) for refresh token storage
  - **Touch**:
    - `api/routes/auth.py`
    - `api/settings.py`
    - `react-app/src/services/auth.js` (if switching from localStorage)
    - `traefik/dynamic.yml` (ensure `Secure` works behind TLS)
  - **How**:
    - If `AUTH_REFRESH_COOKIE=true`:
      - set refresh token as `httpOnly; Secure; SameSite=Lax` cookie
      - access token stays in memory (or returned in JSON)
    - Keep a non-cookie fallback for local dev.
  - **Verify**: refresh works with cookies; no JS access to refresh cookie.

- [ ] T108 Add audit event emission for all auth actions (login, logout, refresh, reset, verify)
  - **Touch**:
    - `api/services/audit_service.py`
    - `api/routes/auth.py`
    - `api/routes/oauth.py`
  - **How**:
    - Log: actor user_id (if any), action, ip, user_agent, metadata (no secrets).
  - **Verify**: `audit_events` rows appear on flows.

---

### Frontend alignment + removal of Django auth proxy (if present)

- [ ] T109 Update React auth client to match Option A tokens/cookies and remove any `/users/*` proxy assumptions
  - **Touch**:
    - `react-app/src/services/auth.js`
    - `react-app/src/services/api.js`
    - `react-app/src/providers/AuthProvider.jsx`
    - `react-app/src/pages/*` (login/register/verify/forgot/reset)
  - **How**:
    - Ensure:
      - token storage strategy consistent (memory + refresh cookie, or localStorage + refresh endpoint)
      - automatic refresh on 401 (single-flight refresh, queue concurrent requests)
      - logout clears state and revokes refresh.
  - **Verify**: E2E happy path: register → verify → login → settings → logout.

- [ ] T110 Decommission Django auth routes (if any exist) and clearly scope Django to admin/schema only
  - **Touch**:
    - `django/users/api_views.py` (remove or restrict)
    - `django/users/api_urls.py`
    - `traefik/dynamic.yml` (ensure no public auth routes point at Django)
    - `docs/STACK.md`
  - **How**:
    - If Django must keep admin:
      - guard it with allowlist/basic-auth middleware already present.
    - Ensure only FastAPI serves `/api/auth/*`.
  - **Verify**: `curl https://<domain>/api/auth/me` hits FastAPI; Django does not expose auth externally.

---
---

## Phase 15: Developer Experience + Local Productivity

**Purpose**: Make it easy for a new dev to clone → run → test → deploy without tribal knowledge.

- [ ] T111 Add a single top-level `Makefile` (or `justfile`) to standardize commands across OSes.
  - **Touch**:
    - `Makefile` (new) OR `justfile` (new)
    - `README.md` (replace long command sequences with `make <target>`)
  - **How**:
    - Targets (minimum):
      - `make up` / `make down`
      - `make logs` (all) + `make logs-api` / `make logs-web`
      - `make test` (runs backend+frontend)
      - `make fmt` (ruff format, prettier)
      - `make lint`
      - `make migrate` (runs migrations in the correct owner service)
      - `make seed`
      - `make reset` (danger: wipe volumes; require `CONFIRM=1`)
    - On Windows, either document `just` or provide `scripts/*.ps1` wrappers that call the same docker compose commands.
  - **Verify**: Fresh clone can run `make up` and reach `/` and `/api/health`.

- [ ] T112 Add `.env.example` completeness pass + env validation at startup.
  - **Touch**:
    - `.env.example`
    - `api/settings.py`
    - `django/project/settings/*.py` (if Django kept)
    - `docs/CONFIG.md` (new)
  - **How**:
    - Include all required keys:
      - DB url, Redis url
      - JWT secret + pepper
      - token TTLs
      - Google client id
      - SMTP/provider keys
      - `ENV` / `DEBUG` flags
    - Add startup-time checks that fail fast with human-readable error if required envs are missing (only in non-local).
  - **Verify**: Removing required env produces clear startup error.

- [ ] T113 Add local seed data command for dev and demo.
  - **Touch**:
    - `api/scripts/seed.py` (new)
    - `api/Dockerfile` (ensure script can run)
    - `README.md`
  - **How**:
    - Seed creates:
      - Admin user (email from env `SEED_ADMIN_EMAIL`, password from `SEED_ADMIN_PASSWORD`)
      - A few standard users
      - Example audit events
    - Make it idempotent (safe to run multiple times).
  - **Verify**: After `make seed`, you can login with seeded user.

---

## Phase 16: Frontend Polish (UX, Accessibility, Quality)

**Purpose**: Make the React app feel “shippable”: robust forms, error states, a11y, performance.

- [ ] T114 Add a unified form + API error handling pattern (toasts + field errors).
  - **Touch**:
    - `react-app/src/components/ToastProvider.jsx` (new if missing)
    - `react-app/src/services/api.js`
    - `react-app/src/pages/*` (login/register/reset/etc)
  - **How**:
    - Standardize server error shape: `{ code, message, fields?: {field: msg} }`
    - API layer maps HTTP errors into this shape.
    - Forms display:
      - inline field errors
      - top-level banner for non-field errors
      - disabled submit + spinner while pending
  - **Verify**: Bad password shows field error; server down shows friendly message.

- [ ] T115 Add route-level guards + redirect memory (return user to original page after login).
  - **Touch**:
    - `react-app/src/routes/PrivateRoute.jsx` (new)
    - `react-app/src/providers/AuthProvider.jsx`
    - `react-app/src/App.js`
  - **How**:
    - If user not authenticated, redirect to `/login?next=/target`.
    - After login, navigate to `next`.
  - **Verify**: Visiting a protected route sends to login then returns.

- [ ] T116 Improve accessibility baseline (keyboard nav, focus, aria).
  - **Touch**:
    - `react-app/src/components/*`
    - `react-app/src/pages/*`
  - **How**:
    - Ensure modals trap focus
    - Buttons have aria labels where needed
    - Error messages linked to inputs (`aria-describedby`)
    - Visible focus ring
  - **Verify**: Basic keyboard-only pass.

- [ ] T117 Add production build performance checklist (bundle size + lazy routes).
  - **Touch**:
    - `react-app/src/App.js` (code splitting)
    - `react-app/package.json` (analyze script)
  - **How**:
    - Lazy-load auth pages and heavy settings pages.
    - Add `npm run analyze` (e.g., source-map-explorer) and document budgets.
  - **Verify**: Build passes and main bundle size drops.

---

## Phase 17: End-to-End Tests + QA Automation

**Purpose**: Prevent regressions on auth flows and deployments.

- [ ] T118 Add E2E test harness (Playwright recommended) for core flows.
  - **Touch**:
    - `e2e/` (new)
    - `package.json` (workspace or root scripts)
    - `.github/workflows/ci-e2e.yml` (new)
  - **How**:
    - Tests (minimum):
      - register → verify (or mock) → login → me → logout
      - forgot → reset → login with new password
      - refresh token rotation scenario
    - In CI:
      - `docker compose up -d`
      - wait for health
      - run playwright against `http://localhost`
  - **Verify**: CI green.

- [ ] T119 Add smoke tests to droplet deploy script (post-deploy checks with rollback hook).
  - **Touch**:
    - `digital_ocean/scripts/powershell/deploy.ps1`
    - `digital_ocean/scripts/powershell/test.ps1`
  - **How**:
    - After deploy:
      - check `/` returns 200
      - `/api/health` returns 200
      - `/api/auth/me` returns 401 (expected unauth)
      - TLS cert valid and not staging in prod
    - If any fails: stop update and print actionable output.
  - **Verify**: `deploy.ps1 -UpdateOnly -AllTests` catches breakage.

---

## Phase 18: Security Hardening (Beyond basics)

**Purpose**: Reduce risk from common web attacks and operational mistakes.

- [ ] T120 Add CORS policy + CSRF posture documentation (token vs cookie modes).
  - **Touch**:
    - `api/main.py` (CORS middleware)
    - `docs/SECURITY.md`
  - **How**:
    - If using refresh cookies:
      - CORS allow only your domains
      - ensure `SameSite=Lax` and require POST for state changes
    - If using Authorization headers only:
      - CORS still strict, but CSRF risk is reduced
  - **Verify**: Browser calls from non-allowed origins fail.

- [ ] T121 Add password policy + account lockout/throttling rules.
  - **Touch**:
    - `api/services/auth_service.py`
    - `api/models/users.py` (track failed attempts, lock until)
    - `api/routes/auth.py`
  - **How**:
    - Password rules (example):
      - length >= 12 (or >= 10 with complexity)
    - Lockout:
      - after N failures, lock for X minutes (also rate-limit by IP)
    - Always return generic “invalid credentials”.
  - **Verify**: repeated failures trigger lock; audit logs record it.

- [ ] T122 Add secrets scanning + dependency scanning in CI.
  - **Touch**:
    - `.github/workflows/security.yml` (new)
  - **How**:
    - Add secret scan (gitleaks or GitHub Advanced Security if available)
    - Add dependency audit:
      - `npm audit --production` (or equivalent)
      - `pip-audit` for Python
  - **Verify**: CI flags known vulnerable deps.

---

## Phase 19: Observability 2.0 (Tracing + Dashboards)

**Purpose**: Make incidents diagnosable in minutes, not hours.

- [ ] T123 Add OpenTelemetry tracing hooks (start with FastAPI) + propagate trace headers.
  - **Touch**:
    - `api/otel.py` (new)
    - `api/main.py`
    - `traefik` config (ensure it forwards trace headers)
    - `docs/OBSERVABILITY.md` (new)
  - **How**:
    - Instrument FastAPI with OTEL middleware.
    - Include DB spans (SQLAlchemy if adopted).
    - Exporter:
      - local: console
      - staging/prod: OTLP endpoint (Tempo/Jaeger).
  - **Verify**: request generates a trace with spans.

- [ ] T124 Add a “golden signals” dashboard checklist (latency, errors, traffic, saturation).
  - **Touch**:
    - `docs/OBSERVABILITY.md`
    - `meta/dashboards/*` (optional JSON exports)
  - **How**:
    - Define SLO-ish targets (even informal):
      - p95 latency for auth endpoints
      - error rate
    - Document alert conditions and runbooks.
  - **Verify**: docs exist and are referenced from README.

---

## Phase 20: API & Product Niceties

**Purpose**: Provide a few “this feels finished” features that users expect.

- [ ] T125 Add `/api/auth/sessions` endpoint + UI for “log out other devices”.
  - **Touch**:
    - `api/routes/auth.py`
    - `api/models/refresh_tokens.py`
    - `react-app/src/pages/Settings.jsx`
  - **How**:
    - Endpoint lists active refresh token sessions with:
      - created_at, last_seen_at (update on refresh), user_agent, ip (masked)
    - Endpoint to revoke all except current.
  - **Verify**: other device refresh stops working after revoke.

- [ ] T126 Add user profile update endpoint (`PATCH /api/users/me`) + UI wiring.
  - **Touch**:
    - `api/routes/users.py` (new)
    - `api/models/users.py`
    - `react-app/src/pages/Settings.jsx`
  - **How**:
    - allow updating display name and optionally email (if you support email change, require re-verify)
  - **Verify**: UI updates and persists.

- [ ] T127 Add feature flags support (simple env-driven, later DB-driven).
  - **Touch**:
    - `api/flags.py` (new)
    - `react-app/src/flags.js` (new)
    - `docs/CONFIG.md`
  - **How**:
    - Start with env flags in backend and build-time flags in frontend.
    - Provide `/api/flags` if you want runtime toggles.
  - **Verify**: toggling a flag changes UI/API behavior predictably.

---
