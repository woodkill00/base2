# Deployment Guide

Authoritative deploy/update/test is executed via `digital_ocean/scripts/powershell/deploy.ps1`.

## Modes

- Full deploy: `powershell -File digital_ocean/scripts/powershell/deploy.ps1 -Full -AllTests -Timestamped`
- Update-only: `powershell -File digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests -Timestamped`

## Pre-Deploy Discipline (UpdateOnly)

- Commit and push runtime-impacting changes to `origin/<DO_APP_BRANCH>` before using `-UpdateOnly`.
- Ensure `.env` defines `DO_APP_BRANCH` for the droplet. The deploy script hard-resets the droplet repo to `origin/<DO_APP_BRANCH>`.
- Runtime-impacting changes include service code (`api/`, `django/`, `react-app/`), Dockerfiles, Compose files, and Traefik configs. Docs-only changes do not require a push.

## TLS Policy (Staging-Only)

- Traefik must use the Let’s Encrypt staging ACME directory (`le-staging`).
- Verification (`test.ps1`) fails if production issuance is detected.

### TLS Mode Guard (Hardening)

- Deploy verification also enforces:
  - ACME email is set (`TRAEFIK_CERT_EMAIL`)
  - ACME storage files are not world-readable
  - If the production Let's Encrypt directory is referenced, `ENV=prod` (or `BASE2_ENV=prod`) must be explicitly set

## Artifacts

- Runs write artifacts to `local_run_logs/<droplet-ip>-<timestamp>/`.
- Post-deploy report: `meta/post-deploy-report.json`.

## Troubleshooting

- If UpdateOnly changes don’t reflect on the droplet, verify a recent push to `origin/<DO_APP_BRANCH>`.
- For DNS allowlists, the script updates `.env` with your public IP; restart Traefik if needed.

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
