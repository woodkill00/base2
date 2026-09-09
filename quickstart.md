# Quickstart Guide

## Platform Requirements

- PowerShell 7+ (Windows) or `pwsh` (macOS/Linux)
- Bash shell for optional wrapper scripts (Mac, Linux, WSL, or Git Bash)
- Docker Engine 20.10+
- Docker Compose v2.0.0 or newer

## Setup Steps

1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```
2. Bootstrap tooling and configuration:

```powershell
./scripts/powershell/first-start.ps1
```

```bash
pwsh -ExecutionPolicy Bypass -File ./scripts/powershell/first-start.ps1
```

This orchestrates onboarding by:

- Creating/activating the `.venv` virtual environment (use `-ForceVenv` to recreate)
- Installing Python requirements (digital ocean automation)
- Installing Node packages in the repo root, `react-app/`, and `e2e/`
- Running `scripts/powershell/setup.ps1` (generates `.env` from `.env.example`, runs guided checks)
- Use `-SkipSetup` to hydrate dependencies without re-running the guided setup

During setup you may be prompted to confirm overwriting `.env` and to enter required values (DigitalOcean token, domain, emails, etc.). You can also edit `.env` manually afterward.

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

### Example prompt transcript (abridged)

This is a shortened example of the `scripts/setup.js` flow:

```
? Overwrite existing .env? (y/N) n
? Project name (lowercase, digits, hyphen): demo-app
? Website domain: demo.example.com
? Primary email (optional): owner@example.com
? Apply primary email to default fields? (y/N) y
? Primary password (optional, masked): ********
? Apply primary password to default fields? (y/N) y
? Primary username (optional): admin
? Apply primary username to default fields? (y/N) y
? Git repo URL (optional): https://github.com/org/repo.git
? Git repo branch (optional): main
? Environment: (development/staging/production) development
? Deploy mode: (local/digitalocean) digitalocean
? Apply safe dev defaults? (y/N) y
```

Afterward, keep the PowerShell session open so `.venv` stays active for any Python or Node command. Re-run the script when dependencies change.

Digital Ocean automation specifics:

- Ensure `.env` includes `DO_API_TOKEN`, `DO_API_REGION`, `DO_API_IMAGE`, `DO_APP_NAME`, etc.
- Use the `.venv` Python for commands: `(.venv) python digital_ocean/scripts/python/deploy.py [--dry-run]`, etc.
- Cross-platform notes: PowerShell on Windows, `pwsh`/Bash elsewhere. Scripts run in containers as well.
- See digital_ocean/README.md for troubleshooting, rate limits, and advanced usage.

## Onboarding Checklist

Follow these steps to get started quickly:

1. **Clone the repository**
   - `git clone <repo-url>`
   - `cd <repo-dir>`
2. **Run first-start orchestration**

- `./scripts/powershell/first-start.ps1` (PowerShell)
- `./scripts/bash/first-start.sh` (Bash)
- Re-run with `-ForceVenv` to rebuild the environment if needed.

3.  **Review `.env` output**

- Fill in required Digital Ocean variables (`DO_API_TOKEN`, `DO_API_REGION`, `DO_API_IMAGE`, `DO_APP_NAME`, etc.).

4. **Run automation scripts**

- Deploy: `./digital_ocean/scripts/bash/deploy.sh [--dry-run]` or `(.venv) python digital_ocean/scripts/python/deploy.py [--dry-run]`
- Teardown: `./digital_ocean/scripts/bash/teardown.sh [--dry-run]` or `(.venv) python digital_ocean/scripts/python/teardown.py [--dry-run]`
- Edit/Maintain: `./digital_ocean/scripts/bash/edit.sh` or `(.venv) python digital_ocean/scripts/python/edit.py`
- Info/Query: `./digital_ocean/scripts/bash/info.sh` or `(.venv) python digital_ocean/scripts/python/info.py`
- Exec: `./digital_ocean/scripts/bash/exec.sh` or `(.venv) python digital_ocean/scripts/python/exec.py`

3. **Validate and troubleshoot**
   - Use `--dry-run` to preview actions without changes.
   - Review logs for errors.
   - Ensure `.env` is complete.
   - For platform issues, see cross-platform notes.

4. **Support**
   - For issues, use the troubleshooting guidance or contact the maintainer.

5. Build and start all services:
   ```bash
   ./scripts/bash/start.sh --build
   ```
6. View logs:
   ```bash
   ./scripts/bash/logs.sh
   ```
7. Run health checks:
   ```bash
   ./scripts/bash/health.sh
   ```
8. Run tests:
   ```bash
   ./scripts/bash/test.sh
   ```

## Troubleshooting

- PowerShell entrypoints live in `scripts/powershell/` (use `pwsh` on macOS/Linux).
- Bash entrypoints live in `scripts/bash/` and work in WSL or Git Bash.
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
- Runs `digital_ocean/scripts/python/orchestrate_deploy.py` (update-only by default)
- Verifies Traefik by fetching rendered configs and logs to local files:
  - Saves to `local_run_logs/`: `compose-ps.txt`, `traefik-env.txt`, `traefik-static.yml`, `traefik-dynamic.yml`, `traefik-logs.txt`

Options:

```powershell
./digital_ocean/scripts/powershell/deploy.ps1 -Full                 # deploy existing or provision once, then stop for host-key enrollment
./digital_ocean/scripts/powershell/deploy.ps1 -SkipAllowlist        # skip allowlist IP update
./digital_ocean/scripts/powershell/deploy.ps1 -SshKey "C:\path\to\key"  # custom SSH key path
```

### Preflight Validation (Optional)

Run preflight checks locally before deploying to catch misconfigurations early.

```powershell
# Human-readable
./digital_ocean/scripts/powershell/validate-predeploy.ps1 -EnvPath .\.env -ComposePath .\development.docker.yml

