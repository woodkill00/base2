
"""
Deployment Script for Digital Ocean (Apps API)
Uses PyDo to automate deployment of containerized app.

Usage:
    python deploy.py [--dry-run] [--help|-h]

Exits nonzero on error. Requires .env to be configured.
"""
import os
from dotenv import load_dotenv
load_dotenv()
import sys
from pydo import Client
from digital_ocean.do_logging import logger
from digital_ocean.env_check import REQUIRED_VARS

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        print("Usage: python deploy.py [--dry-run]\nDeploys app to Digital Ocean using PyDo.")
        sys.exit(0)

    dry_run = "--dry-run" in sys.argv

    # Validate environment
    missing = [var for var in REQUIRED_VARS if not os.getenv(var)]
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)

    DO_API_TOKEN = os.getenv("DO_API_TOKEN")
    DO_APP_NAME = os.getenv("DO_APP_NAME")
    DO_API_REGION = os.getenv("DO_API_REGION", "nyc3")
    DO_GIT_REPO = os.getenv("DO_GIT_REPO")

    if dry_run:
        logger.info(f"[DRY RUN] Would deploy app '{DO_APP_NAME}' from repo '{DO_GIT_REPO}' in region '{DO_API_REGION}'")
        print(f"[DRY RUN] Would deploy app '{DO_APP_NAME}' from repo '{DO_GIT_REPO}' in region '{DO_API_REGION}'")
        sys.exit(0)

    client = Client(token=DO_API_TOKEN)

    app_spec = {
        "spec": {
            "name": DO_APP_NAME,
            "region": DO_API_REGION,
            "services": [{
                "name": "web",
                "git": {
                    "repo_clone_url": DO_GIT_REPO,
                    "branch": "main"  # You can make this configurable
                },
                "run_command": "",  # Optionally set your run command
                "envs": []
            }]
        }
    }
    try:
        logger.info(f"Starting App Platform deployment for app: {DO_APP_NAME} from repo: {DO_GIT_REPO}")
        app = client.apps.create(app_spec)
        app_id = app['app']['id'] if 'app' in app and 'id' in app['app'] else None
        logger.info(f"App Platform deployment started. App ID: {app_id}")
        print(f"App Platform deployment started. App ID: {app_id}")
        post_creation_hook()
    except Exception as e:
        logger.error(f"App Platform deployment failed: {e}")
        print(f"[ERROR] App Platform deployment failed: {e}", file=sys.stderr)
        sys.exit(2)

def post_creation_hook():
    """
    Placeholder for post-creation logic. Can be patched in tests to simulate errors after droplet creation.
    """
    pass

if __name__ == "__main__":
    main()
