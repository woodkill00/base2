## Edit/Maintain

Run the edit/maintain script to update deployed resources (always activate `.venv` first):

```bash
(.venv) python digital_ocean/scripts/python/edit.py [--dry-run]
# or
./digital_ocean/scripts/bash/edit.sh [--dry-run]
```

**Options:**

- `--dry-run`: Show what would be updated without making changes.

**Environment:**

- Requires all Digital Ocean variables in `.env`.

**Error Handling:**

- Exits nonzero on error. See logs for details.

**Rollback:**

- If update fails, rollback logic will log the error and exit with code 4.

**Windows:**

- Use PowerShell for venv activation and script execution.

**Mac/Linux:**

- Use Bash or Zsh for venv activation and script execution.

**Docker:**

- All scripts work in containerized environments.

## Experimental tools

Experimental or stubbed scripts live in [digital_ocean/experimental](experimental/README.md). These are not part of the supported automation path and may change without notice.

## Teardown

Run the teardown script to remove deployed resources:

```bash
(.venv) python digital_ocean/scripts/python/teardown.py [--dry-run]
# or
./digital_ocean/scripts/bash/teardown.sh [--dry-run]
```

**Options:**

- `--dry-run`: Show what would be deleted without making changes.

**Environment:**

- Requires all Digital Ocean variables in `.env`.

**Error Handling:**

- Exits nonzero on error. See logs for details.

**Rollback:**

- If deletion fails, rollback logic will log the error and exit with code 4.

**Windows:**

- Use PowerShell for venv activation and script execution.

**Mac/Linux:**

- Use Bash or Zsh for venv activation and script execution.

**Docker:**

- All scripts work in containerized environments.

## Onboarding & Setup

1. **Clone the repository** and enter the project directory.
2. **Configure environment variables**:
   - Copy `.env.example` to `.env` and fill in all required Digital Ocean variables (see comments in `.env.example`).
   - Key variables: `DO_API_TOKEN`, `DO_API_REGION`, `DO_API_IMAGE`, `DO_APP_NAME`, etc.
3. **Set up Python environment**:
   - Python 3.10+ required.
   - Create and activate a virtual environment:
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     .\.venv\Scripts\python.exe -m pip install --require-hashes -r digital_ocean\requirements.lock
     ```
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     pip install --require-hashes -r digital_ocean/requirements.lock
     ```
   - Keep `.venv` active for every pip install or Python command in this directory.
4. **(Optional) Node.js scripts**:
   - If using Node.js, run `npm install` in the relevant directory.

### DigitalOcean SSH key sync (runs during setup)

This step runs inside [scripts/powershell/setup.ps1](../scripts/powershell/setup.ps1) after .env is written. It calls [scripts/powershell/add-ssh-key.ps1](scripts/powershell/add-ssh-key.ps1) and uses [scripts/python/DO_ssh_keys.py](scripts/python/DO_ssh_keys.py).

What it does (ordered):

- Determines the key name from PROJECT_NAME (fallback: do-ssh).
- Ensures a local SSH key exists at ~/.ssh/<keyName> (creates ED25519 key if missing).
- Queries DigitalOcean for matching keys (same name and public key).
- If a mismatch exists, deletes old DO keys and registers the local key.
- Updates .env with DO_SSH_KEY_ID and DO_API_SSH_KEYS.

Why it exists:

- Droplet provisioning requires a valid DO SSH key; this keeps local and DO keys in sync automatically.

### Setup prompts (interactive)

The interactive questions come from [scripts/setup.js](../scripts/setup.js) (invoked by [scripts/powershell/setup.ps1](../scripts/powershell/setup.ps1)). These are the exact prompts and choices:

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

After writing .env, [scripts/setup.js](../scripts/setup.js) prints a checklist of required categories and recommends running:

- npm run setup:complete
- npm run doctor

Tip: `scripts/powershell/first-start.ps1 -Help` and `scripts/powershell/setup.ps1 -Help` print usage details.

### Golden path (all-green deploy)

See the full end-to-end sequence in [docs/GOLDEN_PATH.md](../docs/GOLDEN_PATH.md).

## Environment Variables

See `.env.example` for a complete, commented list. All required variables must be set in `.env` before running any scripts.

### Required Digital Ocean Variables

- `DO_API_TOKEN`: Personal access token from Digital Ocean dashboard (required)
- `DO_API_REGION`: Default region for resources (e.g., nyc3, sfo2) (required)
- `DO_API_IMAGE`: Default image slug for Droplets/Apps (required)
- `DO_APP_NAME`: Name for deployed app (required)

### Optional/Advanced Variables

- See `.env.example` for all optional and advanced configuration options.

## Usage

Activate the repo virtual environment before running any command below (PowerShell: `.\.venv\Scripts\Activate.ps1`, Bash: `source .venv/bin/activate`). If activation is not possible, prefix commands with `.\.venv\Scripts\python.exe` instead of `python`.

## Troubleshooting

### Cross-Platform Compatibility

Scripts are tested on Windows (PowerShell, Bash), Mac, Linux, and Docker containers.
For Windows, use PowerShell to activate Python venv and run scripts. For Bash, use WSL or Git Bash.
All scripts use environment variables from `.env`—ensure your shell loads them correctly.

### Security Audit

No secrets are logged; all API calls use HTTPS.
Ensure your `.env` is not committed to version control.
API tokens should have least-privilege permissions.

### Onboarding & Troubleshooting

