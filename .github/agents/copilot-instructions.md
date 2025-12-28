# base2 Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-12-24

## Active Technologies
- Python 3.12 (Django + FastAPI), Node 18 (React), PowerShell 5.1 (deploy/test) + Docker Compose, Traefik v3.1, Django + Gunicorn, FastAPI + Uvicorn, React 18, Nginx, Postgres 16, Redis 7.2, Celery, Flower (001-django-fastapi-react)
- PostgreSQL 16 (service `postgres`; Django migrations are canonical) (001-django-fastapi-react)

- (001-django-fastapi-react)

## Project Structure

```text
src/
tests/
```

## Commands

# Add commands for 

## Code Style

: Follow standard conventions

## Recent Changes
- 001-django-fastapi-react: Added Python 3.12 (Django + FastAPI), Node 18 (React), PowerShell 5.1 (deploy/test) + Docker Compose, Traefik v3.1, Django + Gunicorn, FastAPI + Uvicorn, React 18, Nginx, Postgres 16, Redis 7.2, Celery, Flower

- 001-django-fastapi-react: Added

<!-- MANUAL ADDITIONS START -->
## Repo-Accurate Structure (manual)

```text
api/
django/
react-app/
traefik/
nginx/
postgres/
pgadmin/
digital_ocean/
specs/
```

## Operational Entry Point (manual)

- Deploy/update/test (authoritative): `digital_ocean/scripts/powershell/deploy.ps1`
- Post-deploy verification: `digital_ocean/scripts/powershell/test.ps1`

<!-- MANUAL ADDITIONS END -->
