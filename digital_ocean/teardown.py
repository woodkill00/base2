"""
Teardown Script for Digital Ocean (Apps/Droplets)
Automates removal of deployed resources using PyDo.

Usage:
    python teardown.py [--dry-run] [--help|-h]

    --dry-run   Show what would be deleted without making changes.
    --help      Show usage instructions.

Requires .env to be configured with all required Digital Ocean variables.
Exits nonzero on error.
"""
import os
from dotenv import load_dotenv
load_dotenv()
import sys
from pydo import Client
from digital_ocean.do_logging import logger
from digital_ocean.env_check import REQUIRED_VARS

def main():
    """
    Main entry point for teardown automation.
    Finds and deletes the droplet by name, with dry-run and rollback support.
    """
    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        print("Usage: python teardown.py [--dry-run]\nRemoves deployed resources from Digital Ocean using PyDo.")
        sys.exit(0)

    dry_run = "--dry-run" in sys.argv

    # Validate environment variables
    missing = [var for var in REQUIRED_VARS if not os.getenv(var)]
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)

    DO_API_TOKEN = os.getenv("DO_API_TOKEN")
    DO_APP_NAME = os.getenv("DO_APP_NAME")
    DO_API_REGION = os.getenv("DO_API_REGION", "nyc3")
    DO_API_IMAGE = os.getenv("DO_API_IMAGE", "docker-20-04")

    # Initialize Digital Ocean API client
    client = Client(token=DO_API_TOKEN)

    import time
    import random
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Starting teardown for app: {DO_APP_NAME} (attempt {attempt})")
            logger.debug(f"Teardown parameters: region={DO_API_REGION}, image={DO_API_IMAGE}")
            droplets = client.droplets.list()
            target = next((d for d in droplets['droplets'] if d['name'] == DO_APP_NAME), None)
            if not target:
                logger.error(f"No droplet found with name '{DO_APP_NAME}'")
                logger.warning("Teardown aborted: droplet not found.")
                print(f"[ERROR] No droplet found with name '{DO_APP_NAME}'", file=sys.stderr)
                sys.exit(2)
            droplet_id = target['id']
            if dry_run:
                logger.info(f"[DRY RUN] Would delete droplet '{DO_APP_NAME}' (ID: {droplet_id})")
                logger.debug("Dry run mode: no changes made.")
                print(f"[DRY RUN] Would delete droplet '{DO_APP_NAME}' (ID: {droplet_id})")
                sys.exit(0)
            logger.info(f"Deleting droplet '{DO_APP_NAME}' (ID: {droplet_id})")
            try:
                logger.info(f"Attempting to delete droplet '{DO_APP_NAME}' (ID: {droplet_id})")
                client.droplets.delete(droplet_id)
                logger.info(f"Droplet '{DO_APP_NAME}' deleted.")
                print(f"Droplet '{DO_APP_NAME}' deleted.")
            except Exception as delete_err:
                if 'rate limit' in str(delete_err).lower() and attempt < max_retries:
                    wait = 2 ** attempt + random.uniform(0, 1)
                    logger.warning(f"Rate limit hit, retrying in {wait:.1f}s...")
                    time.sleep(wait)
                    continue
                logger.error(f"Rollback failed: Could not delete droplet {droplet_id}: {delete_err}")
                logger.critical("Teardown rollback triggered due to deletion failure.")
                print(f"[ROLLBACK ERROR] Could not delete droplet {droplet_id}: {delete_err}", file=sys.stderr)
                sys.exit(4)
            break
        except Exception as e:
            if 'rate limit' in str(e).lower() and attempt < max_retries:
                wait = 2 ** attempt + random.uniform(0, 1)
                logger.warning(f"Rate limit hit, retrying in {wait:.1f}s...")
                time.sleep(wait)
                continue
            logger.error(f"Teardown failed: {e}")
            logger.critical("Teardown aborted due to unexpected error.")
            print(f"[ERROR] Teardown failed: {e}", file=sys.stderr)
            sys.exit(3)

if __name__ == "__main__":
    main()
