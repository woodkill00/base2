# Quickstart: One-Command Deploy with Verification

## Prerequisites
- .env configured (domain, credentials, DB settings)
- SSH key available for the droplet
- DigitalOcean API token (for orchestration)

## Commands

### Full deploy with timestamped logs
```powershell
# From repo root
./scripts/deploy.ps1 -Full -Timestamped -EnvPath ./.env -RunTests -TestsJson -RunRateLimitTest -RateLimitBurst 20
```

### Update-only redeploy (faster)
```powershell
./scripts/deploy.ps1 -UpdateOnly -Timestamped -EnvPath ./.env -RunTests -TestsJson -RunRateLimitTest -RateLimitBurst 20
```
Expected speedup: ≥30% vs full deploy on same environment. For measurement, run both modes back-to-back and compare total runtime logged in the terminal.

## Expected Outputs
- HTTPS reachable at configured domain (homepage)
- API health at https://<domain>/api/health returns OK
- Timestamped folder under local_run_logs containing:
  - compose-ps.txt, traefik-env.txt, traefik-static.yml, traefik-dynamic.yml
  - traefik-ls.txt, traefik-logs.txt
  - curl-root.txt, curl-api.txt
  - template snapshots for static/dynamic configs

## Troubleshooting
- Missing credentials → script fails fast with an actionable error.
- No IP resolution or blocked SSH → script skips remote verify and still saves local logs (with warning).
- DNS not pointing to droplet → health checks may fail; verify A/AAAA records and propagation.

---

## Ports & Routing Quick Reference
- Traefik: `80` (HTTP redirect), `443` (HTTPS, staging certs)
- Frontend: `react-app` internal `8080`, routed by `frontend-react`
- API: `api` internal `${FASTAPI_PORT}`, router `api` with `PathPrefix(/api)`
- Django: internal `${DJANGO_PORT}`, no public router by default
- Postgres: internal-only

## Pre-Flight Checklist
- `.env` has `FASTAPI_*`, `DJANGO_*`, `REACT_APP_API_URL`, `POSTGRES_*`, `JWT_*`, `RATE_LIMIT_*`, `WEBSITE_DOMAIN`, Traefik vars
- DNS points `${WEBSITE_DOMAIN}` to droplet
- DO token available; SSH key path resolvable
- Using staging certs only per policy

## Use Cases
- Full deploy: run `./scripts/deploy.ps1 -Full -Timestamped -EnvPath ./.env` → verify homepage + `/api/health`
- Update-only: run `./scripts/deploy.ps1 -UpdateOnly -Timestamped -EnvPath ./.env` → verify faster runtime and artifacts
- Remote verify unavailable: expect warning + partial artifacts; fix credentials/network and rerun
 - Preflight validation (optional):
   - Human-readable: `./scripts/validate-predeploy.ps1 -EnvPath ./.env -ComposePath ./local.docker.yml`
   - Strict + JSON: `./scripts/validate-predeploy.ps1 -EnvPath ./.env -ComposePath ./local.docker.yml -Strict -Json`

 - Post-Deploy Smoke Tests (optional):
   - `./scripts/smoke-tests.ps1 -EnvPath ./.env` (auto-uses `WEBSITE_DOMAIN` if present; defaults to `localhost`)
   - Verifies HTTP→HTTPS redirect, security headers (HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy), and `/api/health` 200

 - Post-deploy Verification (artifacts + smoke tests):
   - `./scripts/test.ps1 -EnvPath ./.env -LogsDir ./local_run_logs -UseLatestTimestamp`
  - CI-friendly JSON: `./scripts/test.ps1 -EnvPath ./.env -LogsDir ./local_run_logs -UseLatestTimestamp -Json`
   - When using `deploy.ps1 -RunTests -TestsJson`, the JSON report is saved to the latest timestamped artifact folder as `post-deploy-report.json`
  - Customize filename: add `-ReportName my-report.json` to `deploy.ps1` to save under a different name
   - Or include `-RunTests` with `deploy.ps1` to run automatically
   - Optional: Django proxy test: add `-CheckDjangoProxy`
   - Optional: Admin router test: add `-CheckDjangoAdmin [-AdminUser <user> -AdminPass <pass>]`

  ## Optional: Temporary Django Admin Exposure (Non-Production)
  - Purpose: briefly enable Django admin via `https://<DJANGO_ADMIN_DNS_LABEL>.<domain>/admin` with strict guards.
  - Guards enforced: staging TLS, basic auth (`TRAEFIK_DASH_BASIC_USERS`), and IP allowlist (`DJANGO_ADMIN_ALLOWLIST`).
  - Steps:
    1. Set env in `.env`:
      - `DJANGO_ADMIN_DNS_LABEL=admin`
      - `TRAEFIK_DASH_BASIC_USERS=<user:htpasswd>`
    2. Restrict to your IP:
      - `./scripts/update-django-admin-allowlist.ps1 -EnvPath ./.env`
    3. Apply Traefik config only:
      - `docker compose -f ./local.docker.yml up -d --force-recreate traefik`
    4. Browse: `https://admin.${WEBSITE_DOMAIN}/admin`
  - Disable afterwards: clear `DJANGO_ADMIN_DNS_LABEL`/`DJANGO_ADMIN_ALLOWLIST` and redeploy Traefik.

## Operator Tips
- Inspect Traefik routers/services via `docker compose -f local.docker.yml ps` and logs.
- If enabling admin temporarily in non-production, attach IP whitelist + auth; remove labels afterward.
 - Run the preflight script before deploy to catch env and compose misconfigurations early.
