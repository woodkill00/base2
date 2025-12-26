# Quickstart (Phase 1): Full-stack Baseline

This quickstart is for running and verifying the full stack using the repo’s standard topology and scripts.

## Prerequisites

- Docker Desktop (or Docker Engine) with Compose support
- PowerShell 5.1 (Windows) for deploy/test automation
- Bash (Git Bash or WSL) for local helper scripts
- A domain configured for staging-like verification (recommended for TLS flows)

## Local (Compose-first)

1) Create environment file:
- Copy `.env.example` to `.env`
- Set at minimum:
  - `WEBSITE_DOMAIN`
  - `TRAEFIK_CERT_EMAIL`
  - allowlists (`DJANGO_ADMIN_ALLOWLIST`, `PGADMIN_ALLOWLIST`, `FLOWER_ALLOWLIST`) to your public IP/CIDR

2) Start the stack:
- From repo root: `bash scripts/start.sh --build`

3) Verify health (staging-like expectation):
- Web UI: `https://$WEBSITE_DOMAIN/`
- API health: `https://$WEBSITE_DOMAIN/api/health`

Email (local outbox fallback):
- If SMTP is not configured (for example, `EMAIL_HOST` is empty), outbound emails are written to the Django `EmailOutbox` table instead of being sent.
- To inspect queued emails, use Django Admin (`https://admin.$WEBSITE_DOMAIN/admin`) and view the EmailOutbox entries.

Notes:
- The Traefik config enforces HTTPS and uses the Let’s Encrypt **staging** ACME directory. For fully offline/local domains that are not publicly resolvable, certificate issuance may not succeed; the staging-like verification path is designed for the droplet environment.

## Google OAuth (US4)

To enable “Sign in with Google”, set these env vars (see `.env.example`):

- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`
- `GOOGLE_OAUTH_REDIRECT_URI` (must match the SPA callback route, typically `https://$WEBSITE_DOMAIN/oauth/google/callback`)
- `OAUTH_STATE_SECRET` (HMAC secret used to sign/validate OAuth state)

## Staging-like deployment (authoritative)

Deploy/update/test MUST be executed via the single entrypoint:

- Full deploy + all tests:
  - `powershell -File digital_ocean/scripts/powershell/deploy.ps1 -Full -AllTests -Timestamped`

Artifacts:
- Deploy/test runs write artifacts under `local_run_logs/<droplet-ip>-<timestamp>/`.
- The post-deploy JSON report is stored at `local_run_logs/<run>/meta/post-deploy-report.json`.

Key artifacts to inspect:
- Report summary: `meta/post-deploy-report.json`
- OpenAPI runtime: `api/openapi.json`
- OpenAPI basic validation: `api/openapi-validation.json`
- OpenAPI contract alignment: `api/openapi-contract-check.json`
- Guarded endpoint probes: `meta/guarded-endpoints.json`
- Artifact completeness: `meta/artifact-completeness.json`
- DB schema compatibility: `database/schema-compat-check.json`

How to interpret `meta/post-deploy-report.json`:
- `success=true` means no failures, no missing files, and staging TLS resolver checks passed.
- `failures` lists human-readable failures (including contract mismatches and guarded endpoint violations).
- `openApiContractCheck.missingPaths` shows contract paths that are not present in runtime OpenAPI.
- `guardedEndpointsCheck.endpoints[]` records status codes for unauthenticated probes.
- `artifactCompletenessCheck.missing` lists required artifacts that were not found.

## Quickstart validation checklist

- Run: `powershell -File digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests -Timestamped`
- Confirm `meta/post-deploy-report.json` exists for the run
- Confirm `success=true` and `failures` is empty
- Confirm `stagingResolverOK=true` and `tlsCheck.ok=true`
- Confirm `openApiContractCheck.ok=true` and `missingPaths` is empty
- Confirm `guardedEndpointsCheck.ok=true` (unauthenticated probes return `401`)
- Confirm `artifactCompletenessCheck.ok=true` and `missing` is empty

## Common verification expectations

- Traefik uses staging-only ACME resolver (`le-staging`).
- Protected operational/admin endpoints are not publicly accessible without gating.
- API health checks return `200`.
- Celery ping/result endpoints succeed when worker is running.
