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
- [ ] T003 [P] Create docs/DEPLOY.md documenting “deploy.ps1 is authoritative” and staging-only ACME policy ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
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

- [ ] T025 [P] [US1] Add contract-vs-runtime OpenAPI path check in digital_ocean/scripts/powershell/test.ps1 by parsing specs/001-django-fastapi-react/contracts/openapi.yaml `paths:` keys and verifying they exist in fetched api/openapi.json (write api/openapi-contract-check.json) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T026 [P] [US1] Add guarded endpoint probes in digital_ocean/scripts/powershell/test.ps1 for unauthenticated access (e.g., /api/users/me, /api/users/logout) and write meta/guarded-endpoints.json ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T027 [P] [US1] Add an artifact completeness check in digital_ocean/scripts/powershell/test.ps1 (assert key artifacts exist: openapi.json, openapi-validation.json, schema-compat-check.json, post-deploy-report.json) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests

### Implementation for User Story 1

- [ ] T028 [US1] Ensure post-deploy report schema includes new check blocks (openApiContractCheck, guardedEndpointsCheck, artifactCompletenessCheck) in digital_ocean/scripts/powershell/test.ps1 ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T029 [US1] Align specs/001-django-fastapi-react/contracts/openapi.yaml with actual external routes (only change if real implementation differs) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T030 [US1] Expand specs/001-django-fastapi-react/quickstart.md with artifact locations and “how to interpret” guidance for meta/post-deploy-report.json ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests

**Checkpoint**: At this point, US1 is independently verifiable and becomes the deployment safety net for all later stories

---

## Phase 4: User Story 2 - Signup and login/logout (Priority: P2)

**Goal**: Visitor can sign up, log in, log out securely with cookie auth; rate limiting and enumeration resistance are enforced; CSRF blocks state-changing calls without token.

**Independent Test**: `digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests` runs Django + FastAPI + React tests covering signup/login/logout, and post-deploy probes confirm protected endpoints deny unauthenticated access.

### Tests for User Story 2 (write first) ⚠️

- [ ] T031 [P] [US2] Add Django tests for internal auth API in django/tests/test_auth_api.py (signup, login, logout, me; duplicate email; generic errors; CSRF rejection) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T032 [P] [US2] Add Django tests for audit events in django/tests/test_audit_events.py (login failure/success actions recorded; secrets not in metadata) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T033 [P] [US2] Add FastAPI proxy tests in api/tests/test_auth_proxy.py (cookie forwarding; header forwarding; error mapping; 429 passthrough) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T034 [P] [US2] Add FastAPI rate limit tests in api/tests/test_rate_limit.py (Redis counter increments; 429 returns {detail}) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests

### Implementation for User Story 2 (Django internal endpoints)

- [ ] T035 [US2] Implement internal JSON auth views in django/users/api_views.py (signup/login/logout/me/profile patch) using Django auth + sessions ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T036 [US2] Add internal routes in django/users/api_urls.py and mount under /internal/api in django/project/urls.py ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T037 [US2] Implement CSRF bootstrap view in django/users/api_views.py (ensures CSRF cookie is set; returns `{detail}` or token info) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T038 [US2] Ensure UserProfile auto-creation on signup in django/users/models.py or django/users/signals.py (if not already present) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T039 [US2] Emit AuditEvent records for auth actions in django/users/api_views.py using django/users/models.py::AuditEvent ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests

### Implementation for User Story 2 (FastAPI external surface)

- [ ] T040 [US2] Create Django proxy client in api/clients/django_client.py (base URL from api/settings.py; forwards cookies + CSRF header; timeout; error mapping) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T041 [US2] Implement external auth routes in api/routes/auth.py for /users/signup, /users/login, /users/logout and include router in api/main.py ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T042 [US2] Implement external current-user routes in api/routes/users.py for /users/me (GET + PATCH) and include router in api/main.py ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T043 [US2] Apply app-level rate limiting to external signup/login in api/routes/auth.py using api/security/rate_limit.py ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T044 [US2] Update FastAPI OpenAPI metadata in api/main.py (title/version) to remain compatible with specs/001-django-fastapi-react/contracts/openapi.yaml ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests

### React minimal auth UI (US2 scope)

- [ ] T045 [P] [US2] Add React tests for login/logout UI in react-app/src/__tests__/auth.test.js (successful login sets authenticated state; logout clears it) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T046 [US2] Implement Login page in react-app/src/pages/Login.jsx (email/password form; calls POST /api/users/login with credentials) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T047 [US2] Implement Signup page in react-app/src/pages/Signup.jsx (email/password; calls POST /api/users/signup) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T048 [US2] Wire routes for /login and /signup in react-app/src/App.js ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests

**Checkpoint**: At this point, a user can sign up, sign in, sign out, and the session cookie auth works end-to-end

---

## Phase 5: User Story 3 - Dashboard and settings (Priority: P3)

**Goal**: Signed-in user sees dashboard and can update profile settings; session expiry redirects to login with friendly messaging.

**Independent Test**: `digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests` passes React tests for protected routes and API tests for profile update; manual staging smoke shows dashboard loads behind auth.

### Tests for User Story 3 (write first) ⚠️

