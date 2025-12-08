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


## Onboarding Steps
1. **Clone the repository** and enter the project directory.
2. **Configure environment variables**:
   - Copy `.env.example` to `.env` and fill in all required Digital Ocean variables (see comments in `.env.example`).
   - Key variables: `DO_API_TOKEN`, `DO_API_REGION`, `DO_API_IMAGE`, `DO_APP_NAME`, etc.
   - Never commit `.env` to version control.
3. **Set up Python environment**:
   - Python 3.10+ required.
   - Create and activate a virtual environment:
     ```bash
     python -m venv .venv
     source .venv/bin/activate  # or .venv\Scripts\activate on Windows
     pip install -r requirements.txt
     ```
   - PyDo and pytest are required for automation and testing (see `requirements.txt`).
4. **(Optional) Node.js scripts**:
   - If using Node.js, run `npm install` in the relevant directory.
5. **Cross-platform usage**:
   - Windows: Use PowerShell for venv activation and script execution.
   - Mac/Linux: Use Bash or Zsh for venv activation and script execution.
   - Docker: All scripts work in containerized environments.


## Environment Variables Summary
| Variable         | Purpose/Usage                                 |
|------------------|-----------------------------------------------|
| DO_API_TOKEN     | API authentication (required)                 |
| DO_API_REGION    | Resource region (required, e.g., nyc3)        |
| DO_API_IMAGE     | Image slug for Droplets/Apps (required)       |
| DO_APP_NAME      | Name for deployed app (required)              |
| ...              | See `.env.example` for full list              |

## Usage

## Deployment Instructions

To deploy your app to Digital Ocean:

1. Ensure all required environment variables are set in `.env`.
2. Activate your Python virtual environment and install dependencies:

# ---
# Expanded Quickstart for Digital Ocean Integration

## Prerequisites
- Python 3.10+ (3.12 recommended)
- Digital Ocean account and API token

## Step-by-Step Onboarding
1. **Clone the repository**
2. **Copy and edit environment variables**
    - `cp .env.example .env` (Linux/macOS) or copy manually on Windows
    - Fill in all required Digital Ocean variables in `.env` (see comments for guidance)
3. **Create Python virtual environment**
    - `python -m venv .venv`
    - Activate: `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (Linux/macOS)
    - `pip install -r requirements.txt`
4. **Install Node.js dependencies** (if needed)
    - `cd react-app` or `cd backend`
    - `npm install`


## Usage
- **Deploy**: `./scripts/deploy.sh [--dry-run]` or `python deploy.py [--dry-run]`
   - `--dry-run` shows what would be deployed without making changes.
   - Shows errors if required environment variables are missing.
- **Teardown**: `./scripts/teardown.sh` or `python teardown.py`
- **Edit/Maintain**: `./scripts/edit.sh` or `python edit.py`
- **Info/Query**: `./scripts/info.sh` or `python info.py`
- **Exec**: `./scripts/exec.sh` or `python exec.py`

## Troubleshooting
- Ensure all required variables are set in `.env` (see `.env.example` for details)
- Check API token permissions and region/image slugs
- Review logs for error details
- For rate limit issues, adjust retry settings in `.env`

## Documentation
- See `README.md` for a summary and advanced usage
- See `specs/2-digital-ocean-integration/` for design and task breakdown

# ---
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```
3. Run the deployment script:
   ```bash
   cd digital_ocean/scripts
   ./deploy.sh
   # or
   python ../deploy.py
   ```
4. Monitor logs for deployment status and errors.


## Teardown Instructions

To remove your app from Digital Ocean:

1. Ensure all required environment variables are set in `.env`.
2. Activate your Python virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```
3. Run the teardown script:
   ```bash
   cd digital_ocean/scripts
   ./teardown.sh [--dry-run]
   # or
   python ../teardown.py [--dry-run]
   ```
   - `--dry-run` shows what would be deleted without making changes.
   - Errors are shown if required environment variables are missing or droplet is not found.
4. Monitor logs for teardown status and errors.

## Edit/Maintain Instructions

To update or maintain your app on Digital Ocean:

1. Ensure all required environment variables are set in `.env`.
2. Activate your Python virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```
3. Run the edit/maintain script:
   ```bash
   cd digital_ocean/scripts
   ./edit.sh
   # or
   python ../edit.py
   ```
4. Monitor logs for edit/maintain status and errors.

## Troubleshooting
- Missing or invalid environment variables will cause scripts to exit with an error.
- API errors: Check token, region, image, and permissions.
- Deployment failures: Check logs and API response codes.
- Rate limits: Adjust retry settings in `.env.example`.

## References
- [Digital Ocean API Docs](https://docs.digitalocean.com/reference/api/api-reference/)
- See `README.md` for more details and advanced usage.