# Strict + JSON (CI-friendly)
./digital_ocean/scripts/powershell/validate-predeploy.ps1 -EnvPath .\.env -ComposePath .\development.docker.yml -Strict -Json

# Integrate with deploy (fails fast when preflight fails)
./digital_ocean/scripts/powershell/deploy.ps1 -Preflight
```

Manual invocation (advanced):

```bash
# Preview actions
python digital_ocean/scripts/python/orchestrate_deploy.py --dry-run

# Full deploy
python digital_ocean/scripts/python/orchestrate_deploy.py
```

After deploy:

- Frontend: `https://${WEBSITE_DOMAIN}` (staging cert; warning expected)
- API: `https://${WEBSITE_DOMAIN}/api`
- Verification artifacts: see the fetched files in the repo root
  - Stored under `local_run_logs/` (use `-Timestamped` for per-run subfolders)

Architecture summary (Option 1-only):

- Django owns the schema, migrations, and admin UI (internal-only by default).
- FastAPI is the public API runtime and talks directly to Postgres.
- React is the public frontend and calls `https://${WEBSITE_DOMAIN}/api/...`.
- Traefik routes `/api/*` to FastAPI without stripping `/api`, so FastAPI serves `/api/health`, `/api/users/...`, etc.

## Celery + Redis (Optional)

Add background task processing without increasing the attack surface. Redis and Celery are internal-only; Flower dashboard is disabled by default and guarded when enabled.

### Enable profiles

- Redis + worker:
  ```bash
  docker compose -f development.docker.yml --profile celery up -d redis celery-worker
  ```
- Flower (dashboard):
  ```bash
  docker compose -f development.docker.yml --profile flower up -d flower
  ```

### Environment keys

- Redis/Celery:
  - `REDIS_VERSION`, `REDIS_PORT`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `CELERY_CONCURRENCY`, `CELERY_LOG_LEVEL`
- Flower (optional):
  - `FLOWER_DNS_LABEL`, `FLOWER_BASIC_USERS` (htpasswd `user:hash`), `FLOWER_ALLOWLIST`

Update your allowlist to your current IP:

```powershell
./scripts/powershell/update-flower-allowlist.ps1
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
