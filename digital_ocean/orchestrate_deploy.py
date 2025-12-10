#!/usr/bin/env python3
"""
Orchestrate Digital Ocean Droplet deployment, DNS update, .env generation, and service startup.
- Requires: pydo, paramiko (for SSH/SCP), python-dotenv
- Usage: python orchestrate_deploy.py
"""

import os
import json
from pathlib import Path
import subprocess
from dotenv import load_dotenv
# Load .env
load_dotenv()
def log_json(label, data):
    print(f"\033[1;36m[DEBUG]\033[0m {label}: {json.dumps(data, indent=2)}")

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
    # --- Automatic recovery routine ---
    try:
        print("[RECOVERY] Attempting SSH recovery and diagnostics...")
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(ip_address, username=SSH_USER, key_filename=ssh_key_path)
        # Check logs
        for log_path in ["/var/log/cloud-init-output.log", "/var/log/do_base.log"]:
            print(f"[RECOVERY] Checking {log_path}...")
            stdin, stdout, stderr = ssh_client.exec_command(f"tail -n 100 {log_path}")
            print(stdout.read().decode())
            err_out = stderr.read().decode()
            if err_out:
                print(f"[RECOVERY][stderr] {err_out}")
        # Rerun base script
        print("[RECOVERY] Rerunning digital_ocean_base.sh...")
        stdin, stdout, stderr = ssh_client.exec_command("bash /srv/backend/scripts/digital_ocean_base.sh")
        print(stdout.read().decode())
        err_out = stderr.read().decode()
        if err_out:
            print(f"[RECOVERY][stderr] {err_out}")
        ssh_client.close()
    except Exception as e:
        print(f"[RECOVERY] SSH recovery failed: {e}")
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


# --- Read digital_ocean_basev1.sh for user_data ---
base_script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "scripts/digital_ocean_basev1.sh"))
with open(base_script_path, "r") as f:
    user_data_script = f.read()
log("Loaded digital_ocean_basev1.sh for user_data:")
print(user_data_script)

# --- 1. Create Droplet ---
droplet_spec = {
    "name": DO_DROPLET_NAME,
    "region": DO_API_REGION,
    "size": DO_API_SIZE,
    "image": DO_API_IMAGE,
    "ssh_keys": ssh_keys,
    "tags": ["base2"],
    "user_data": user_data_script,
}
log_json("Droplet spec being sent", droplet_spec)


log("Creating droplet via DigitalOcean API...")
try:
    log_json("API Request - droplets.create", droplet_spec)
    droplet = client.droplets.create(droplet_spec)
    log_json("API Response - droplets.create", droplet)
    droplet_id = droplet["droplet"]["id"]

    log("Waiting for droplet to become active...")
    while True:
        droplet_info = client.droplets.get(droplet_id)["droplet"]
        log_json("API Response - droplets.get", droplet_info)
        if droplet_info["status"] == "active":
            break
        time.sleep(5)
        print("...", flush=True)
    ip_address = droplet_info["networks"]["v4"][0]["ip_address"]
    print(f"Droplet created! IP address: {ip_address}")
    exit(0)
except Exception as e:
    err(f"Droplet creation failed: {e}")
    exit(1)
