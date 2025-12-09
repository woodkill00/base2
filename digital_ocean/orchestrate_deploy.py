#!/usr/bin/env python3
"""
Orchestrate Digital Ocean Droplet deployment, DNS update, .env generation, and service startup.
- Requires: pydo, paramiko (for SSH/SCP), python-dotenv
- Usage: python orchestrate_deploy.py
"""

import os
from pathlib import Path
import subprocess
from dotenv import load_dotenv
load_dotenv()
# --- SSH Key Generation and .env Update ---
PROJECT_NAME = os.getenv("PROJECT_NAME", "base2")
ssh_dir = os.path.expanduser("~/.ssh")
ssh_key_path = os.path.join(ssh_dir, PROJECT_NAME)
pub_key_path = ssh_key_path + ".pub"

# Generate SSH key if it does not exist
if not os.path.exists(ssh_key_path) or not os.path.exists(pub_key_path):
    os.makedirs(ssh_dir, exist_ok=True)
    print(f"[INFO] Generating SSH key: {ssh_key_path}")
    subprocess.run(["ssh-keygen", "-t", "ed25519", "-f", ssh_key_path, "-N", ""], check=True)
else:
    print(f"[INFO] SSH key already exists: {ssh_key_path}")

# Read public key
with open(pub_key_path, "r") as f:
    pubkey = f.read().strip()

# Update DO_API_SSH_KEYS in .env
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.env"))
with open(env_path, "r") as f:
    lines = f.readlines()
found = False
for i, line in enumerate(lines):
    if line.strip().startswith("DO_API_SSH_KEYS"):
        lines[i] = f"DO_API_SSH_KEYS={pubkey}\n"
        found = True
        break
if not found:
    lines.append(f"DO_API_SSH_KEYS={pubkey}\n")
with open(env_path, "w") as f:
    f.writelines(lines)
import time
from pydo import Client
import paramiko
from dotenv import dotenv_values, set_key

def log(msg):
    print(f"\033[1;32m[INFO]\033[0m {msg}")

def err(msg):
    print(f"\033[1;31m[ERROR]\033[0m {msg}", flush=True)
DO_API_TOKEN = os.getenv("DO_API_TOKEN")
DO_DOMAIN = os.getenv("DO_DOMAIN")  # e.g. example.com
DO_DROPLET_NAME = os.getenv("DO_DROPLET_NAME", "base2-droplet")
DO_API_REGION = os.getenv("DO_API_REGION", "nyc3")
DO_API_SIZE = os.getenv("DO_API_SIZE", "s-1vcpu-1gb")
DO_API_IMAGE = os.getenv("DO_API_IMAGE", "ubuntu-22-04-x64")
import sys
DRY_RUN = "--dry-run" in sys.argv
if DRY_RUN:
    print("\033[1;32m[INFO]\033[0m [DRY RUN] No changes will be made. Printing planned actions only.")
DO_SSH_KEY_ID = os.getenv("DO_SSH_KEY_ID")
DO_API_SSH_KEYS = os.getenv("DO_API_SSH_KEYS")

# Determine SSH key(s) for droplet
ssh_keys = []
if DO_SSH_KEY_ID and DO_SSH_KEY_ID.strip():
    ssh_keys = [DO_SSH_KEY_ID.strip()]
elif DO_API_SSH_KEYS and DO_API_SSH_KEYS.strip():
    ssh_keys = [DO_API_SSH_KEYS.strip()]
else:
    err("No valid SSH key identifier found. Set DO_SSH_KEY_ID (numeric ID or fingerprint) or DO_API_SSH_KEYS (public key string) in your .env file.")
    exit(1)
LOCAL_ENV_PATH = os.getenv("LOCAL_ENV_PATH", os.path.abspath(os.path.join(os.path.dirname(__file__), "../.env")))
REMOTE_ENV_PATH = "/srv/backend/.env"  # Adjust as needed for your droplet
SSH_USER = os.getenv("SSH_USER", "root")

client = Client(token=DO_API_TOKEN)

# --- 1. Create Droplet ---
droplet_spec = {
    "name": DO_DROPLET_NAME,
    "region": DO_API_REGION,
    "size": DO_API_SIZE,
    "image": DO_API_IMAGE,
    "ssh_keys": ssh_keys,
    "tags": ["base2"],
}

