# Stack Overview

Services (Compose-first):
- traefik: public edge (80/443), staging-only ACME, routing and security headers
- react-app: SPA built and served by Nginx (internal)
- nginx: internal Nginx (optional use, not a public edge)
- nginx-static: serves Django collected static for admin subdomain
- api: FastAPI external API under `/api/*` (Traefik strips prefix); canonical auth surface `/api/auth/*`
- django: canonical domain models, migrations, admin
- postgres: Postgres 16 (internal-only)
- redis: Redis 7.2 (internal-only)
- celery-worker: executes async jobs (django image)
- celery-beat: schedules periodic jobs (django image)
- flower: Celery monitoring UI (gated)
- pgadmin: DB admin UI (gated)

Routing:
- Host `${WEBSITE_DOMAIN}` path `/` -> react-app
- Host `${WEBSITE_DOMAIN}` path `/api/*` -> api (strip `/api`)
- Admin subdomain/path guarded -> django
- Admin static -> nginx-static
- pgadmin/flower/traefik dashboard -> gated subdomains

Policy:
- Staging-only ACME (`le-staging`) enforced; production issuance disallowed
- Security headers applied to public routes; admin routes may use no-HSTS variant for staging

Runtime notes:
- api runs under Gunicorn using `uvicorn.workers.UvicornWorker`.
- Email sending is provider-agnostic; if SMTP is not configured, emails are written to the Django `EmailOutbox` table.
- Phase 14 email flows: FastAPI writes outgoing messages to `api_email_outbox` (inspect via pgAdmin/psql).
