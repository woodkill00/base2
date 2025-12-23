
"""digital_ocean/deploy.py

Minimal DigitalOcean droplet deployment script.

This module is exercised by unit tests in `digital_ocean/tests/test_deploy.py`.
It intentionally keeps behavior simple and deterministic:

- Loads `.env` only when `main()` runs (so tests can patch `os.environ`).
- Exits with:
    - 0 on success / dry-run
    - 1 on missing required env vars
    - 2 on API errors
    - 4 on post-creation failure after a droplet was created (rollback attempted)
"""

import os
import sys

from dotenv import load_dotenv
from pydo import Client

from digital_ocean.do_logging import logger
from digital_ocean.env_check import REQUIRED_VARS

def main():
    # Load .env at runtime so tests can control os.environ via monkeypatch.
    load_dotenv(override=False)

    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        print("Usage: python deploy.py [--dry-run]\nDeploys a droplet to DigitalOcean using PyDo.")
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
    DO_API_IMAGE = os.getenv("DO_API_IMAGE")
    DO_DROPLET_SIZE = os.getenv("DO_DROPLET_SIZE") or os.getenv("DO_API_SIZE") or "s-1vcpu-1gb"

    if dry_run:
        logger.info(
            f"[DRY RUN] Would create droplet '{DO_APP_NAME}' in region '{DO_API_REGION}' "
            f"image='{DO_API_IMAGE}' size='{DO_DROPLET_SIZE}'"
        )
        print(
            f"[DRY RUN] Would create droplet '{DO_APP_NAME}' in region '{DO_API_REGION}' "
            f"image='{DO_API_IMAGE}' size='{DO_DROPLET_SIZE}'"
        )
        sys.exit(0)

    client = Client(token=DO_API_TOKEN)

    droplet_spec = {
        "name": DO_APP_NAME,
        "region": DO_API_REGION,
        "size": DO_DROPLET_SIZE,
        "image": DO_API_IMAGE,
    }

    droplet_id = None
    try:
        logger.info(f"Creating droplet: name={DO_APP_NAME} region={DO_API_REGION} image={DO_API_IMAGE} size={DO_DROPLET_SIZE}")
        resp = client.droplets.create(droplet_spec)
        droplet_id = ((resp or {}).get("droplet") or {}).get("id")
        logger.info(f"Droplet create requested. Droplet ID: {droplet_id}")
        print(f"Droplet create requested. Droplet ID: {droplet_id}")
        post_creation_hook()
    except Exception as e:
        # If we already created a droplet and a post-creation step failed, attempt rollback.
        if droplet_id:
            try:
                logger.warning(f"Post-creation failed; attempting rollback delete of droplet {droplet_id}: {e}")
                client.droplets.delete(droplet_id)
            except Exception as rollback_err:
                logger.error(f"Rollback failed for droplet {droplet_id}: {rollback_err}")
            print(f"[ERROR] Deploy failed after droplet creation: {e}", file=sys.stderr)
            sys.exit(4)

        logger.error(f"Droplet deployment failed: {e}")
        print(f"[ERROR] Droplet deployment failed: {e}", file=sys.stderr)
        sys.exit(2)

def post_creation_hook():
    """
    Placeholder for post-creation logic. Can be patched in tests to simulate errors after droplet creation.
    """
    pass

if __name__ == "__main__":
    main()
