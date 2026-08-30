# Golden Path (All-Green Deploy)

This is the recommended end-to-end sequence to get a full green run: local bootstrap, config validation, deploy, and tests.

## Prereqs (host machine)

- Git
- PowerShell 7+ (Windows) or pwsh (macOS/Linux)
- Docker Desktop (running)
- Node.js 24.20.0+
- Python 3.12+

## 1) First-start (local bootstrap)

```powershell
./scripts/powershell/first-start.ps1
```

```bash
pwsh -ExecutionPolicy Bypass -File ./scripts/powershell/first-start.ps1
```

What it does (in order):

- Creates or recreates `.venv` (use `-ForceVenv` to rebuild)
- Activates `.venv` for the current shell session
- Installs Python deps (DigitalOcean automation)
- Installs Node deps in root, `react-app/`, and `e2e/`
- Runs `scripts/powershell/setup.ps1` to generate `.env`, generate secrets, and sync DO SSH keys

## 2) Required .env inputs

Provide these during setup prompts or fill them manually afterward:

- Core: `PROJECT_NAME`, `WEBSITE_DOMAIN`, `ENV`, `DEPLOY_MODE`
- Primary user: `USER_MAIN_EMAIL`, `USER_MAIN_PASSWORD`, `USER_MAIN_NAME`
- DigitalOcean: `DO_API_TOKEN`, `DO_API_REGION`, `DO_API_IMAGE`, `DO_API_SIZE`
- DO SSH: `DO_SSH_KEY_ID`, `DO_API_SSH_KEYS` (auto-filled when possible)

## 3) Validate config (recommended)

```bash
npm run setup:complete
npm run doctor
```

## 4) Deploy + tests (DigitalOcean)

```powershell
./digital_ocean/scripts/powershell/deploy.ps1 -Full -AllTests -Timestamped -LogsDir .\local_run_logs
```

High-level order:

- Loads `.env` and validates DO credentials
- Updates allowlists based on your public IP
- Creates or updates droplet and DNS
- Runs remote verification and pulls artifacts to `local_run_logs/`
- Runs post-deploy checks and local React/Jest + Playwright E2E tests

## 5) Confirm all-green

- `local_run_logs/<ip>-<timestamp>/meta/post-deploy-report.json` should have `success: true`
- `local_run_logs/<ip>-<timestamp>/smoke/external-edge-checks.json` should have `ok: true`

## Notes

- Keep the same PowerShell session open so `.venv` remains active.
- `-NonInteractive` on `scripts/powershell/setup.ps1` disables prompts; missing required values will fail fast.
- `APPLY_DEV_DEFAULTS=true` only affects `npm run setup:complete`, which will set `DJANGO_DEBUG=true` in development.
