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
      - If using frontend/backend scripts, run `npm install` in the relevant directory
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
   cp .env.example .env
   # Edit .env to set your values
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

## Onboarding
- All required environment variables are documented in `.env.example`.
- Scripts automate all setup, build, start, stop, test, and log processes.
- All major scripts support a `--self-test` mode to verify environment and dependencies before running. Use this mode for troubleshooting and onboarding.
- No manual steps outside documented scripts.

## Support
- For issues, see the troubleshooting section or contact the project maintainer.