log("Creating droplet...")
try:
    droplet = client.droplets.create(droplet_spec)
    droplet_id = droplet["droplet"]["id"]
except Exception as e:
    err(f"Droplet creation failed: {e}")
    exit(1)

ip_address = None  # Will be set after droplet is active

log("Waiting for droplet to become active...")
while True:
    droplet_info = client.droplets.get(droplet_id)["droplet"]
    if droplet_info["status"] == "active":
        break
    time.sleep(5)
    print("...", flush=True)

ip_address = droplet_info["networks"]["v4"][0]["ip_address"]
log(f"Droplet IP: {ip_address}")

# --- 3. Update DNS Records ---
log("Updating DNS A/AAAA records for domain and www...")
try:
    records = client.domains.list_records(DO_DOMAIN)["domain_records"]
    v6_list = droplet_info["networks"].get("v6", [])
    ipv6_address = v6_list[0]["ip_address"] if v6_list else None

    # Track which records exist
    found = {"A_root": None, "A_www": None, "AAAA_root": None}
    updated = {"A_root": False, "A_www": False, "AAAA_root": False}

    for record in records:
        # Root A record
        if record["type"] == "A" and (record["name"] == "@" or record["name"] == DO_DOMAIN or record["name"] == ""):
            found["A_root"] = record
            if DRY_RUN:
                log(f"[DRY RUN] Would update root A record ({record['name']}) -> {ip_address}")
            else:
                client.domains.update_record(DO_DOMAIN, record["id"], {
                    "type": "A",
                    "name": record["name"],
                    "data": ip_address
                })
                log(f"Updated root A record ({record['name']}) -> {ip_address}")
            updated["A_root"] = True
        # www A record
        if record["type"] == "A" and (record["name"] == "www" or record["name"] == f"www.{DO_DOMAIN}"):
            found["A_www"] = record
            if DRY_RUN:
                log(f"[DRY RUN] Would update www A record ({record['name']}) -> {ip_address}")
            else:
                client.domains.update_record(DO_DOMAIN, record["id"], {
                    "type": "A",
                    "name": record["name"],
                    "data": ip_address
                })
                log(f"Updated www A record ({record['name']}) -> {ip_address}")
            updated["A_www"] = True
        # Root AAAA record
        if record["type"] == "AAAA" and (record["name"] == "@" or record["name"] == DO_DOMAIN or record["name"] == ""):
            found["AAAA_root"] = record
            if ipv6_address:
                if DRY_RUN:
                    log(f"[DRY RUN] Would update root AAAA record ({record['name']}) -> {ipv6_address}")
                else:
                    client.domains.update_record(DO_DOMAIN, record["id"], {
                        "type": "AAAA",
                        "name": record["name"],
                        "data": ipv6_address
                    })
                    log(f"Updated root AAAA record ({record['name']}) -> {ipv6_address}")
                updated["AAAA_root"] = True

    # Create missing records
    if not found["A_root"]:
        if DRY_RUN:
            log(f"[DRY RUN] Would create root A record (@) -> {ip_address}")
        else:
            client.domains.create_record(DO_DOMAIN, {
                "type": "A",
                "name": "@",
                "data": ip_address
            })
            log(f"Created root A record (@) -> {ip_address}")
    if not found["A_www"]:
        if DRY_RUN:
            log(f"[DRY RUN] Would create www A record (www) -> {ip_address}")
        else:
            client.domains.create_record(DO_DOMAIN, {
                "type": "A",
                "name": "www",
                "data": ip_address
            })
            log(f"Created www A record (www) -> {ip_address}")
    if ipv6_address and not found["AAAA_root"]:
        if DRY_RUN:
            log(f"[DRY RUN] Would create root AAAA record (@) -> {ipv6_address}")
        else:
            client.domains.create_record(DO_DOMAIN, {
                "type": "AAAA",
                "name": "@",
                "data": ipv6_address
            })
            log(f"Created root AAAA record (@) -> {ipv6_address}")
    if not updated["A_root"] and not updated["A_www"] and not updated["AAAA_root"]:
        log("No A/AAAA records for root or www found to update or create.")
except Exception as e:
    err(f"DNS update failed: {e}")
    exit(1)
