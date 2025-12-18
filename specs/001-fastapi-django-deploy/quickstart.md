# Quickstart: One-Command Deploy with Verification

## Prerequisites
- .env configured (domain, credentials, DB settings)
- SSH key available for the droplet
- DigitalOcean API token (for orchestration)

## Commands

### Full deploy with timestamped logs
```powershell
# From repo root
./scripts/deploy.ps1 -Full -Timestamped -EnvPath ./.env
```

### Update-only redeploy (faster)
```powershell
./scripts/deploy.ps1 -UpdateOnly -Timestamped -EnvPath ./.env
```

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

## Operator Tips
- Inspect Traefik routers/services via `docker compose -f local.docker.yml ps` and logs.
- If enabling admin temporarily in non-production, attach IP whitelist + auth; remove labels afterward.
 - Run the preflight script before deploy to catch env and compose misconfigurations early.
