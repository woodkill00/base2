# Base2 Docker Environment


A robust, production-ready Docker setup with enhanced security, health checks, and comprehensive environment variable management.

## Feature Docs (Current Work)

- Spec: [specs/001-django-fastapi-react/spec.md](specs/001-django-fastapi-react/spec.md)
- Plan: [specs/001-django-fastapi-react/plan.md](specs/001-django-fastapi-react/plan.md)

## ⚠️ Platform Compatibility

All scripts require Bash and are tested on Mac, Linux, and Windows (WSL/Git Bash). For Windows, use WSL or Git Bash for best results.

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

### Stack Overview: Option 1 + Option B
- **Option 1 (Django + FastAPI)**
   - Django owns the schema, migrations, and admin UI (internal-only by default).
   - FastAPI is the public API runtime and talks to Postgres directly.
   - React is the public frontend and calls `https://${WEBSITE_DOMAIN}/api/...`.
- **Option B (Traefik strips `/api`)**
   - Traefik router `api` matches `Host(${WEBSITE_DOMAIN}) && PathPrefix(/api)`.
   - Middleware `strip-api-prefix` removes `/api` before forwarding to FastAPI.
   - FastAPI implements routes without the `/api` prefix (for example, `/health`).

## 📋 Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 4GB RAM available for Docker

## 🔧 Setup Instructions

### 1. Environment Configuration

Copy the example environment file and customize it:

```bash
cp .env.example .env
```

Edit `.env` to configure your services with custom values. All environment variables are documented in the file.

### 2. Build and Start Services

```bash
# Build all services
docker compose -f local.docker.yml build

# Start all services
docker compose -f local.docker.yml up -d

# View logs
docker compose -f local.docker.yml logs -f
```

### 2b. (Recommended) Use the Makefile shortcuts

If you have `make` available (Mac/Linux, or Windows via WSL/Git Bash), you can use:

```bash
make up
make logs
make test
```

See `Makefile` for all available targets.

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
- `TRAEFIK_DOCKER_NETWORK`: Docker network to monitor (default: base2_network)
- `TRAEFIK_EXPOSED_BY_DEFAULT`: Auto-expose containers (default: false)
 - `TRAEFIK_DNS_LABEL`: Subdomain label for Traefik dashboard host rule and DNS (default: `traefik`). Final FQDN: `${TRAEFIK_DNS_LABEL}.${WEBSITE_DOMAIN}`.

**⚠️ Important Notes:**

1. When changing the network name, you must update **both** `NETWORK_NAME` and `TRAEFIK_DOCKER_NETWORK` to the same value in `.env` for Traefik to work correctly. These two variables must always match.
## 🛠️ Troubleshooting

If you encounter issues running scripts:

- Ensure you are using Bash (not PowerShell or Command Prompt).
- On Windows, use WSL or Git Bash.
- Check your Docker Compose version (`docker-compose version`).
- Review error messages for missing files or environment variables.
- See the onboarding section in quickstart.md for more help.

This project includes an automatic synchronization system that keeps configuration files in sync with `.env` variables.

### Why Synchronization is Needed

Due to limitations in Docker Compose and YAML, certain values cannot use variable substitution:

- Network definition keys in `local.docker.yml`
- EntryPoint keys in `traefik/traefik.yml`
- The `TRAEFIK_DOCKER_NETWORK` must match `NETWORK_NAME`

### Automatic Synchronization

The `scripts/sync-env.sh` script automatically updates these literal values to match your `.env` file.

**Integration Points:**

1. **Manual Execution:**

   ```bash
   ./scripts/sync-env.sh
   ```

2. **Automatic on Start:**
   The `start.sh` script automatically runs synchronization before starting services.

3. **Git Pre-Commit Hook:**

   ```bash
   ./scripts/setup-hooks.sh  # Install git hooks
   ```

   Prevents commits if configuration is out of sync.

4. **CI/CD (GitHub Actions):**
   Workflow at `.github/workflows/sync-config.yml` validates configuration on push/PR.

### What Gets Synchronized

- **`local.docker.yml`**: Network definition key and service network references
- **`traefik/traefik.yml`**: API entrypoint key
- **`.env`**: `TRAEFIK_DOCKER_NETWORK` is updated to mirror `NETWORK_NAME`

Source of truth:
- `NETWORK_NAME` is the single source of truth for networking.
- `scripts/sync-env.sh` will automatically make `TRAEFIK_DOCKER_NETWORK` match `NETWORK_NAME`.

---

## 🛠️ Management Scripts

The `scripts/` directory contains convenient management scripts for common Docker operations. All major scripts now support a `--self-test` mode to verify environment and dependencies before running.

### Available Scripts

#### `./scripts/start.sh` - Start Services

Start all Docker services. Automatically checks for .env file and validates required environment variables. Supports self-test mode:

```bash
./scripts/start.sh --self-test   # Run self-test for environment and config
./scripts/start.sh               # Start in detached mode
./scripts/start.sh --build       # Build before starting
./scripts/start.sh --foreground  # Run in foreground
```

#### `./scripts/stop.sh` - Stop Services

