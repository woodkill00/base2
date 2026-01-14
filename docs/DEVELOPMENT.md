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

## Tailwind Usage Policy

- Utilities allowed where already present; do not remove or replace Tailwind.
- No global overrides; keep styles component-scoped and use CSS variables/tokens.
- No new Tailwind plugins; keep config unchanged.

## Style Guard (Glass Feature)

Run a simple guard to detect forbidden global overrides or `!important` usage in glass styles:

```bash
node react-app/scripts/style_guard.js
```

The guard checks `react-app/src/styles` and `react-app/src/components/glass` for:

- Global selectors (`html`, `body`, `:root`, `.dark`) outside of `tokens.css`
- `!important` usage

If violations are found, the script exits non-zero and lists offending files/lines.

## OpenAPI Types Generation

Generate frontend TypeScript types from the OpenAPI contract:

```bash
cd react-app
npm run generate:openapi:types
```

## Design Integration & Attributions

- Design bundle in c:\Users\theju\Documents\coding\website_build\base2\junk\idea\; see additional tasks in c:\Users\theju\Documents\coding\website_build\base2\specs\002-react-design\tasks.design-integration.md
- Components referenced from shadcn/ui are used under MIT license.
- Photos referenced from Unsplash are under Unsplash license; we do not ship raster images. Use vector assets (SVG/WebP) only.
