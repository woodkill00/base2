# Testing Guide

## Python environment boundaries

Do not invoke bare `pytest` from the repository root. The API, Django, provider, and visual tooling intentionally use different dependency environments; root discovery mixes them and produces misleading collection failures. Run API tests with `.venv-api/bin/pytest api/tests`, Django tests with `.venv-django/bin/pytest django/tests`, and repository Python/script tests with `.venv/bin/python -m pytest scripts/tests`. Cross-service PostgreSQL, Redis, Celery, and browser integration belongs to `scripts/bash/complete-gate.sh`, which provisions and validates the expected stack.

## Categories

- Unit: default fast tests (pytest.ini excludes integration/perf)
- Integration: require services (Postgres/Redis/Celery), marked `@pytest.mark.integration`
- Contract: OpenAPI/schema checks, marked `@pytest.mark.contract`
- E2E: Playwright browser tests (run from `react-app/`)

## All-in-one entrypoint

Run a full deploy verification + tests (DigitalOcean update-only):

`./digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests -Timestamped -LogsDir .\local_run_logs`

Artifacts land under `local_run_logs/<ip>-<timestamp>/` with per-service folders and a meta report.

## Official local test path (Docker-first)

Start the stack, then run tests through the wrappers:

- PowerShell: `./scripts/powershell/test.ps1`
- Bash/WSL: `./scripts/bash/test.sh`

These scripts expect Docker Compose to be running (use `./scripts/powershell/start.ps1` or `./scripts/bash/start.sh`). They run backend tests in containers and frontend tests locally.

## Backend

- API unit: `cd api && pytest -q`
- API integration: `cd api && pytest -q -m integration -o addopts=`
- Django unit: `cd django && pytest -q`
- Django integration: `cd django && pytest -q -m integration -o addopts=`

Coverage thresholds enforced in CI and deploy gate.

## Frontend

- Lint: `cd react-app && npm run lint`
- Tests: `cd react-app && npm run test:ci`
- E2E: `cd react-app && npm run e2e`

### Isolated fresh-volume E2E proof (WSL/Linux)

Use the bounded runner below when an existing Base2 stack must remain running.
It owns only the fixed `base2-e2e-isolated` Compose project, removes that exact
project and its volumes before starting, waits for API, test-support, and web
health, runs both real browser and API/auth journeys, and tears its project down
on success, failure, or interruption. It acquires a nonblocking local lock
before touching Docker, so concurrent invocations fail safely instead of
precleaning one another's disposable project.

```bash
scripts/bash/e2e-isolated.sh
```

The owner/contender and final empty-inventory contract is exercised with:

```bash
scripts/bash/e2e-isolated-concurrency-proof.sh
```

The runner defaults to loopback ports `15001`, `15002`, and `18080`. Optional
overrides use only `E2E_API_PORT`, `E2E_TEST_SUPPORT_PORT`, and `E2E_WEB_PORT`;
values must be distinct numeric unprivileged ports. Hosted CI retains defaults
`5001`, `5002`, and `8080`. API and web publication is loopback-only in both
cases. `E2E_WEB_ORIGIN` is derived by the runner, while browser API calls remain
same-origin and traverse the frontend container's fixed private-network `/api`
proxy. The browser, CORS policy, and tested services therefore stay in the same
isolated namespace without relaxing Content Security Policy.

Parallel visual reviewers must also select distinct loopback-only ports. The
release gate keeps the default `4174`; an independent review can use, for
example, `BASE2_VISUAL_PORT=4175 npm run test:visual`. The value is accepted
only when it is a numeric unprivileged TCP port from 1024 through 65535, the
preview remains bound to `127.0.0.1`, and existing servers are never reused.

### React Router v7 future flags (tests-only)

- Production: Router flags are configured in app code (see `react-app/src/App.js`).
- Tests: We suppress only the React Router "Future Flag Warning" messages in `react-app/src/setupTests.js` to keep CI output clean.
- Alternative (preferred in new tests): Wrap components with `TestRouter` from `react-app/src/test/TestRouter.jsx`, which sets `future={{ v7_startTransition: true, v7_relativeSplatPath: true }}`.
- Scope: This policy affects Jest tests only. Runtime builds and behavior remain unchanged.

### Frontend crash guard (placeholder check)

To prevent accidental placeholder artifacts from shipping (e.g. a standalone `...` line in a module), run:

`powershell -Command "Select-String -Path react-app/src/**/* -Pattern '^\s*\.\.\.\s*$' -List"`

This should return no matches.

## Contract

- Runtime OpenAPI vs contract: `cd api && pytest -q -m contract`

## Performance Smoke

- Script: `python scripts/python/perf_smoke.py` (env `PERF_BASE_URL`, `PERF_P95_BUDGET_MS`)

## Pre-commit

- Install: `pip install pre-commit && pre-commit install`
- Run: `pre-commit run --all-files`