Ensure all required variables are set in `.env` (see `.env.example` for details)
Check API token permissions and region/image slugs
Review logs for error details
For rate limit issues, adjust retry settings in `.env`

## Digital Ocean Integration: Expanded Onboarding

### Prerequisites

- Python 3.10+ (recommended: 3.12)
- Digital Ocean account and API token
- (Optional) Node.js for frontend scripts

### Setup Steps

1. **Clone the repository**
2. **Copy and edit environment variables**
   - `cp .env.example .env` (Linux/macOS) or copy manually on Windows
   - Fill in all required Digital Ocean variables in `.env` (see comments for guidance)

## Usage

### Deploy

Run deployment:

```bash
./digital_ocean/scripts/bash/deploy.sh [options]
# or
(.venv) python digital_ocean/scripts/python/deploy.py [--dry-run]
```

Bash MVP flags:

- `--dry-run`
- `--update-only`
- `--full` (default when no deploy mode is specified)
- `--env-path <path>` (sets `ENV_PATH` for the orchestrator)
- `--logs-dir <path>` (sets `DEPLOY_ARTIFACT_DIR`)
- `--timestamped` (append a timestamp to the logs dir)

`--dry-run` shows planned actions without making changes.
Error handling: exits nonzero if environment variables are missing or API fails. See logs for details.

### Teardown

Remove resources:

```bash
./digital_ocean/scripts/bash/teardown.sh [--dry-run]
# or
(.venv) python digital_ocean/scripts/python/teardown.py [--dry-run]
```

`--dry-run` shows planned deletions. Error handling and rollback on failure.

### Edit/Maintain

Update resources:

```bash
./digital_ocean/scripts/bash/edit.sh
# or
(.venv) python digital_ocean/scripts/python/edit.py
```

Error handling: logs errors, supports rollback.

### Info/Query

List namespaces, domains, and resource metadata:

```bash
./digital_ocean/scripts/bash/info.sh
# or
(.venv) python digital_ocean/scripts/python/info.py
```

Output example:

```
Namespaces: ["project1", "project2"]
Domains: ["example.com", "test.com"]
Resources: {"droplets": ["droplet1"], "apps": ["app1"], "volumes": ["vol1"]}
```

Error handling: exits nonzero if environment variables are missing or API fails.

### Exec

Run commands in droplets (via SSH) or apps (if supported):

```bash
./digital_ocean/scripts/bash/exec.sh --droplet <id|name> --cmd <command>
./digital_ocean/scripts/bash/exec.sh --app <id|name> --service <service> --cmd <command>
# or
(.venv) python digital_ocean/scripts/python/exec.py --droplet <id|name> --cmd <command>
(.venv) python digital_ocean/scripts/python/exec.py --app <id|name> --service <service> --cmd <command>
```

Output example (droplet):

```
[INFO] Use SSH: ssh root@<droplet_ip> 'ls -l'
```

Output example (app):

```
[INFO] App Platform exec not supported via PyDo. Use 'doctl' CLI or dashboard.
```

Error handling: exits nonzero if arguments are invalid or API fails.

## Troubleshooting

### Cross-Platform Compatibility

Scripts are tested on Windows (PowerShell, Bash), Mac, Linux, and Docker containers.
Windows: Use PowerShell for venv activation and script execution. Bash: Use WSL or Git Bash. Docker: All scripts work in containers.

### Security Audit

No secrets are logged; all API calls use HTTPS. `.env` should not be committed. API tokens should have least-privilege permissions.

### Onboarding & Troubleshooting

Ensure all required variables are set in `.env` (see `.env.example`).
Check API token permissions and region/image slugs.
Review logs for error details.
For rate limit issues, adjust retry settings in `.env`.
Test with invalid/missing API token, resource name conflicts, and deleted resources for robust error handling.

## Onboarding & Setup

1. **Clone the repository** and enter the project directory.
2. **Configure environment variables**:
   - Copy `.env.example` to `.env` and fill in all required Digital Ocean variables (see comments in `.env.example`).
   - Key variables: `DO_API_TOKEN`, `DO_API_REGION`, `DO_API_IMAGE`, `DO_APP_NAME`, etc.
3. **Run first-start orchestration**:
   - `./scripts/powershell/first-start.ps1` (PowerShell) or `pwsh -ExecutionPolicy Bypass -File ./scripts/powershell/first-start.ps1`
   - Creates/activates `.venv`, installs Python/Node dependencies, and runs the guided setup.
   - Use `-SkipSetup` if you only need to hydrate dependencies.
   - Keep `.venv` active for every pip install or Python command referenced in this README.
4. **(Optional) Node.js scripts**:
   - Additional `npm install` runs are only needed if you maintain custom directories beyond the defaults handled by `first-start`.

## Environment Variables

See `.env.example` for a complete, commented list. All required variables must be set in `.env` before running any scripts.

### Required Digital Ocean Variables

- `DO_API_TOKEN`: Personal access token from Digital Ocean dashboard (required)
- `DO_API_REGION`: Default region for resources (e.g., nyc3, sfo2) (required)
- `DO_API_IMAGE`: Default image slug for Droplets/Apps (required)
- `DO_APP_NAME`: Name for deployed app (required)

### Optional/Advanced Variables

See `.env.example` for all optional and advanced configuration options.

## Documentation

- See `quickstart.md` for step-by-step onboarding
- See `specs/2-digital-ocean-integration/` for design and task breakdown

---