- [ ] T049 [P] [US3] Add React tests for protected route gating in react-app/src/__tests__/protected-route.test.js ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T050 [P] [US3] Add React tests for dashboard render in react-app/src/__tests__/dashboard.test.js ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T051 [P] [US3] Add React tests for settings update form in react-app/src/__tests__/settings.test.js ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T052 [P] [US3] Add API integration tests for PATCH /api/users/me allowed fields in api/tests/test_profile_update.py ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests

### Implementation for User Story 3 (React)

- [ ] T053 [US3] Create ProtectedRoute component in react-app/src/components/ProtectedRoute.jsx (redirect to /login on 401/unauthenticated) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T054 [US3] Create auth hook in react-app/src/hooks/useAuth.js (loads current user via GET /api/users/me; exposes loading/authenticated/user) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T055 [US3] Create axios wrapper in react-app/src/lib/apiClient.js (withCredentials; attaches X-CSRF-Token when present) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T056 [US3] Implement Dashboard page in react-app/src/pages/Dashboard.jsx (renders email + basic metadata) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T057 [US3] Implement Settings page in react-app/src/pages/Settings.jsx (edit display_name/avatar_url/bio; calls PATCH /api/users/me) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T058 [US3] Wire routes for /dashboard and /settings in react-app/src/App.js using ProtectedRoute ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests

**Checkpoint**: At this point, dashboard + profile update flows are independently testable

---

## Phase 6: User Story 4 - Sign in with Google (Priority: P4)

**Goal**: User can sign in with Google via Authorization Code flow and end in an authenticated cookie session; failures are safe and non-sensitive.

**Independent Test**: `digital_ocean/scripts/powershell/deploy.ps1 -AllTests` passes backend unit tests for OAuth state/redirect validation and React tests for OAuth button + callback handling.

### Tests for User Story 4 (write first) ⚠️

- [ ] T059 [P] [US4] Add Django tests for OAuth start/callback in django/tests/test_oauth_google.py (state validation; allowlist; cancel/fail paths; account link) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T060 [P] [US4] Add FastAPI proxy tests for OAuth routes in api/tests/test_oauth_proxy.py ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T061 [P] [US4] Add React tests for OAuth start + callback UX in react-app/src/__tests__/oauth.test.js ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests

### Implementation for User Story 4 (Django + FastAPI + React)

- [ ] T062 [US4] Document required Google OAuth env vars in specs/001-django-fastapi-react/quickstart.md (client id/secret/redirect; state secret) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T063 [US4] Ensure OAuthAccount uniqueness constraints align with data-model.md in django/users/models.py (add migration if missing) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T064 [US4] Implement internal OAuth views in django/users/api_views.py (start → auth URL; callback → exchange code; link/create user; create session; audit event) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T065 [US4] Implement external OAuth proxy routes in api/routes/oauth.py (/oauth/google/start and /oauth/google/callback) and include router in api/main.py ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T066 [US4] Add Login page “Sign in with Google” button in react-app/src/pages/Login.jsx (calls POST /api/oauth/google/start then redirects) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T067 [US4] Add OAuth callback page in react-app/src/pages/OAuthCallback.jsx (reads code/state; calls POST /api/oauth/google/callback; redirects to /dashboard; safe error display) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T068 [US4] Wire /oauth/google/callback route in react-app/src/App.js ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests

**Checkpoint**: At this point, OAuth login works end-to-end (or is safely failing with tests proving failure handling)

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T069 [P] Update docs/SECURITY.md to include rate limiting policies (Traefik + app-level) and enumeration-safe error guidance ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T070 [P] Add “quickstart validation checklist” to specs/001-django-fastapi-react/quickstart.md (URLs + artifact files + expected report keys) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T071 [P] Add a note to .specify/scripts/bash/common.sh about Git Bash vs WSL path differences on Windows and recommend Git Bash for prereq checks ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T072 Resolve Spec-Kit numeric-prefix ambiguity by renumbering any conflicting spec directory and updating README.md links (optional, only if another 001-* directory exists) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests

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

- [ ] T073 [P] [US1] Add explicit staging-only TLS guard verification in digital_ocean/scripts/powershell/test.ps1 (assert ACME uses staging directory; fail if production issuance is configured; write meta/tls-acme-guard.json) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T074 [P] [US1] Add health timing probe in digital_ocean/scripts/powershell/test.ps1 (sample N requests to /api/health; compute p95; enforce SC-002 p95 < 5s; write meta/health-timings.json) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T075 [P] [US1] Add login timing probe in digital_ocean/scripts/powershell/test.ps1 (sample N logins under “normal conditions”; enforce SC-004 99% < 2s; write meta/login-timings.json) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T076 [P] [US1] Add signup-to-dashboard timing probe in digital_ocean/scripts/powershell/test.ps1 (script signup + auth confirmation via /api/users/me; optionally fetch a protected page; enforce SC-003 < 2 minutes; write meta/signup-to-dashboard-timings.json) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
- [ ] T077 [P] [US1] Add health response contract-shape check in digital_ocean/scripts/powershell/test.ps1 (assert /api/health JSON fields minimally: ok/service/db_ok; write meta/health-contract-check.json) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests

### Make AllTests prefer UpdateOnly when possible

- [ ] T078 [US1] Update digital_ocean/scripts/powershell/deploy.ps1 so `-AllTests` prefers `-UpdateOnly` automatically when an existing droplet/environment can be resolved and `-Full` was not requested (fallback to full deploy only when needed; log the chosen mode into artifacts) ; Verify: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests
