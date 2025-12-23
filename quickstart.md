# Quickstart Guide

## Platform Requirements
- Bash shell (Mac, Linux, Windows WSL or Git Bash)
- Docker Engine 20.10+
- Docker Compose v2.0.0 or newer

## Setup Steps
1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd base2
   ```
2. Copy and configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env to set your values
   ## Digital Ocean Automation Onboarding
   This project includes robust Digital Ocean automation for deployment, teardown, edit/maintain, info/query, and exec actions.

   ### Digital Ocean Setup Steps
   1. Copy `.env.example` to `.env` and fill in all required Digital Ocean variables:
      - `DO_API_TOKEN`, `DO_API_REGION`, `DO_API_IMAGE`, `DO_APP_NAME`, etc.
   2. Create and activate Python virtual environment:
      ```bash
      python -m venv .venv
      source .venv/bin/activate  # or .venv\Scripts\activate on Windows
      pip install -r requirements.txt
      ```
   3. Run automation scripts:
      - Deploy: `./scripts/deploy.sh [--dry-run]` or `python digital_ocean/deploy.py [--dry-run]`
      - Teardown: `./scripts/teardown.sh [--dry-run]` or `python digital_ocean/teardown.py [--dry-run]`
      - Edit/Maintain: `./scripts/edit.sh` or `python digital_ocean/edit.py`
      - Info/Query: `./scripts/info.sh` or `python digital_ocean/info.py`
      - Exec: `./scripts/exec.sh` or `python digital_ocean/exec.py`

   ### Cross-Platform Notes
   - **Windows:** Use PowerShell for Python venv activation and script execution, or WSL/Git Bash for shell scripts.
   - **Mac/Linux:** Use Bash/Zsh for all scripts.
   - **Docker:** All automation scripts work in containerized environments.

   ### Troubleshooting
   - Ensure all required variables are set in `.env` (see `.env.example`).
   - Check API token permissions and region/image slugs.
   - Review logs for error details.
   - For rate limit issues, adjust retry settings in `.env`.

   See `digital_ocean/README.md` for full usage, error handling, and troubleshooting details.

   ## Onboarding Checklist
   Follow these steps to get started quickly:

   1. **Clone the repository**
      - `git clone <repo-url>`
      - `cd base2`
   2. **Configure environment variables**
      - Copy `.env.example` to `.env`
      - Fill in all required Digital Ocean variables (`DO_API_TOKEN`, `DO_API_REGION`, `DO_API_IMAGE`, `DO_APP_NAME`, etc.)
   3. **Set up Python environment**
      - Python 3.10+ required
      - Create and activate a virtual environment:
        - `python -m venv .venv`
        - `source .venv/bin/activate` (Linux/macOS) or `.venv\Scripts\activate` (Windows)
      - Install dependencies:
        - `pip install -r requirements.txt`
   4. **(Optional) Set up Node.js dependencies**
      - If using frontend scripts, run `npm install` in `react-app/`
   5. **Run automation scripts**
      - Deploy: `./scripts/deploy.sh [--dry-run]` or `python digital_ocean/deploy.py [--dry-run]`
      - Teardown: `./scripts/teardown.sh [--dry-run]` or `python digital_ocean/teardown.py [--dry-run]`
      - Edit/Maintain: `./scripts/edit.sh` or `python digital_ocean/edit.py`
      - Info/Query: `./scripts/info.sh` or `python digital_ocean/info.py`
      - Exec: `./scripts/exec.sh` or `python digital_ocean/exec.py`
   6. **Validate and troubleshoot**
      - Use `--dry-run` to preview actions without making changes
      - Review logs for errors and troubleshooting
      - Ensure all required variables are set in `.env`
      - For platform issues, see cross-platform notes below
   7. **Support**
      - For issues, see troubleshooting below or contact the project maintainer
   ```
3. Build and start all services:
   ```bash
   ./scripts/start.sh --build
   ```
4. View logs:
   ```bash
   ./scripts/logs.sh
   ```
5. Run health checks:
   ```bash
   ./scripts/health.sh
   ```
6. Run tests:
   ```bash
   ./scripts/test.sh
   ```

## Troubleshooting
- Use Bash, not PowerShell or Command Prompt.
- On Windows, use WSL or Git Bash.
- Ensure Docker Compose is v2.0.0 or newer.
- Review error messages for missing files or environment variables.
- See README.md for more details.

Additional operator-focused tips (routing, certs, health, allowlists):
- Certificate warnings on `https://${WEBSITE_DOMAIN}` are expected: Traefik uses Let's Encrypt **staging** ACME for this stack.
- If `https://${WEBSITE_DOMAIN}/api/health` fails, check that Traefik and the `api` container are healthy and inspect remote artifacts under `local_run_logs/`.
- If admin or pgAdmin subdomains time out or return 403, verify IP allowlist and basic auth variables in `.env` and re-run the relevant allowlist update scripts.

## DigitalOcean Deploy (Optional)
Automate droplet creation, DNS, and remote stack startup with Traefik-only public entrypoint.

**TLS & Certificates (Staging-Only Policy)**
- Traefik is configured to use **Lets Encrypt staging ACME** for this stack.
- Certificates are **staging-only** and will trigger browser warnings by design.
- **Production/real certificates are intentionally not issued** by this project.
- If you later adapt this for production, you must explicitly change the ACME configuration and update the documentation.

### One-command Deploy (Windows PowerShell)

```powershell
./digital_ocean/scripts/powershell/deploy.ps1
```

What it does:
- Creates/uses `.venv` and installs `digital_ocean/requirements.txt`
- Updates `PGADMIN_ALLOWLIST` to your public IP
- Runs `digital_ocean/orchestrate_deploy.py` (update-only by default)
- Verifies Traefik by fetching rendered configs and logs to local files:
   - Saves to `local_run_logs/`: `compose-ps.txt`, `traefik-env.txt`, `traefik-static.yml`, `traefik-dynamic.yml`, `traefik-logs.txt`

Options:

```powershell
./digital_ocean/scripts/powershell/deploy.ps1 -Full                 # full provision path in orchestrator
./digital_ocean/scripts/powershell/deploy.ps1 -SkipAllowlist        # skip allowlist IP update
./digital_ocean/scripts/powershell/deploy.ps1 -DropletIp 1.2.3.4    # override droplet IP detection
./digital_ocean/scripts/powershell/deploy.ps1 -SshKey "C:\path\to\key"  # custom SSH key path
```

### Preflight Validation (Optional)
Run preflight checks locally before deploying to catch misconfigurations early.

```powershell
# Human-readable
./digital_ocean/scripts/powershell/validate-predeploy.ps1 -EnvPath .\.env -ComposePath .\local.docker.yml

# Strict + JSON (CI-friendly)
./digital_ocean/scripts/powershell/validate-predeploy.ps1 -EnvPath .\.env -ComposePath .\local.docker.yml -Strict -Json

# Integrate with deploy (fails fast when preflight fails)
./digital_ocean/scripts/powershell/deploy.ps1 -Preflight
```

Manual invocation (advanced):

```bash
# Preview actions
python digital_ocean/orchestrate_deploy.py --dry-run

# Full deploy
python digital_ocean/orchestrate_deploy.py
```

After deploy:
- Frontend: `https://${WEBSITE_DOMAIN}` (staging cert; warning expected)
- API: `https://${WEBSITE_DOMAIN}/api`
- Verification artifacts: see the fetched files in the repo root
   - Stored under `local_run_logs/` (use `-Timestamped` for per-run subfolders)

Architecture summary (Option 1 + Option B):
- Django owns the schema, migrations, and admin UI (internal-only by default).
- FastAPI is the public API runtime and talks directly to Postgres.
- React is the public frontend and calls `https://${WEBSITE_DOMAIN}/api/...`.
- Traefik strips the `/api` prefix before forwarding requests to FastAPI, so FastAPI implements `/health`, `/users/...`, etc., without the `/api` prefix.

## Celery + Redis (Optional)
Add background task processing without increasing the attack surface. Redis and Celery are internal-only; Flower dashboard is disabled by default and guarded when enabled.

### Enable profiles
- Redis + worker:
   ```bash
   docker compose -f local.docker.yml --profile celery up -d redis celery-worker
   ```
- Flower (dashboard):
   ```bash
   docker compose -f local.docker.yml --profile flower up -d flower
   ```

### Environment keys
- Redis/Celery:
   - `REDIS_VERSION`, `REDIS_PORT`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `CELERY_CONCURRENCY`, `CELERY_LOG_LEVEL`
- Flower (optional):
   - `FLOWER_DNS_LABEL`, `FLOWER_BASIC_USERS` (htpasswd `user:hash`), `FLOWER_ALLOWLIST`

Update your allowlist to your current IP:
```powershell
./scripts/update-flower-allowlist.ps1
```

### Traefik routing (guarded)
- Flower is available at `https://${FLOWER_DNS_LABEL}.${WEBSITE_DOMAIN}` only when the `flower` profile is enabled.
- Access requires basic auth and the source IP must be allowlisted.

### Post-deploy tests
- Validate Flower security posture (401 unauth; 200/302 with auth):
```powershell
./digital_ocean/scripts/powershell/test.ps1 -EnvPath .\.env -Json -CheckCelery -AdminUser <user> -AdminPass <pass>
```
- Or via deploy wrapper:
```powershell
./digital_ocean/scripts/powershell/deploy.ps1 -RunTests -TestsJson -RunCeleryCheck
```

### API helpers (roundtrip task)
- Enqueue a ping task:
   ```bash
   curl -sk https://${WEBSITE_DOMAIN}/api/celery/ping | jq
   ```
- Poll result (replace <id>):
   ```bash
   curl -sk https://${WEBSITE_DOMAIN}/api/celery/result/<id> | jq
   ```

## Onboarding
- Recommended starting point:
   - `cp .env.example .env`
   - Set at minimum `WEBSITE_DOMAIN`, `TRAEFIK_CERT_EMAIL`, and secrets (`DJANGO_SECRET_KEY`, `JWT_SECRET`).
- Traefik is the only public entrypoint and publishes host ports **80/443 only**.
- Scripts automate all setup, build, start, stop, test, and log processes.
- All major scripts support a `--self-test` mode to verify environment and dependencies before running. Use this mode for troubleshooting and onboarding.
- `NETWORK_NAME` controls the Compose network name.
- If you change the network, update the Compose network key to match (variable substitution is not supported for YAML keys).
## Network Alignment
## Environment Variables (Quick Reference)

- **Domain**: `WEBSITE_DOMAIN=example.com`
- **Edge TLS (staging only)**: `TRAEFIK_CERT_EMAIL=you@example.com`
- **Frontend → API**: `REACT_APP_API_URL=https://${WEBSITE_DOMAIN}/api`
- **Ports (internal-only)**: `FASTAPI_PORT=5001`, `DJANGO_PORT=8000`, `POSTGRES_PORT=5432`
- **DB**: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- **API auth**: `JWT_SECRET`, `JWT_EXPIRE`
- **Admin guards**:
   - `TRAEFIK_DASH_BASIC_USERS` (htpasswd format)
   - `DJANGO_ADMIN_ALLOWLIST`, `PGADMIN_ALLOWLIST` (CIDR allowlists)
- Ensure `NETWORK_NAME` equals `TRAEFIK_DOCKER_NETWORK` in `.env`.
- If you change the network, update the compose network key to match (variable substitution is not supported for keys).

## Support
- For issues, see the troubleshooting section or contact the project maintainer.
