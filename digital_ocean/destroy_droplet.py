#!/usr/bin/env python3
"""
Destroy a DigitalOcean droplet by ID.
Usage: python destroy_droplet.py <droplet_id>
Requires: pydo
"""
from dotenv import load_dotenv
load_dotenv()
import sys
from pydo import Client
import os

def log(msg):
    print(f"\033[1;31m[DO DESTROY]\033[0m {msg}")

def main():
    dry_run = False
    args = sys.argv[1:]
    if not args or len(args) > 2:
        log("Usage: python destroy_droplet.py <droplet_id> [--dry-run]")
        sys.exit(1)
    droplet_id = args[0]
    if len(args) == 2 and args[1] == "--dry-run":
        dry_run = True
    DO_API_TOKEN = os.getenv("DO_API_TOKEN")
    if not DO_API_TOKEN:
        log("DO_API_TOKEN not set in environment.")
        sys.exit(1)
    payload = {"droplet_id": droplet_id}
    if dry_run:
        import json
        log("[DRY RUN] Would send this payload to DigitalOcean API:")
        print(json.dumps(payload, indent=2))
        # Simulate expected response
        expected_response = {"status": "success", "droplet_id": droplet_id, "action": "destroy"}
        log("[DRY RUN] Expected response from DigitalOcean API:")
        print(json.dumps(expected_response, indent=2))
        sys.exit(0)
    client = Client(token=DO_API_TOKEN)
    try:
        log(f"Destroying droplet {droplet_id}...")
        # Correct pydo method is destroy, not delete
        resp = client.droplets.destroy(droplet_id)
        log(f"Droplet {droplet_id} destroy request sent. Response: {resp}")
    except Exception as e:
        log(f"Failed to destroy droplet: {e}")
        # Try to log any response if available
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
