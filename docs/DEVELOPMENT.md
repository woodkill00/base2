# Development Guide

## Tool Versions

- Python: 3.12 (see .python-version)
- Node.js: 18.x (see react-app/.nvmrc)

## Pre-commit Hooks

Pre-commit runs formatting and lint checks before commits.

### Install

```
pip install pre-commit
pre-commit install
```

### Run manually

```
pre-commit run --all-files
```

### Hooks

- Ruff (lint + format) for Python (api/, django/)
- Prettier for React app (react-app/)
- Basic hygiene: YAML check, trailing whitespace, end-of-file fixes

## Running Tests

- Deploy/test entrypoint: digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests -Timestamped
- React Jest: runs automatically via deploy script; see local_run_logs/<run>/react-app/jest.txt
- Playwright E2E: runs via deploy script; artifacts under local_run_logs/<run>/react-app/playwright/
- API/Django Pytest: runs inside containers; outputs under local_run_logs/<run>/(api|django)/

## Storybook

Run Storybook locally:

```bash
cd react-app
npm run storybook
```

Build Storybook (CI also builds this):

```bash
cd react-app
npm run build-storybook
```

## OpenAPI Types Generation

Generate frontend TypeScript types from the OpenAPI contract:

```bash
cd react-app
npm run generate:openapi:types
```
