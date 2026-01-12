# Deployment Guide

Authoritative deploy/update/test is executed via `digital_ocean/scripts/powershell/deploy.ps1`.

## Workflow Overview

- Commit code changes and ensure tests are green locally.
- Push to `origin/<branch>`.
- Set `.env` `DO_APP_BRANCH` to the branch you want the droplet to hard-reset to (usually `main`).
- Run UpdateOnly deploy with tests: `-UpdateOnly -AllTests -Timestamped`.
- Review artifacts under `local_run_logs/<ip>-<timestamp>/`.

## Modes

- Full deploy: `powershell -File digital_ocean/scripts/powershell/deploy.ps1 -Full -AllTests -Timestamped`
- Update-only: `powershell -File digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests -Timestamped`

Alias/Flag note: Recent runs used `-RunAllTests` which is equivalent to `-AllTests`.

## Flags Reference

- `-Full`: end-to-end resource provisioning path via orchestrator (droplet create, DNS, stack).
- `-UpdateOnly`: skip provisioning, hard-reset remote repo to `origin/$env:DO_APP_BRANCH`, rebuild core services.
- `-Preflight`: run preflight validators locally; deploy fails fast if validation fails.
- `-AllTests`: run all post-deploy tests (React Jest, Playwright E2E, API/Django pytest, smoke checks).
- `-RunTests`: run a subset of tests (omit E2E by default); use with `-TestsJson` for machine-readable output.
- `-TestsJson`: JSON output for test results; artifacts saved under `local_run_logs/.../meta`.
- `-Timestamped`: write artifacts to `local_run_logs/<ip>-<timestamp>/` instead of a generic folder.
- `-AsyncVerify`: return sooner after kicking off remote verification; artifacts may continue to populate.
- `-DropletIp <ip>`: override droplet IP detection.
- `-SshKey <path>`: specify SSH private key path.
- `-SkipAllowlist`: do not update IP allowlists in `.env` before deploy.
- `-VerifyTimeoutSec <sec>`: override remote verification timeout (default 1800).
- `-ReactTestTimeoutSec <sec>`: override local React test timeout (default 1800).

### When to use which

- Use `-UpdateOnly` for routine code changes already on the droplet; faster and safer.
- Use `-Full` when creating a new droplet or re-provisioning infrastructure.
- Always include `-AllTests` for CI-like gating unless experimenting locally.
- Use `-Timestamped` to keep runs isolated and auditable.

## Pre-Deploy Discipline (UpdateOnly)

- Commit and push runtime-impacting changes to `origin/<DO_APP_BRANCH>` before using `-UpdateOnly`.
- Ensure `.env` defines `DO_APP_BRANCH` for the droplet. The deploy script hard-resets the droplet repo to `origin/<DO_APP_BRANCH>`.
- Runtime-impacting changes include service code (`api/`, `django/`, `react-app/`), Dockerfiles, Compose files, and Traefik configs. Docs-only changes do not require a push.

Recommended: set `DO_APP_BRANCH=main` in `.env` for stable deployments.

## TLS Policy (Staging-Only)

- Traefik must use the Let’s Encrypt staging ACME directory (`le-staging`).
- Verification (`test.ps1`) fails if production issuance is detected.

### TLS Mode Guard (Hardening)

- Deploy verification also enforces:
  - ACME email is set (`TRAEFIK_CERT_EMAIL`)
  - ACME storage files are not world-readable
  - If the production Let's Encrypt directory is referenced, `ENV=prod` (or `BASE2_ENV=prod`) must be explicitly set

Flag interaction:

- In staging/non-prod, the stack uses Let's Encrypt staging (`le-staging`); tests expect browser warnings on TLS.
- In prod (`ENV=production`), use real ACME directory and ensure DNS/allowlists are correct; tests will enforce stricter checks.

## Artifacts

- Runs write artifacts to `local_run_logs/<droplet-ip>-<timestamp>/`.
- Post-deploy report: `meta/post-deploy-report.json`.

### Suggested Verification Flow (UpdateOnly)

- Run: `powershell -File digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -RunAllTests -Timestamped`
- Verify endpoints:
  - Traefik dashboard: https://traefik.${WEBSITE_DOMAIN}/ (basic-auth + allowlist)
  - Django admin: https://admin.${WEBSITE_DOMAIN}/admin/ (basic-auth + allowlist)
  - FastAPI Swagger UI: https://swagger.${WEBSITE_DOMAIN}/docs
- Review artifacts under `local_run_logs/<droplet-ip>-<timestamp>/` for jest, Playwright, and API/Django pytest outputs.

Artifacts map:

- `meta/post-deploy-report.json`: consolidated outcome and timings.
- `docker/*`: compose ps/config/ports.
- `traefik/*`: static/dynamic configs and logs.
- `api/*`, `django/*`: service-specific logs and health outputs.
- `react-app/*`: jest/e2e outputs.

## Troubleshooting

- If UpdateOnly changes don’t reflect on the droplet, verify a recent push to `origin/<DO_APP_BRANCH>`.
- For DNS allowlists, the script updates `.env` with your public IP; restart Traefik if needed.

Test warnings:

- React Router v7 "Future Flag Warning" messages are suppressed in Jest only; see `docs/TESTING.md` for policy and the `TestRouter` helper.

## Migration Safety (CI)

CI enforces Django migration safety by failing if model changes are detected without migrations.
Run locally before PRs:

```
cd django
python manage.py makemigrations --check --dry-run
```

## Hostnames (Dev-Production)

- Main site: `https://${WEBSITE_DOMAIN}/`
- API: `https://${WEBSITE_DOMAIN}/api/*`
- Django admin: `https://admin.${WEBSITE_DOMAIN}/admin/` (guarded by Traefik basic-auth + IP allowlist)
- FastAPI Swagger UI: `https://swagger.${WEBSITE_DOMAIN}/docs` (docs-only host; routed to FastAPI)

## Container Runtime Hardening

`local.docker.yml` applies defense-in-depth settings where feasible:

- `cap_drop: [ALL]`
- `security_opt: [no-new-privileges:true]`
- `read_only: true` for stateless services, with `tmpfs` mounts for writable paths like `/tmp`