Stop all Docker services. Supports self-test mode:

```bash
./scripts/stop.sh --self-test    # Run self-test for Docker and Compose
./scripts/stop.sh                # Stop services
./scripts/stop.sh --volumes      # Stop and remove volumes (deletes data!)
```

#### `./scripts/test.sh` - Run Tests

Run frontend tests by default.

```bash
./scripts/test.sh --self-test    # Run self-test for Node, npm, and test scripts
./scripts/test.sh                # Run all tests
./scripts/test.sh --coverage     # Run tests with coverage
./scripts/test.sh --watch        # Run tests in watch mode
```

#### `./scripts/logs.sh` - View Logs

View service logs with filtering options. Supports self-test mode:

```bash
./scripts/logs.sh --self-test    # Run self-test for Docker and Compose
./scripts/logs.sh                # View last 100 lines of all services
./scripts/logs.sh --follow       # Follow all logs in real-time
./scripts/logs.sh nginx          # View nginx logs
./scripts/logs.sh -f postgres    # Follow postgres logs
./scripts/logs.sh -t 50 nginx    # View last 50 lines of nginx
```

#### `./scripts/status.sh` - Check Status

Get comprehensive status of all services.

```bash
./scripts/status.sh             # Show status, health, and resource usage
```

#### `./scripts/health.sh` - Health Check

Check health status of all services with detailed output.

```bash
./scripts/health.sh             # Detailed health check for all services
```

#### `./scripts/rebuild.sh` - Rebuild Services

Rebuild Docker images.

```bash
./scripts/rebuild.sh            # Rebuild all services
./scripts/rebuild.sh nginx      # Rebuild specific service
./scripts/rebuild.sh --no-cache # Rebuild without cache
```

#### `./scripts/clean.sh` - Clean Resources

Clean up Docker resources.

```bash
./scripts/clean.sh              # Remove containers only
./scripts/clean.sh --volumes    # Remove containers and volumes
./scripts/clean.sh --images     # Remove containers and images
./scripts/clean.sh --all        # Remove everything
```

#### `./scripts/debug.sh` - Debug Services

Inspect containers, networks, and volumes for troubleshooting.

```bash
./scripts/debug.sh              # Debug all services
./scripts/debug.sh postgres     # Debug specific service
```

#### `./scripts/shell.sh` - Access Container Shell

Access a container's shell for direct interaction.

```bash
./scripts/shell.sh postgres     # Access postgres container
./scripts/shell.sh -b react-app # Access react-app with bash
```

#### `./scripts/kill.sh` - ⚠️ NUCLEAR OPTION ⚠️

**WARNING: DESTRUCTIVE OPERATION!** Completely removes ALL Docker resources for this project including all data. This is the nuclear option when you want to start completely fresh.

```bash
./scripts/kill.sh               # Requires typing "DELETE EVERYTHING" to confirm
./scripts/kill.sh --force       # Skip confirmation (use with extreme caution!)
```

This script will permanently delete:

- All containers (base2\_\*)
- All volumes (base2\_\*) - **ALL DATA WILL BE LOST**
- All images (base2\_\*)
- All networks (base2\_\*)

⚠️ **This action CANNOT be undone!** Use only when you want to completely reset the environment.

### Quick Start with Scripts

```bash
# Initial setup
./scripts/start.sh --build

# Check if everything is running
./scripts/status.sh

# View logs
./scripts/logs.sh --follow

# Access a container
./scripts/shell.sh postgres

# Stop everything
./scripts/stop.sh
```

## 🛠️ Direct Docker Compose Commands

If you prefer to use Docker Compose directly:

### Start Services

```bash
docker compose -f local.docker.yml up -d
```

### Stop Services

```bash
docker compose -f local.docker.yml down
```

### Restart a Specific Service

```bash
docker compose -f local.docker.yml restart react-app
```

### View Logs

```bash
# All services
docker compose -f local.docker.yml logs -f

# Specific service
docker compose -f local.docker.yml logs -f postgres
```

### Rebuild After Changes

```bash
docker compose -f local.docker.yml up -d --build
```

### Check Service Health

```bash
docker compose -f local.docker.yml ps
```

### Access Container Shell

```bash
docker compose -f local.docker.yml exec postgres sh
```

## 🗄️ Data Persistence

The following data is persisted in named volumes:

- `postgres_data`: PostgreSQL database files
- `pgadmin_data`: pgAdmin configuration and settings
- `traefik_logs`: Traefik access and error logs

To remove volumes (⚠️ **WARNING: This will delete all data**):

```bash
docker compose -f local.docker.yml down -v
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
docker compose -f local.docker.yml logs servicename
```

### Database Connection Issues

Verify PostgreSQL is healthy:

```bash
docker compose -f local.docker.yml exec postgres pg_isready -U myuser
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

This project configuration is available for use under your project's license terms.

## 🤝 Contributing

To contribute improvements:

1. Update the relevant Dockerfile or configuration
2. Test thoroughly with `docker compose build` and `up`
3. Update this README with any new features or changes
4. Document environment variables in `.env.example`
