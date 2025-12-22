# Current State and Drift Risks (as of 2025-12-21)

## 1. Current Behavior

- **Docker Compose stack**: Traefik, Django, FastAPI, React, Nginx, Postgres, pgAdmin, Redis, Celery, Flower
- **Traefik**: File provider only, le-staging ACME, correct entrypoints, no Docker provider. Routers for API (with stripPrefix), Django admin, static, frontend, dashboard, pgAdmin, Flower, all with correct middlewares and priorities.
- **Nginx**: Internal-only, static serving, healthcheck.
- **Scripts**: All present and up to date for deploy, test, validation, logs, status, etc.
- **backend/**: Node backend present for deprecation/removal.
- **digital_ocean/**: Orchestration scripts and docs.
- **.github/workflows/**: CI/CD configs.
- **package.json**: Still references backend and react-app for test/lint/format.
- **.env/.env.example**: Present, but may need updates for new stack.

## 2. Drift Risks

- **Node backend**: Still present in codebase and package.json; risk of accidental deployment or confusion.
- **Compose/Traefik configs**: Must ensure no references to Node backend remain; all routers and services should point to Django, FastAPI, or React only.
- **Environment files**: .env and .env.example may have legacy or missing variables for Django/FastAPI/React.
- **Documentation**: Diagrams and stack docs may be outdated or reference deprecated services.
- **Scripts**: Any scripts referencing backend/ or Node.js must be updated or removed.
- **CI/CD**: Workflows must not build/test/deploy Node backend.

## 3. Planned Changes

- Remove Node.js backend from Compose, Traefik, scripts, and documentation.
- Add/verify Django and FastAPI services in Compose and Traefik.
- Update .env.example for Django, FastAPI, React.
- Update architecture diagrams and stack documentation.
- Ensure only Traefik exposes host ports (80/443).
- Validate all routers and middlewares in Traefik configs.
- Audit and update scripts and CI/CD workflows for new stack.

---

*This file is auto-generated as part of T000 (Inventory & sanity pass).*
