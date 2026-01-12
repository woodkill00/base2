# Testing Guide

## Categories

- Unit: default fast tests (`-m "not integration and not contract and not e2e"`)
- Integration: require services (Postgres/Redis/Celery), marked `@pytest.mark.integration`
- Contract: OpenAPI/schema checks, marked `@pytest.mark.contract`
- E2E: Playwright browser tests (run from `react-app/`)

## Backend

- API unit: `cd api && pytest -q -m "not integration"`
- API integration: `cd api && pytest -q -m integration`
- Django unit: `cd django && pytest -q -m "not integration"`

Coverage thresholds enforced in CI and deploy gate.

## Frontend

- Lint: `cd react-app && npm run lint`
- Tests: `cd react-app && npm run test:ci`
- E2E: `cd react-app && npm run e2e`

### React Router v7 future flags (tests-only)

- Production: Router flags are configured in app code (see `react-app/src/App.js`).
- Tests: We suppress only the React Router "Future Flag Warning" messages in `react-app/src/setupTests.js` to keep CI output clean.
- Alternative (preferred in new tests): Wrap components with `TestRouter` from `react-app/src/test/TestRouter.jsx`, which sets `future={{ v7_startTransition: true, v7_relativeSplatPath: true }}`.
- Scope: This policy affects Jest tests only. Runtime builds and behavior remain unchanged.

## Contract

- Runtime OpenAPI vs contract: `cd api && pytest -q -m contract`

## Performance Smoke

- Script: `python scripts/perf_smoke.py` (env `PERF_BASE_URL`, `PERF_P95_BUDGET_MS`)

## Pre-commit

- Install: `pip install pre-commit && pre-commit install`
- Run: `pre-commit run --all-files`
