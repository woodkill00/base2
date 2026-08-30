# Docker Environment

A robust, production-ready Docker setup with enhanced security, health checks, and comprehensive environment variable management.

## Quickstart (Docker-first)

1. `./scripts/powershell/first-start.ps1`
2. `./scripts/powershell/start.ps1`
3. `./scripts/powershell/test.ps1`
4. Open `https://${WEBSITE_DOMAIN}` (staging cert warnings are expected)
5. For a deeper setup flow, see [quickstart.md](quickstart.md)
6. Architecture overview: [project_overview.md](project_overview.md)

## CI Status

- [![CI (backend)](https://github.com/woodkill00/base2/actions/workflows/ci-backend.yml/badge.svg?branch=main)](https://github.com/woodkill00/base2/actions/workflows/ci-backend.yml)
- [![CI (contract)](https://github.com/woodkill00/base2/actions/workflows/ci-contract.yml/badge.svg?branch=main)](https://github.com/woodkill00/base2/actions/workflows/ci-contract.yml)
- [![CI (e2e)](https://github.com/woodkill00/base2/actions/workflows/ci-e2e.yml/badge.svg?branch=main)](https://github.com/woodkill00/base2/actions/workflows/ci-e2e.yml)
- [![CI (frontend)](https://github.com/woodkill00/base2/actions/workflows/ci-frontend.yml/badge.svg?branch=main)](https://github.com/woodkill00/base2/actions/workflows/ci-frontend.yml)
- [![CI (perf-smoke)](https://github.com/woodkill00/base2/actions/workflows/ci-perf-smoke.yml/badge.svg?branch=main)](https://github.com/woodkill00/base2/actions/workflows/ci-perf-smoke.yml)
- [![CI (repo guards)](https://github.com/woodkill00/base2/actions/workflows/ci-repo-guards.yml/badge.svg?branch=main)](https://github.com/woodkill00/base2/actions/workflows/ci-repo-guards.yml)
- [![CI (smoke)](https://github.com/woodkill00/base2/actions/workflows/ci-smoke.yml/badge.svg?branch=main)](https://github.com/woodkill00/base2/actions/workflows/ci-smoke.yml)
- [![CI (load)](https://github.com/woodkill00/base2/actions/workflows/ci-load.yml/badge.svg?branch=main)](https://github.com/woodkill00/base2/actions/workflows/ci-load.yml)
- [![CI (chaos)](https://github.com/woodkill00/base2/actions/workflows/ci-chaos.yml/badge.svg?branch=main)](https://github.com/woodkill00/base2/actions/workflows/ci-chaos.yml)
- [![Option1 Guard](https://github.com/woodkill00/base2/actions/workflows/option1-guard.yml/badge.svg?branch=main)](https://github.com/woodkill00/base2/actions/workflows/option1-guard.yml)
- [![Sync Environment Configuration](https://github.com/woodkill00/base2/actions/workflows/sync-config.yml/badge.svg?branch=main)](https://github.com/woodkill00/base2/actions/workflows/sync-config.yml)
- [![security](https://github.com/woodkill00/base2/actions/workflows/security.yml/badge.svg?branch=main)](https://github.com/woodkill00/base2/actions/workflows/security.yml)

## Feature Docs (Current Work)

- Spec: [specs/001-django-fastapi-react/spec.md](specs/001-django-fastapi-react/spec.md)
- Plan: [specs/001-django-fastapi-react/plan.md](specs/001-django-fastapi-react/plan.md)
- Observability: [docs/OBSERVABILITY.md](docs/OBSERVABILITY.md)

## ⚠️ Platform Compatibility

Primary automation scripts live in `scripts/powershell/` and `scripts/bash/`.

- Windows: run PowerShell entrypoints with Windows PowerShell or PowerShell 7.
- macOS/Linux: run Bash entrypoints or use `pwsh` for PowerShell scripts.
- Bash entrypoints cover local Docker flows (start/logs/test/seed).

## ⚠️ Docker Compose Version

Docker Compose v2.0.0 or newer is required. Scripts will check and warn if your version is outdated.

## 🚀 Services

This Docker environment includes the following services:

- **React App**: Node.js-based React application with Google OAuth
- **API**: FastAPI-based service
- **Nginx**: Web server and reverse proxy
- **PostgreSQL**: Relational database with authentication schema
- **pgAdmin**: PostgreSQL management interface
- **Traefik**: Modern reverse proxy and load balancer

### TLS & Certificates (Staging-Only Policy)

- Traefik in this repository is configured to use **Let's Encrypt staging ACME** only.
- All HTTPS endpoints will present **staging certificates** and therefore show browser warnings.
- **No production/real certificates are issued by default**; this environment is for development and pre-production simulation.
- If you fork or adapt this for production, you must explicitly update the Traefik ACME configuration and associated documentation.

### Stack Overview: Option 1 (Authoritative)

- **Django**: Owns schema, migrations, and admin UI (internal-only by default).
- **FastAPI**: Public API runtime and talks to Postgres directly; all public routes are under `/api/*`.
- **React**: Public frontend; calls `https://${WEBSITE_DOMAIN}/api/...`.
- **Traefik**: Routes `/api/*` to FastAPI as pass-through (no prefix stripping).

### Architecture (Option 1)

```
          [ Traefik :80/:443 ]
               |
      +--------------+--------------+
      |                             |
   /api/* -> [ FastAPI ]         / -> [ Nginx -> React ]
      |
      v
   [ PostgreSQL ] <- [ Django (schema + admin) ]
```

More detail in [project_overview.md](project_overview.md).

## Contents

- [Services](#-services)
- [Prerequisites](#-prerequisites)
- [Setup Instructions](#-setup-instructions)
- [Testing](#-testing)
- [DigitalOcean Deploy (Optional)](#digitalocean-deploy-optional)

## 📋 Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 4GB RAM available for Docker

## 🔧 Setup Instructions

### Python Environment (required)

Use the orchestration script to create/activate the virtual environment and install dependencies:

```powershell
./scripts/powershell/first-start.ps1
```

```bash
pwsh -ExecutionPolicy Bypass -File ./scripts/powershell/first-start.ps1
```

This script:

- Creates `.venv` (or recreates with `-ForceVenv`)
- Activates the environment for the current session
- Installs Python packages (digital_ocean requirements)
- Installs Node packages in the root, `react-app/`, and `e2e/`
- Runs `scripts/powershell/setup.ps1` to generate `.env` from `.env.example`
- Use `-SkipSetup` if you only need dependency hydration without re-running the guided setup.

During `scripts/powershell/setup.ps1`, you may be prompted to confirm overwriting `.env` and to provide required values (DigitalOcean token, domain, email, etc.). You can also edit `.env` manually afterward.

### Setup prompts (interactive)

The interactive questions come from [scripts/setup.js](scripts/setup.js) (invoked by [scripts/powershell/setup.ps1](scripts/powershell/setup.ps1)). These are the exact prompts and choices:

- Overwrite existing .env: yes/no (default no); creates a timestamped backup on yes.
- Project name: lowercase letters, digits, hyphen only; required.
- Website domain: required non-empty value.
- Primary email: optional; if provided you are asked whether to apply it to all default email fields.
- Primary password: optional (masked); if provided you are asked whether to apply it to all default password fields.
- Primary username: optional; if provided you are asked whether to apply it to all default username fields.
- Git repo URL: optional; used for deploy automation defaults.
- Git repo branch: optional; used for deploy automation defaults.
- Environment: choice of development, staging, production.
- Deploy mode: choice of local or digitalocean.
- Apply safe dev defaults: yes/no, only when environment is development.

Dev defaults summary:

- Selecting "Apply safe dev defaults" sets `APPLY_DEV_DEFAULTS=true` in `.env`.
- When you later run `npm run setup:complete`, the only change it applies is `DJANGO_DEBUG=true` (only if `ENV=development`).

Non-interactive note:

- `scripts/powershell/setup.ps1 -NonInteractive` disables prompts and reads values from args/environment; it will fail fast if required values are missing.

After writing .env, [scripts/setup.js](scripts/setup.js) prints a checklist of required categories and recommends running:

- npm run setup:complete
- npm run doctor

Exact scripts invoked by `first-start.ps1` (in order):

- `scripts/powershell/bootstrap-venv.ps1`
- `scripts/powershell/install-python-deps.ps1`
- `scripts/powershell/install-node-deps.ps1`
- `scripts/powershell/setup.ps1`

Tip: `scripts/powershell/first-start.ps1 -Help` and `scripts/powershell/setup.ps1 -Help` print usage details.

### DigitalOcean SSH key sync (runs during setup)

This step runs inside [scripts/powershell/setup.ps1](scripts/powershell/setup.ps1) after .env is written. It calls [digital_ocean/scripts/powershell/add-ssh-key.ps1](digital_ocean/scripts/powershell/add-ssh-key.ps1) and uses [digital_ocean/scripts/python/DO_ssh_keys.py](digital_ocean/scripts/python/DO_ssh_keys.py).

What it does (ordered):

- Determines the key name from PROJECT_NAME (fallback: do-ssh).
- Ensures a local SSH key exists at ~/.ssh/<keyName> (creates ED25519 key if missing).
- Queries DigitalOcean for matching keys (same name and public key).
- If a mismatch exists, deletes old DO keys and registers the local key.
- Updates .env with DO_SSH_KEY_ID and DO_API_SSH_KEYS.

Why it exists:

- Droplet provisioning requires a valid DO SSH key; this keeps local and DO keys in sync automatically.

### Golden path (all-green deploy)

See the full end-to-end sequence in [docs/GOLDEN_PATH.md](docs/GOLDEN_PATH.md).

Keep the environment active for every Python-related command (pip installs, Django/DO scripts, tests). Re-run `./scripts/powershell/first-start.ps1` anytime you need to refresh dependencies.

If you prefer a manual venv flow (no guided setup), install Python deps per service with:

```bash
python -m pip install -r requirements-dev-api.txt
# or
python -m pip install -r requirements-dev-django.txt
```

### 1. Install root tooling dependencies

The guided environment setup commands live in the repository root.

```bash
npm install
```

### 2. Generate `.env` (guided)

```bash
npm run setup
```

This creates (or overwrites, with confirmation) `.env` based on `.env.example`, derives identifiers from `PROJECT_NAME`, and prints a categorized next-steps checklist.

### 3. Validate + fill required config (recommended)

```bash
npm run setup:complete -- --no-print
```

This validates required categories, generates missing credentials, fills IP allowlists when placeholders remain, and is safe to re-run.

### 4. Readiness check (read-only)

```bash
npm run doctor -- --strict
```

Use `--json` if you want machine-readable output.

### 5. Build and Start Services

```bash
# Build all services
docker compose -f development.docker.yml build

# Start all services
docker compose -f development.docker.yml up -d

# View logs
docker compose -f development.docker.yml logs -f
```

### 5b. (Recommended) Use the Makefile shortcuts

If you have `make` available (Mac/Linux, or Windows via WSL/Git Bash), you can use:

```bash
make up
make logs
make test
```

See `Makefile` for all available targets.

If you do not have `make`, use the cross-platform wrapper:

```bash
./scripts/make/make.sh start
```

```powershell
./scripts/make/make.ps1 start
```

On Windows PowerShell (no Bash/make required), use the equivalent wrappers:

```powershell
./scripts/powershell/start.ps1
./scripts/powershell/logs.ps1
./scripts/powershell/test.ps1
```

`make test`, `./scripts/bash/test.sh`, and `./scripts/powershell/test.ps1` expect the Docker stack to be running; start it first with `make up` or `./scripts/powershell/start.ps1`.

Integration/perf tests are opt-in:

```bash
make test-integration
make test-perf
```

## 🧪 Testing

- Default unit-only runs: `./scripts/powershell/test.ps1` or `./scripts/bash/test.sh`
- Integration/perf (opt-in): `make test-integration`, `make test-perf`
- Local compose override: `./scripts/powershell/test.ps1 -ComposeFile local.docker.yml -EnvFile .env.local`

### Lint (frontend)

```bash
cd react-app
npm run lint
```

### Use local.docker.yml for local testing

All local helper scripts support an explicit compose file flag. Examples:

You can also keep a separate env file (for example, `.env.local`) and pass it explicitly.

```bash
./scripts/bash/start.sh --compose-file local.docker.yml --env-file .env.local
./scripts/bash/test.sh --compose-file local.docker.yml --env-file .env.local
./scripts/bash/stop.sh --compose-file local.docker.yml --env-file .env.local
```

```powershell
./scripts/powershell/start.ps1 -ComposeFile local.docker.yml -EnvFile .env.local
./scripts/powershell/test.ps1 -ComposeFile local.docker.yml -EnvFile .env.local
./scripts/powershell/stop.ps1 -ComposeFile local.docker.yml -EnvFile .env.local
```

```bash
make COMPOSE_FILE=local.docker.yml ENV_FILE=.env.local up
make COMPOSE_FILE=local.docker.yml ENV_FILE=.env.local test
```

### Seed data (dev/demo)

Configure `SEED_ADMIN_EMAIL` and `SEED_ADMIN_PASSWORD` in `.env`, then run:

```bash
make seed
```

Windows PowerShell:

```powershell
./scripts/powershell/seed.ps1
```

### 3. Configure Authentication (IMPORTANT!)

Before starting, you MUST configure:

**A. JWT Secret (Required):**

```bash
# Generate secure JWT secret
node -e "console.log(require('crypto').randomBytes(64).toString('hex'))"

# Add to .env as JWT_SECRET=<generated_value>
```

**B. Email Service (Required for email/password auth):**

```env
# For Gmail (development):
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_gmail_app_password

# Or use SendGrid, Mailgun, etc.
```

If you enable email-based flows, configure an app password/provider credentials.

### 4. Access Services

Once running, access the services at:
**React App**: Built into static assets; served internally by Nginx
**API**: FastAPI service routed via Traefik `/api`
**Nginx**: Standalone SPA server; only exposed via Traefik
**PostgreSQL**: Internal-only database; health-checked
**pgAdmin**: https://${PGADMIN_DNS_LABEL}.${WEBSITE_DOMAIN} (via Traefik; basic-auth + IP allowlist)
**Traefik v3**: Only public entrypoint (80/443); staging certs; no insecure dashboard

- **Traefik Dashboard**: disabled insecure access
  - Host: `${TRAEFIK_DNS_LABEL}.${WEBSITE_DOMAIN}` via HTTPS, protected by basic-auth
- **PostgreSQL**: internal-only (no public access)

## 🔐 Security Enhancements

All Dockerfiles have been enhanced with:

### Non-Root Users

- Each service runs as a non-root user for improved security
- Proper file permissions and ownership configured

  **Frontend (via Traefik)**: `http://localhost` (HTTP)
  **Frontend (HTTPS)**: `https://${WEBSITE_DOMAIN}` (staging cert; expect browser warning)

- Built-in health monitoring for all services
- Automatic restart on failure
- Configurable health check intervals
- Optimized PostgreSQL configuration for better performance

## 📝 Environment Variables

- `REACT_APP_API_URL`: API endpoint URL
- `NGINX_PORT`: Internal container port (default: 80)
- `NGINX_HOST_PORT`: Host machine port (default: 8080)
- `NGINX_WORKER_PROCESSES`: Number of worker processes (default: auto)
- `NGINX_WORKER_CONNECTIONS`: Max connections per worker (default: 1024)

### PostgreSQL

- `POSTGRES_USER`: Database user
- `POSTGRES_PASSWORD`: Database password (change in production!)
- `POSTGRES_DB`: Database name

### pgAdmin

- `PGADMIN_VERSION`: pgAdmin version (default: latest)
- `PGADMIN_DEFAULT_EMAIL`: Admin email
- `PGADMIN_DEFAULT_PASSWORD`: Admin password (change in production!)
- `PGADMIN_PORT`: Internal container port (default: 80)
- `PGADMIN_HOST_PORT`: Host machine port (default: 5050)
- `PGADMIN_ALLOWLIST`: CIDR(s) allowed to access pgAdmin via Traefik (e.g., `203.0.113.5/32`). Default `0.0.0.0/0` exposes to all (change in production!).
- `PGADMIN_DNS_LABEL`: Subdomain label used for DNS and Traefik host rule (default: `pgadmin`). Final FQDN is `${PGADMIN_DNS_LABEL}.${WEBSITE_DOMAIN}`.

To enable web access to pgAdmin:

- Ensure DNS `A` record for `${PGADMIN_DNS_LABEL}.${WEBSITE_DOMAIN}` points to your server (orchestrator will create/update automatically).
- Set `TRAEFIK_DASH_BASIC_USERS` in `.env` to an htpasswd entry.
- Set `PGADMIN_ALLOWLIST` to your public IP `/32` to restrict access.

### Traefik

- `TRAEFIK_DOCKER_NETWORK`: Docker network to monitor (default: `${NETWORK_NAME}`)
- `TRAEFIK_EXPOSED_BY_DEFAULT`: Auto-expose containers (default: false)
- `TRAEFIK_DNS_LABEL`: Subdomain label for Traefik dashboard host rule and DNS (default: `traefik`). Final FQDN: `${TRAEFIK_DNS_LABEL}.${WEBSITE_DOMAIN}`.

**⚠️ Important Notes:**

1. When changing the network name, you must update **both** `NETWORK_NAME` and `TRAEFIK_DOCKER_NETWORK` to the same value in `.env` for Traefik to work correctly. These two variables must always match.

## Development Versions

- **Python**: 3.12 (pin via .python-version)
- **Node.js**: 24.20.0 (pin via react-app/.nvmrc)

Fresh clone: install these versions before running builds/tests.

## Contribution & Release

- See CONTRIBUTING.md for dev flow, commit style, and PR guidance.
- See docs/RELEASE.md for tagging and deploy validation.

## 🛠️ Troubleshooting

If you encounter issues running scripts:

- PowerShell entrypoints live in `scripts/powershell/` (use `pwsh` on macOS/Linux).
- Bash entrypoints live in `scripts/bash/` and work in WSL or Git Bash.
- Check your Docker Compose version (`docker-compose version`).
- Review error messages for missing files or environment variables.
- See the onboarding section in quickstart.md for more help.

This project includes an automatic synchronization system that keeps configuration files in sync with `.env` variables.

### Why Synchronization is Needed

Due to limitations in Docker Compose and YAML, certain values cannot use variable substitution:

- Network definition keys in `development.docker.yml`
- EntryPoint keys in `traefik/traefik.yml`
- The `TRAEFIK_DOCKER_NETWORK` must match `NETWORK_NAME`

### Automatic Synchronization

The `scripts/bash/sync-env.sh` script automatically updates these literal values to match your `.env` file.

**Integration Points:**

1. **Manual Execution:**

   ```bash
   ./scripts/bash/sync-env.sh
   ```

2. **Automatic on Start:**
   The `scripts/bash/start.sh` script automatically runs synchronization before starting services.

3. **Git Pre-Commit Hook:**

   ```bash
   ./scripts/bash/setup-hooks.sh  # Install git hooks
   ```

   Prevents commits if configuration is out of sync.

4. **CI/CD (GitHub Actions):**
   Workflow at `.github/workflows/sync-config.yml` validates configuration on push/PR.

### What Gets Synchronized

- **`development.docker.yml`**: Network definition key and service network references
- **`traefik/traefik.yml`**: API entrypoint key
- **`.env`**: `TRAEFIK_DOCKER_NETWORK` is updated to mirror `NETWORK_NAME`

Source of truth:

- `NETWORK_NAME` is the single source of truth for networking.
- `scripts/bash/sync-env.sh` will automatically make `TRAEFIK_DOCKER_NETWORK` match `NETWORK_NAME`.

---

## 🛠️ Management Scripts

The `scripts/` directory contains convenient management scripts for common Docker operations. All major scripts now support a `--self-test` mode to verify environment and dependencies before running.

### Available Scripts

#### `./scripts/bash/start.sh` - Start Services

Start all Docker services. Automatically checks for .env file and validates required environment variables. Supports self-test mode:

```bash
./scripts/bash/start.sh --self-test   # Run self-test for environment and config
./scripts/bash/start.sh               # Start in detached mode
./scripts/bash/start.sh --build       # Build before starting
./scripts/bash/start.sh --foreground  # Run in foreground
```

#### `./scripts/bash/stop.sh` - Stop Services

Stop all Docker services. Supports self-test mode:

```bash
./scripts/bash/stop.sh --self-test    # Run self-test for Docker and Compose
./scripts/bash/stop.sh                # Stop services
./scripts/bash/stop.sh --volumes      # Stop and remove volumes (deletes data!)
```

#### `./scripts/bash/test.sh` - Run Tests

Run backend tests in Docker and frontend tests locally. Requires the stack to be running.

```bash
./scripts/bash/test.sh --self-test    # Run self-test for Node, npm, and test scripts
./scripts/bash/test.sh                # Run all tests
./scripts/bash/test.sh --coverage     # Run tests with coverage
./scripts/bash/test.sh --watch        # Run tests in watch mode
```

#### `./scripts/bash/logs.sh` - View Logs

View service logs with filtering options. Supports self-test mode:

```bash
./scripts/bash/logs.sh --self-test    # Run self-test for Docker and Compose
./scripts/bash/logs.sh                # View last 100 lines of all services
./scripts/bash/logs.sh --follow       # Follow all logs in real-time
./scripts/bash/logs.sh nginx          # View nginx logs
./scripts/bash/logs.sh -f postgres    # Follow postgres logs
./scripts/bash/logs.sh -t 50 nginx    # View last 50 lines of nginx
```

#### `./scripts/bash/status.sh` - Check Status

Get comprehensive status of all services.

```bash
./scripts/bash/status.sh             # Show status, health, and resource usage
```

#### `./scripts/bash/health.sh` - Health Check

Check health status of all services with detailed output.

```bash
./scripts/bash/health.sh             # Detailed health check for all services
```

#### `./scripts/bash/rebuild.sh` - Rebuild Services

Rebuild Docker images.

```bash
./scripts/bash/rebuild.sh            # Rebuild all services
./scripts/bash/rebuild.sh nginx      # Rebuild specific service
./scripts/bash/rebuild.sh --no-cache # Rebuild without cache
```

#### `./scripts/bash/clean.sh` - Clean Resources

Clean up Docker resources.

```bash
./scripts/bash/clean.sh              # Remove containers only
./scripts/bash/clean.sh --volumes    # Remove containers and volumes
./scripts/bash/clean.sh --images     # Remove containers and images
./scripts/bash/clean.sh --all        # Remove everything
```

#### `./scripts/bash/debug.sh` - Debug Services

Inspect containers, networks, and volumes for troubleshooting.

```bash
./scripts/bash/debug.sh              # Debug all services
./scripts/bash/debug.sh postgres     # Debug specific service
```

#### `./scripts/bash/shell.sh` - Access Container Shell

Access a container's shell for direct interaction.

```bash
./scripts/bash/shell.sh postgres     # Access postgres container
./scripts/bash/shell.sh -b react-app # Access react-app with bash
```

#### `./scripts/bash/kill.sh` - ⚠️ NUCLEAR OPTION ⚠️

**WARNING: DESTRUCTIVE OPERATION!** Completely removes ALL Docker resources for this project including all data. This is the nuclear option when you want to start completely fresh.

```bash
./scripts/bash/kill.sh               # Requires typing "DELETE EVERYTHING" to confirm
./scripts/bash/kill.sh --force       # Skip confirmation (use with extreme caution!)
```

This script will permanently delete:

- All containers (`${COMPOSE_PROJECT_NAME}_*`)
- All volumes (`${COMPOSE_PROJECT_NAME}_*`) - **ALL DATA WILL BE LOST**
- All images (`*${COMPOSE_PROJECT_NAME}*`)
- Network: `${NETWORK_NAME}` (and any network matching `*${COMPOSE_PROJECT_NAME}*`)

⚠️ **This action CANNOT be undone!** Use only when you want to completely reset the environment.

### Quick Start with Scripts

```bash
# Initial setup
./scripts/bash/start.sh --build

# Check if everything is running
./scripts/bash/status.sh

# View logs
./scripts/bash/logs.sh --follow

# Access a container
./scripts/bash/shell.sh postgres

# Stop everything
./scripts/bash/stop.sh
```

## 🛠️ Direct Docker Compose Commands

If you prefer to use Docker Compose directly:

Tip: swap `development.docker.yml` for `local.docker.yml` when running local-only stacks.

### Start Services

```bash
docker compose -f development.docker.yml up -d
```

### Stop Services

```bash
docker compose -f development.docker.yml down
```

### Restart a Specific Service

```bash
docker compose -f development.docker.yml restart react-app
```

### View Logs

```bash
# All services
docker compose -f development.docker.yml logs -f

# Specific service
docker compose -f development.docker.yml logs -f postgres
```

### Rebuild After Changes

```bash
docker compose -f development.docker.yml up -d --build
```

### Check Service Health

```bash
docker compose -f development.docker.yml ps
```

### Access Container Shell

```bash
docker compose -f development.docker.yml exec postgres sh
```

## 🗄️ Data Persistence

The following data is persisted in named volumes:

- `postgres_data`: PostgreSQL database files
- `pgadmin_data`: pgAdmin configuration and settings
- `traefik_logs`: Traefik access and error logs

To remove volumes (⚠️ **WARNING: This will delete all data**):

```bash
docker compose -f development.docker.yml down -v
```

## 🔍 Troubleshooting

### Port Conflicts

If you encounter port conflicts, update the `*_HOST_PORT` variables in your `.env` file.

### Permission Issues

Ensure Docker has proper permissions:

```bash
sudo usermod -aG docker $USER
```

Then log out and back in.

### Container Won't Start

Check logs for the specific service:

```bash
docker compose -f development.docker.yml logs servicename
```

### Database Connection Issues

Verify PostgreSQL is healthy:

```bash
docker compose -f development.docker.yml exec postgres pg_isready -U myuser
```

## 🚨 Production Considerations

Before deploying to production:

1. **Change Default Passwords**: Update all default passwords in `.env`
2. **Enable SSL/TLS**: Configure HTTPS for Traefik and Nginx
3. **Review Security Settings**: Disable debug modes and insecure settings
4. **Configure Backups**: Set up regular database backups
5. **Monitor Resources**: Implement proper logging and monitoring
6. **Update Versions**: Keep all service versions up to date
7. **Network Isolation**: Review and restrict network access as needed

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Traefik Documentation](https://doc.traefik.io/traefik/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

## 📄 License

See [LICENSE](LICENSE).

## 🤝 Contributing

To contribute improvements:

1. Update the relevant Dockerfile or configuration
2. Test thoroughly with `docker compose build` and `up`
3. Update this README with any new features or changes
4. Document environment variables in `.env.example`
