# Research Notes: FastAPI + Django Automated Deployment

Date: 2025-12-18
Branch: 001-fastapi-django-deploy

## Key Decisions
- Traefik remains sole public entrypoint on 80/443.
- Staging certificates only for this simulation; no production issuance.
- Fail fast on missing/invalid cloud credentials; do not proceed locally.
- Django admin non-public by default; optional exposure only in non-production with extra protections.

## Integration Summary
- FastAPI replaces existing Node backend at `/api/**` via Traefik routing.
- Django runs internal-only; FastAPI may call Django over internal network.
- Post-deploy verification collects proxy config, container state, and HTTP headers.

## Open Items (tracked in plan)
- Compose changes for `api/` and `django/` services.
- Health endpoint presence at `/api/health`.
- Operator quickstart for deploy and troubleshooting.
