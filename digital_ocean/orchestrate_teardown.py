#!/usr/bin/env python3
"""
Tear down DigitalOcean droplet and related resources for this project.
- Deletes droplet named DO_DROPLET_NAME
- Optionally cleans A/AAAA records for @, www, traefik if --clean-dns is provided
Requirements: pydo, python-dotenv
Usage:
  python digital_ocean/orchestrate_teardown.py [--clean-dns]
"""
import os
import sys
import time
import re
from dotenv import load_dotenv
from pydo import Client

load_dotenv()


_ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _expand_env_templates(value: str, env: dict | None = None) -> str:
    if value is None:
        return value
    env_map = env or os.environ
    current = str(value)
    for _ in range(5):
        next_value = _ENV_VAR_PATTERN.sub(lambda m: env_map.get(m.group(1), m.group(0)), current)
        if next_value == current:
            break
        current = next_value
    return current

DO_API_TOKEN = os.getenv("DO_API_TOKEN")
PROJECT_NAME = os.getenv("PROJECT_NAME", "base2")
_EXPANSION_ENV = {**os.environ, "PROJECT_NAME": PROJECT_NAME}
DO_DOMAIN = _expand_env_templates(os.getenv("DO_DOMAIN"), _EXPANSION_ENV)
DO_DROPLET_NAME = _expand_env_templates(os.getenv("DO_DROPLET_NAME", "base2-droplet"), _EXPANSION_ENV)
CLEAN_DNS = "--clean-dns" in sys.argv

client = Client(token=DO_API_TOKEN)

def log(msg: str):
    print(f"\033[1;32m[INFO]\033[0m {msg}")

def err(msg: str):
    print(f"\033[1;31m[ERROR]\033[0m {msg}", flush=True)

# Find droplet by name
try:
    log(f"Searching for droplet named '{DO_DROPLET_NAME}'...")
    droplet_id = None
    page = 1
    while True:
        resp = client.droplets.list(page=page, per_page=50)
        for d in resp.get("droplets", []):
            if d.get("name") == DO_DROPLET_NAME:
                droplet_id = d.get("id")
                ip = None
                nets = d.get("networks", {}).get("v4", [])
                if nets:
                    ip = nets[0].get("ip_address")
                log(f"Found droplet id={droplet_id}, ip={ip}")
                break
        if droplet_id or not resp.get("links", {}).get("pages", {}).get("next"):
            break
        page += 1
    if not droplet_id:
        log("Droplet not found; nothing to delete.")
    else:
        log(f"Deleting droplet id={droplet_id}...")
        client.droplets.delete(droplet_id)
        # Poll until gone
        for _ in range(30):
            exists = False
            resp = client.droplets.list(page=1, per_page=50)
            for d in resp.get("droplets", []):
                if d.get("id") == droplet_id:
                    exists = True
                    break
            if not exists:
                log("Droplet deleted.")
                break
            time.sleep(5)
        else:
            err("Timed out waiting for droplet deletion confirmation.")
except Exception as e:
    err(f"Droplet deletion failed: {e}")

# Optionally clean DNS records (A/AAAA for @, www, traefik)
if CLEAN_DNS and DO_DOMAIN:
    try:
        log(f"Cleaning DNS A/AAAA records on domain {DO_DOMAIN} for @, www, traefik...")
        recs = client.domains.list_records(DO_DOMAIN)["domain_records"]
        targets = set(["@", "www", "traefik"])  # names to delete for A/AAAA
        for r in recs:
            if r.get("type") in ("A", "AAAA") and r.get("name") in targets:
                log(f"Deleting {r['type']} record '{r['name']}' (id={r['id']})")
                client.domains.delete_record(DO_DOMAIN, r["id"])
        log("DNS cleanup complete.")
    except Exception as e:
        err(f"DNS cleanup failed: {e}")
else:
    log("DNS cleanup skipped (use --clean-dns to enable).")

log("Teardown complete.")
