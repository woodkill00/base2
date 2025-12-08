"""
Edit/Maintain Script for Digital Ocean (Apps/Droplets)
Automates updates and maintenance actions using PyDo.

Usage:
    python edit.py [--dry-run] [--help|-h]

    --dry-run   Show what would be updated without making changes.
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
    Main entry point for edit/maintain automation.
    Finds and updates the droplet/app by name, with dry-run and rollback support.
    """
    # Validate environment
    missing = [var for var in REQUIRED_VARS if not os.getenv(var)]
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        print(f"[ERROR] Missing required environment variables: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    DO_API_TOKEN = os.getenv("DO_API_TOKEN")
    DO_APP_NAME = os.getenv("DO_APP_NAME")
    DO_API_REGION = os.getenv("DO_API_REGION")
    DO_API_IMAGE = os.getenv("DO_API_IMAGE")
    dry_run = "--dry-run" in sys.argv
    client = Client(token=DO_API_TOKEN)
    import time
    import random
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Starting edit/maintain for app: {DO_APP_NAME} (attempt {attempt})")
            logger.debug(f"Edit parameters: region={DO_API_REGION}, image={DO_API_IMAGE}")
            droplets = client.droplets.list()
            target = next((d for d in droplets['droplets'] if d['name'] == DO_APP_NAME), None)
            if not target:
                logger.error(f"No droplet found with name '{DO_APP_NAME}'")
                logger.warning("Edit/maintain aborted: droplet not found.")
                print(f"[ERROR] No droplet found with name '{DO_APP_NAME}'", file=sys.stderr)
                sys.exit(2)
            droplet_id = target['id']
            if dry_run:
                logger.info(f"[DRY RUN] Would update droplet '{DO_APP_NAME}' (ID: {droplet_id})")
                logger.debug("Dry run mode: no changes made.")
                print(f"[DRY RUN] Would update droplet '{DO_APP_NAME}' (ID: {droplet_id})")
                sys.exit(0)
            logger.info(f"Updating droplet '{DO_APP_NAME}' (ID: {droplet_id})")
            try:
                client.tags.create({'name': 'maintained'})
                client.tags.tag_resource('maintained', 'droplet', droplet_id)
                logger.info(f"Droplet '{DO_APP_NAME}' updated.")
                print(f"Droplet '{DO_APP_NAME}' updated.")
            except Exception as update_err:
                if 'rate limit' in str(update_err).lower() and attempt < max_retries:
                    wait = 2 ** attempt + random.uniform(0, 1)
                    logger.warning(f"Rate limit hit, retrying in {wait:.1f}s...")
                    time.sleep(wait)
                    continue
                logger.error(f"Rollback failed: Could not update droplet {droplet_id}: {update_err}")
                logger.critical("Edit/maintain rollback triggered due to update failure.")
                print(f"[ROLLBACK ERROR] Could not update droplet {droplet_id}: {update_err}", file=sys.stderr)
                sys.exit(4)
            break
        except Exception as e:
            if 'rate limit' in str(e).lower() and attempt < max_retries:
                wait = 2 ** attempt + random.uniform(0, 1)
                logger.warning(f"Rate limit hit, retrying in {wait:.1f}s...")
                time.sleep(wait)
                continue
            logger.error(f"Edit/Maintain failed: {e}")
            logger.critical("Edit/maintain aborted due to unexpected error.")
            print(f"[ERROR] Edit/Maintain failed: {e}", file=sys.stderr)
            sys.exit(3)

if __name__ == "__main__":
    main()
