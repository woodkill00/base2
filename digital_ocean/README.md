## Edit/Maintain

Run the edit/maintain script to update deployed resources:

```bash
python edit.py [--dry-run]
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
## Teardown

Run the teardown script to remove deployed resources:

```bash
python teardown.py [--dry-run]
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
     ```bash
     python -m venv .venv
     source .venv/bin/activate  # or .venv\Scripts\activate on Windows
     pip install -r requirements.txt
     ```
   - PyDo is required for API automation (see `requirements.txt`).
4. **(Optional) Node.js scripts**:
   - If using Node.js, run `npm install` in the relevant directory.


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
- (Optional) Node.js for frontend/backend scripts

### Setup Steps
1. **Clone the repository**
2. **Copy and edit environment variables**
    - `cp .env.example .env` (Linux/macOS) or copy manually on Windows
    - Fill in all required Digital Ocean variables in `.env` (see comments for guidance)
## Usage

### Deploy
Run deployment:
```bash
./scripts/deploy.sh [--dry-run]
# or
python digital_ocean/deploy.py [--dry-run]
```
`--dry-run` shows planned actions without making changes.
Error handling: exits nonzero if environment variables are missing or API fails. See logs for details.

### Teardown
Remove resources:
```bash
./scripts/teardown.sh [--dry-run]
# or
python digital_ocean/teardown.py [--dry-run]
```
`--dry-run` shows planned deletions. Error handling and rollback on failure.

### Edit/Maintain
Update resources:
```bash
./scripts/edit.sh
# or
python digital_ocean/edit.py
```
Error handling: logs errors, supports rollback.

### Info/Query
List namespaces, domains, and resource metadata:
```bash
./scripts/info.sh
# or
python digital_ocean/info.py
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
./scripts/exec.sh --droplet <id|name> --cmd <command>
./scripts/exec.sh --app <id|name> --service <service> --cmd <command>
# or
python digital_ocean/exec.py --droplet <id|name> --cmd <command>
python digital_ocean/exec.py --app <id|name> --service <service> --cmd <command>
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
All scripts use environment variables from `.env`—ensure your shell loads them correctly.

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
3. **Set up Python environment**:
   - Python 3.10+ required.
   - Create and activate a virtual environment:
     ```bash
     python -m venv .venv
     source .venv/bin/activate  # or .venv\Scripts\activate on Windows
     pip install -r requirements.txt
     ```
   - PyDo is required for API automation (see `requirements.txt`).
4. **(Optional) Node.js scripts**:
   - If using Node.js, run `npm install` in the relevant directory.

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
