# Project Overview

This workspace is a full-stack web application project, organized into several main components:

## 1. Backend (`backend/`)
- **Node.js/Express server**: The backend is built with Node.js and Express, handling API requests and business logic.
- **Authentication**: There are controllers and middleware for authentication, including JWT-based auth and email verification.
- **Database**: Uses a SQL database (likely PostgreSQL, based on the presence of `postgres/` and `.sql` files). The schema is defined in `database/schema.sql` and `postgres/init.sql`.
- **Testing**: Jest is used for backend unit/integration tests (`__tests__/`).
- **Config**: Database configuration is in `config/database.js`.

## 2. Frontend (`react-app/`)
- **React application**: The frontend is a React SPA, with routing and context for authentication.
- **Pages**: Includes pages for dashboard, user settings, password reset, email verification, etc.
- **Components**: Navigation, protected routes, and other UI components.
- **Services**: API service for communicating with the backend.
- **Testing**: Jest is also used for frontend tests.

## 3. Infrastructure
- **Docker Compose**: `local.docker.yml` defines the stack with internal-only exposure. Only Traefik maps host ports (80/443).
- **Nginx**: Standalone SPA server (`nginx/nginx.conf`), never exposed directly; Traefik routes to it.
- **Traefik v3**: Static config at `traefik/traefik.yml` and dynamic routers at `traefik/dynamic.yml`. Uses Let's Encrypt staging resolver `le-staging`.
- **PgAdmin**: Internal-only DB admin; no public exposure.

## 4. Scripts (`scripts/`)
- Shell scripts for managing the environment, starting/stopping services, health checks, logs, and testing.

## 5. Project Management
- **README.md**: Contains setup and usage instructions.
- **Workspace file**: VS Code workspace configuration.

## 6. Build & Deployment
The build process composes services with Traefik as the only public entrypoint.

- Frontend served by Nginx via Traefik
- Backend API routed via Traefik at `/api`
- PostgreSQL and pgAdmin are internal-only
- Health checks enabled across services

DigitalOcean automation (`digital_ocean/orchestrate_deploy.py`) provisions a droplet, applies cloud-init (`digital_ocean/scripts/digital_ocean_base.sh`), runs post-reboot config, starts the stack, and summarizes health/logs.

## 7. Authentication & Security
- The project supports user authentication, password reset, email verification, and protected routes.
- Security hardening: non-root users, `no-new-privileges`, Traefik capability to bind 80/443, read-only filesystems, tmpfs for Nginx, and disabled insecure dashboard.

## 8. Operations
- Management scripts in `scripts/` for start/stop/logs/status/health/test.
- `scripts/start.sh` validates `.env`, syncs literal config, starts services, and prints endpoints.
- Ensure `NETWORK_NAME` equals `TRAEFIK_DOCKER_NETWORK` in `.env`.

---

**Summary:**  
This build is a modern, containerized web application with a React frontend, Node.js backend, PostgreSQL database, and infrastructure managed via Docker, Nginx, and Traefik. It includes robust authentication features, automated testing, and scripts for easy management and deployment. The architecture is suitable for scalable, secure web services.

If you want a deeper dive into any specific part (e.g., authentication flow, database schema, deployment), let me know!
