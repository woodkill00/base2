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
import re

def log(msg):
    print(f"\033[1;32m[INFO]\033[0m {msg}")

def err(msg):
    print(f"\033[1;31m[ERROR]\033[0m {msg}", flush=True)

def log_json(label, data):
    print(f"\033[1;36m[DEBUG]\033[0m {label}: {json.dumps(data, indent=2)}")

# Load .env
load_dotenv()


# --- SSH Key Generation and .env Update ---
# --- Configurable timeouts and intervals ---
SSH_INITIAL_WAIT = 60  # seconds
SSH_ATTEMPTS = 3
SSH_INTERVAL = 20  # seconds
SSH_TIMEOUT = 15  # seconds
LOG_POLL_ATTEMPTS = 60
LOG_POLL_TIMEOUT = 30  # seconds
LOG_POLL_INTERVAL = 15  # seconds
REBOOT_MARKERS = [
    "Cloud-init v. 25.2-0ubuntu1~22.04.1 finished at"
]
COMPLETION_MARKER = "User data script completed at"
SUMMARY = []
PROJECT_NAME = os.getenv("PROJECT_NAME", "base2")
ssh_dir = os.path.expanduser("~/.ssh")
ssh_key_path = os.path.join(ssh_dir, PROJECT_NAME)
pub_key_path = ssh_key_path + ".pub"
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.env"))


log(f"Checking for SSH key at {ssh_key_path} and {pub_key_path}")
if not os.path.exists(ssh_key_path):
    err(f"SSH key file {ssh_key_path} does not exist. Please check your key path and permissions.")
    exit(1)
if not os.path.exists(ssh_key_path) or not os.path.exists(pub_key_path):
    os.makedirs(ssh_dir, exist_ok=True)
    log(f"Generating SSH key: {ssh_key_path}")
    result = subprocess.run(["ssh-keygen", "-t", "ed25519", "-f", ssh_key_path, "-N", ""], capture_output=True, text=True)
    print(f"[ssh-keygen stdout]:\n{result.stdout}")
    if result.stderr:
        print(f"[ssh-keygen stderr]:\n{result.stderr}")
else:
    log(f"SSH key already exists: {ssh_key_path}")


log(f"Reading public key from {pub_key_path}")
with open(pub_key_path, "r") as f:
    pubkey = f.read().strip()
print(f"[public key]: {pubkey}")


log(f"Updating DO_API_SSH_KEYS in .env at {env_path}")
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
log(".env updated with public key.")
import time
from pydo import Client
import paramiko
from dotenv import dotenv_values, set_key
from typing import Dict, Tuple

def log(msg):
    print(f"\033[1;32m[INFO]\033[0m {msg}")

def err(msg):
    print(f"\033[1;31m[ERROR]\033[0m {msg}", flush=True)

# --- Recovery routine, now only called explicitly ---
def recovery_ssh_logs(ip_address, SSH_USER, ssh_key_path):
    try:
        print("[RECOVERY] Attempting SSH recovery and diagnostics...")
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(ip_address, username=SSH_USER, key_filename=ssh_key_path)
        # Only check logs, do not rerun any scripts
        for log_path in ["/var/log/cloud-init-output.log"]:
            # Check if file exists before tailing
            stdin, stdout, stderr = ssh_client.exec_command(f"test -f {log_path} && echo exists || echo missing")
            exists = stdout.read().decode().strip()
            if exists == "exists":
                print(f"[RECOVERY] Checking {log_path}...")
                stdin, stdout, stderr = ssh_client.exec_command(f"tail -n 100 {log_path}")
                print(stdout.read().decode())
                err_out = stderr.read().decode()
                if err_out:
                    print(f"[RECOVERY][stderr] {err_out}")
            else:
                print(f"[RECOVERY] {log_path} does not exist, skipping.")
        ssh_client.close()
    except Exception as e:
        print(f"[RECOVERY] SSH recovery failed: {e}")
DO_API_TOKEN = os.getenv("DO_API_TOKEN")
DO_DOMAIN = os.getenv("DO_DOMAIN")  # e.g. example.com
DO_DROPLET_NAME = os.getenv("DO_DROPLET_NAME", "base2-droplet")
DO_API_REGION = os.getenv("DO_API_REGION", "nyc3")
DO_API_SIZE = os.getenv("DO_API_SIZE", "s-1vcpu-1gb")
DO_API_IMAGE = os.getenv("DO_API_IMAGE", "ubuntu-22-04-x64")
PGADMIN_DNS_LABEL = os.getenv("PGADMIN_DNS_LABEL", "pgadmin").strip() or "pgadmin"
TRAEFIK_DNS_LABEL = os.getenv("TRAEFIK_DNS_LABEL", "traefik").strip() or "traefik"
DJANGO_ADMIN_DNS_LABEL = os.getenv("DJANGO_ADMIN_DNS_LABEL", "admin").strip() or "admin"
FLOWER_DNS_LABEL = os.getenv("FLOWER_DNS_LABEL", "flower").strip() or "flower"
import sys
import argparse

# CLI flags
parser = argparse.ArgumentParser(description="Orchestrate DO deploy and post-deploy actions")
parser.add_argument("--dry-run", action="store_true", help="Print actions without making changes")
parser.add_argument("--update-only", action="store_true", help="Skip droplet creation; pull latest repo on droplet and rerun post-deploy")
args = parser.parse_args()
DRY_RUN = args.dry_run
UPDATE_ONLY = args.update_only
if DRY_RUN:
    print("\033[1;32m[INFO]\033[0m [DRY RUN] No changes will be made. Printing planned actions only.")
DO_SSH_KEY_ID = os.getenv("DO_SSH_KEY_ID")
DO_API_SSH_KEYS = os.getenv("DO_API_SSH_KEYS")


log(f"DO_SSH_KEY_ID: {DO_SSH_KEY_ID}")
log(f"DO_API_SSH_KEYS: {DO_API_SSH_KEYS}")
ssh_keys = []
if DO_SSH_KEY_ID and DO_SSH_KEY_ID.strip():
    ssh_keys = [DO_SSH_KEY_ID.strip()]
elif DO_API_SSH_KEYS and DO_API_SSH_KEYS.strip():
    ssh_keys = [DO_API_SSH_KEYS.strip()]
else:
    err("No valid SSH key identifier found. Set DO_SSH_KEY_ID (numeric ID or fingerprint) or DO_API_SSH_KEYS (public key string) in your .env file.")
    exit(1)
log(f"Using SSH keys for droplet: {ssh_keys}")
LOCAL_ENV_PATH = os.getenv("LOCAL_ENV_PATH", os.path.abspath(os.path.join(os.path.dirname(__file__), "../.env")))
REMOTE_ENV_PATH = "/srv/backend/.env"  # Adjust as needed for your droplet
SSH_USER = os.getenv("SSH_USER", "root")

client = Client(token=DO_API_TOKEN)



from dotenv import dotenv_values




base_script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "scripts/digital_ocean_base.sh"))
log(f"Loading user_data script from {base_script_path}")
with open(base_script_path, "r") as f:
    user_data_script = f.read()

# Load .env as dict
env_dict = dotenv_values(env_path)

def substitute_env_vars(script, env):
    # Replace $VAR and ${VAR} with env[VAR] if present
    def replacer(match):
        var = match.group(1) or match.group(2)
        return env.get(var, match.group(0))
    # $VAR or ${VAR}
    pattern = re.compile(r'\$(\w+)|\${(\w+)}')
    return pattern.sub(replacer, script)


user_data_script_sub = substitute_env_vars(user_data_script, env_dict)
log("Loaded digital_ocean_base.sh for user_data (with env substitution):")
print("--- user_data script ---\n" + user_data_script_sub + "\n--- end user_data script ---")

# Write user_data to DO_userdata.json for inspection (droplet_id will be added after creation)
do_userdata_json_path = "DO_userdata.json"
with open(do_userdata_json_path, "w", encoding="utf-8") as f:
    json.dump({"user_data": user_data_script_sub}, f, indent=2)
log("Wrote user_data to DO_userdata.json (without droplet_id yet)")

# --- 1. Create Droplet ---

log("Preparing droplet spec...")
droplet_spec = {
    "name": DO_DROPLET_NAME,
    "region": DO_API_REGION,
    "size": DO_API_SIZE,
    "image": DO_API_IMAGE,
    "ssh_keys": ssh_keys,
    "tags": ["base2"],
    "user_data": user_data_script_sub,
    "ipv6": True,
}
log_json("Droplet spec being sent", droplet_spec)

# Determine droplet to use (create or reuse) and set ip_address/droplet_id/droplet_info
ip_address = None
droplet_id = None
droplet_info = None

if UPDATE_ONLY:
    log("[UPDATE-ONLY] Skipping creation; locating existing droplet by name...")
    try:
        lst = client.droplets.list()
        matched = next((d for d in lst.get("droplets", []) if d.get("name") == DO_DROPLET_NAME), None)
        if not matched:
            raise RuntimeError(f"No existing droplet found named {DO_DROPLET_NAME}")
        droplet_id = matched["id"]
        droplet_info = client.droplets.get(droplet_id)["droplet"]
        ip_address = droplet_info["networks"]["v4"][0]["ip_address"]
        log(f"Using existing droplet {droplet_id} at {ip_address}")
    except Exception as e:
        err(f"Failed to locate existing droplet: {e}")
        exit(1)
else:
    log("Creating droplet via DigitalOcean API...")
    try:
        log_json("API Request - droplets.create", droplet_spec)
        droplet = client.droplets.create(droplet_spec)
        log_json("API Response - droplets.create", droplet)
        droplet_id = droplet["droplet"]["id"]
        log(f"Droplet created with ID: {droplet_id}")
        # Wait active and set ip
        while True:
            droplet_info = client.droplets.get(droplet_id)["droplet"]
            log_json("API Response - droplets.get", droplet_info)
            if droplet_info["status"] == "active":
                break
            time.sleep(5)
            print("...", flush=True)
        ip_address = droplet_info["networks"]["v4"][0]["ip_address"]
        log(f"Droplet is active. IP address: {ip_address}")
        print(f"Droplet created! IP address: {ip_address}")
        # Update DO_userdata.json
        try:
            with open(do_userdata_json_path, "r", encoding="utf-8") as f:
                do_userdata = json.load(f)
            do_userdata["droplet_id"] = droplet_id
            do_userdata["ip_address"] = ip_address
            with open(do_userdata_json_path, "w", encoding="utf-8") as f:
                json.dump(do_userdata, f, indent=2)
            log(f"Updated {do_userdata_json_path} with droplet_id {droplet_id} and ip_address {ip_address}")
        except Exception as e:
            err(f"Failed to update {do_userdata_json_path}: {e}")
    except Exception as e:
        err(f"Droplet creation failed: {e}")
        exit(1)

    # --- 3. Update DNS Records ---
    # Always ensure required DNS records exist/update to current droplet IP
    if True:
        log("Updating DNS A/AAAA records for domain and www...")
        try:
            log_json("API Request - domains.list_records", {"domain": DO_DOMAIN})
            records = client.domains.list_records(DO_DOMAIN)["domain_records"]
            log_json("API Response - domains.list_records", records)
            v6_list = droplet_info["networks"].get("v6", [])
            ipv6_address = v6_list[0]["ip_address"] if v6_list else None

            # Track which records exist
            found = {
                "A_root": None,
                "A_www": None,
                "AAAA_root": None,
                "A_pgadmin": None,
                "AAAA_pgadmin": None,
                "A_traefik": None,
                "AAAA_traefik": None,
                "A_django_admin": None,
                "AAAA_django_admin": None,
                "A_flower": None,
                "AAAA_flower": None,
            }
            updated = {
                "A_root": False,
                "A_www": False,
                "AAAA_root": False,
                "A_pgadmin": False,
                "AAAA_pgadmin": False,
                "A_traefik": False,
                "AAAA_traefik": False,
                "A_django_admin": False,
                "AAAA_django_admin": False,
                "A_flower": False,
                "AAAA_flower": False,
            }

            for record in records:
                # Update all A records for this domain (root, www, subdomains, wildcard, traefik)
                if record["type"] == "A":
                    match_a = (
                        record["name"] == "@"
                        or record["name"] == DO_DOMAIN
                        or record["name"] == ""
                        or record["name"] == "www"
                        or record["name"] == f"www.{DO_DOMAIN}"
                        or DO_DOMAIN in record["name"]
                        or record["name"].startswith("*")
                        or record["name"] == TRAEFIK_DNS_LABEL
                        or record["name"] == f"{TRAEFIK_DNS_LABEL}.{DO_DOMAIN}"
                        or record["name"] == PGADMIN_DNS_LABEL
                        or record["name"] == f"{PGADMIN_DNS_LABEL}.{DO_DOMAIN}"
                        or record["name"] == DJANGO_ADMIN_DNS_LABEL
                        or record["name"] == f"{DJANGO_ADMIN_DNS_LABEL}.{DO_DOMAIN}"
                        or record["name"] == FLOWER_DNS_LABEL
                        or record["name"] == f"{FLOWER_DNS_LABEL}.{DO_DOMAIN}"
                    )
                    if match_a:
                        # Track root and www for legacy logic
                        if record["name"] == "@" or record["name"] == DO_DOMAIN or record["name"] == "":
                            found["A_root"] = record
                            updated["A_root"] = True
                        if record["name"] == "www" or record["name"] == f"www.{DO_DOMAIN}":
                            found["A_www"] = record
                            updated["A_www"] = True
                        if record["name"] == TRAEFIK_DNS_LABEL or record["name"] == f"{TRAEFIK_DNS_LABEL}.{DO_DOMAIN}":
                            found["A_traefik"] = record
                            updated["A_traefik"] = True
                        if record["name"] == PGADMIN_DNS_LABEL or record["name"] == f"{PGADMIN_DNS_LABEL}.{DO_DOMAIN}":
                            found["A_pgadmin"] = record
                            updated["A_pgadmin"] = True
                        if record["name"] == DJANGO_ADMIN_DNS_LABEL or record["name"] == f"{DJANGO_ADMIN_DNS_LABEL}.{DO_DOMAIN}":
                            found["A_django_admin"] = record
                            updated["A_django_admin"] = True
                        if record["name"] == FLOWER_DNS_LABEL or record["name"] == f"{FLOWER_DNS_LABEL}.{DO_DOMAIN}":
                            found["A_flower"] = record
                            updated["A_flower"] = True
                        if DRY_RUN:
                            log(f"[DRY RUN] Would update A record ({record['name']}) -> {ip_address}")
                        else:
                            log_json("API Request - domains.update_record (A_generic)", {"id": record["id"], "data": ip_address})
                            resp = client.domains.update_record(DO_DOMAIN, record["id"], {
                                "type": "A",
                                "name": record["name"],
                                "data": ip_address
                            })
                            log_json("API Response - domains.update_record (A_generic)", resp)
                            log(f"Updated A record ({record['name']}) -> {ip_address}")
                # Update all AAAA records for this domain (root, subdomains, wildcard)
                if record["type"] == "AAAA":
                    if (
                        record["name"] == "@"
                        or record["name"] == DO_DOMAIN
                        or record["name"] == ""
                        or DO_DOMAIN in record["name"]
                        or record["name"].startswith("*")
                        or record["name"] == TRAEFIK_DNS_LABEL
                        or record["name"] == f"{TRAEFIK_DNS_LABEL}.{DO_DOMAIN}"
                        or record["name"] == PGADMIN_DNS_LABEL
                        or record["name"] == f"{PGADMIN_DNS_LABEL}.{DO_DOMAIN}"
                        or record["name"] == DJANGO_ADMIN_DNS_LABEL
                        or record["name"] == f"{DJANGO_ADMIN_DNS_LABEL}.{DO_DOMAIN}"
                        or record["name"] == FLOWER_DNS_LABEL
                        or record["name"] == f"{FLOWER_DNS_LABEL}.{DO_DOMAIN}"
                    ):
                        # Track root for legacy logic
                        if record["name"] == "@" or record["name"] == DO_DOMAIN or record["name"] == "":
                            found["AAAA_root"] = record
                            updated["AAAA_root"] = True
                        if record["name"] == TRAEFIK_DNS_LABEL or record["name"] == f"{TRAEFIK_DNS_LABEL}.{DO_DOMAIN}":
                            found["AAAA_traefik"] = record
                            updated["AAAA_traefik"] = True
                        if record["name"] == PGADMIN_DNS_LABEL or record["name"] == f"{PGADMIN_DNS_LABEL}.{DO_DOMAIN}":
                            found["AAAA_pgadmin"] = record
                            updated["AAAA_pgadmin"] = True
                        if record["name"] == DJANGO_ADMIN_DNS_LABEL or record["name"] == f"{DJANGO_ADMIN_DNS_LABEL}.{DO_DOMAIN}":
                            found["AAAA_django_admin"] = record
                            updated["AAAA_django_admin"] = True
                        if record["name"] == FLOWER_DNS_LABEL or record["name"] == f"{FLOWER_DNS_LABEL}.{DO_DOMAIN}":
                            found["AAAA_flower"] = record
                            updated["AAAA_flower"] = True
                        if ipv6_address:
                            if DRY_RUN:
                                log(f"[DRY RUN] Would update AAAA record ({record['name']}) -> {ipv6_address}")
                            else:
                                log_json("API Request - domains.update_record (AAAA_generic)", {"id": record["id"], "data": ipv6_address})
                                resp = client.domains.update_record(DO_DOMAIN, record["id"], {
                                    "type": "AAAA",
                                    "name": record["name"],
                                    "data": ipv6_address
                                })
                                log_json("API Response - domains.update_record (AAAA_generic)", resp)
                                log(f"Updated AAAA record ({record['name']}) -> {ipv6_address}")

            # Create missing records
            if not found["A_root"]:
                if DRY_RUN:
                    log(f"[DRY RUN] Would create root A record (@) -> {ip_address}")
                else:
                    log_json("API Request - domains.create_record (A_root)", {"type": "A", "name": "@", "data": ip_address})
                    resp = client.domains.create_record(DO_DOMAIN, {
                        "type": "A",
                        "name": "@",
                        "data": ip_address
                    })
                    log_json("API Response - domains.create_record (A_root)", resp)
                    log(f"Created root A record (@) -> {ip_address}")
            if not found["A_www"]:
                if DRY_RUN:
                    log(f"[DRY RUN] Would create www A record (www) -> {ip_address}")
                else:
                    log_json("API Request - domains.create_record (A_www)", {"type": "A", "name": "www", "data": ip_address})
                    resp = client.domains.create_record(DO_DOMAIN, {
                        "type": "A",
                        "name": "www",
                        "data": ip_address
                    })
                    log_json("API Response - domains.create_record (A_www)", resp)
                    log(f"Created www A record (www) -> {ip_address}")
            if ipv6_address and not found["AAAA_root"]:
                if DRY_RUN:
                    log(f"[DRY RUN] Would create root AAAA record (@) -> {ipv6_address}")
                else:
                    log_json("API Request - domains.create_record (AAAA_root)", {"type": "AAAA", "name": "@", "data": ipv6_address})
                    resp = client.domains.create_record(DO_DOMAIN, {
                        "type": "AAAA",
                        "name": "@",
                        "data": ipv6_address
                    })
                    log_json("API Response - domains.create_record (AAAA_root)", resp)
                    log(f"Created root AAAA record (@) -> {ipv6_address}")

            # Ensure Traefik subdomain exists
            if not found["A_traefik"]:
                if DRY_RUN:
                    log(f"[DRY RUN] Would create A record ({TRAEFIK_DNS_LABEL}) -> {ip_address}")
                else:
                    log_json("API Request - domains.create_record (A_traefik)", {"type": "A", "name": TRAEFIK_DNS_LABEL, "data": ip_address})
                    resp = client.domains.create_record(DO_DOMAIN, {
                        "type": "A",
                        "name": TRAEFIK_DNS_LABEL,
                        "data": ip_address
                    })
                    log_json("API Response - domains.create_record (A_traefik)", resp)
                    log(f"Created A record ({TRAEFIK_DNS_LABEL}) -> {ip_address}")
            if ipv6_address and not found["AAAA_traefik"]:
                if DRY_RUN:
                    log(f"[DRY RUN] Would create AAAA record ({TRAEFIK_DNS_LABEL}) -> {ipv6_address}")
                else:
                    log_json("API Request - domains.create_record (AAAA_traefik)", {"type": "AAAA", "name": TRAEFIK_DNS_LABEL, "data": ipv6_address})
                    resp = client.domains.create_record(DO_DOMAIN, {
                        "type": "AAAA",
                        "name": TRAEFIK_DNS_LABEL,
                        "data": ipv6_address
                    })
                    log_json("API Response - domains.create_record (AAAA_traefik)", resp)
                    log(f"Created AAAA record ({TRAEFIK_DNS_LABEL}) -> {ipv6_address}")

            # Ensure pgAdmin subdomain exists
            if not found["A_pgadmin"]:
                if DRY_RUN:
                    log(f"[DRY RUN] Would create A record ({PGADMIN_DNS_LABEL}) -> {ip_address}")
                else:
                    log_json("API Request - domains.create_record (A_pgadmin)", {"type": "A", "name": PGADMIN_DNS_LABEL, "data": ip_address})
                    resp = client.domains.create_record(DO_DOMAIN, {
                        "type": "A",
                        "name": PGADMIN_DNS_LABEL,
                        "data": ip_address
                    })
                    log_json("API Response - domains.create_record (A_pgadmin)", resp)
                    log(f"Created A record ({PGADMIN_DNS_LABEL}) -> {ip_address}")
            if ipv6_address and not found["AAAA_pgadmin"]:
                if DRY_RUN:
                    log(f"[DRY RUN] Would create AAAA record ({PGADMIN_DNS_LABEL}) -> {ipv6_address}")
                else:
                    log_json("API Request - domains.create_record (AAAA_pgadmin)", {"type": "AAAA", "name": PGADMIN_DNS_LABEL, "data": ipv6_address})
                    resp = client.domains.create_record(DO_DOMAIN, {
                        "type": "AAAA",
                        "name": PGADMIN_DNS_LABEL,
                        "data": ipv6_address
                    })
                    log_json("API Response - domains.create_record (AAAA_pgadmin)", resp)
                    log(f"Created AAAA record ({PGADMIN_DNS_LABEL}) -> {ipv6_address}")

            # Ensure Django admin subdomain exists
            if not found["A_django_admin"]:
                if DRY_RUN:
                    log(f"[DRY RUN] Would create A record ({DJANGO_ADMIN_DNS_LABEL}) -> {ip_address}")
                else:
                    log_json("API Request - domains.create_record (A_django_admin)", {"type": "A", "name": DJANGO_ADMIN_DNS_LABEL, "data": ip_address})
                    resp = client.domains.create_record(DO_DOMAIN, {
                        "type": "A",
                        "name": DJANGO_ADMIN_DNS_LABEL,
                        "data": ip_address
                    })
                    log_json("API Response - domains.create_record (A_django_admin)", resp)
                    log(f"Created A record ({DJANGO_ADMIN_DNS_LABEL}) -> {ip_address}")
            if ipv6_address and not found["AAAA_django_admin"]:
                if DRY_RUN:
                    log(f"[DRY RUN] Would create AAAA record ({DJANGO_ADMIN_DNS_LABEL}) -> {ipv6_address}")
                else:
                    log_json("API Request - domains.create_record (AAAA_django_admin)", {"type": "AAAA", "name": DJANGO_ADMIN_DNS_LABEL, "data": ipv6_address})
                    resp = client.domains.create_record(DO_DOMAIN, {
                        "type": "AAAA",
                        "name": DJANGO_ADMIN_DNS_LABEL,
                        "data": ipv6_address
                    })
                    log_json("API Response - domains.create_record (AAAA_django_admin)", resp)
                    log(f"Created AAAA record ({DJANGO_ADMIN_DNS_LABEL}) -> {ipv6_address}")

            # Ensure Flower subdomain exists
            if not found["A_flower"]:
                if DRY_RUN:
                    log(f"[DRY RUN] Would create A record ({FLOWER_DNS_LABEL}) -> {ip_address}")
                else:
                    log_json("API Request - domains.create_record (A_flower)", {"type": "A", "name": FLOWER_DNS_LABEL, "data": ip_address})
                    resp = client.domains.create_record(DO_DOMAIN, {
                        "type": "A",
                        "name": FLOWER_DNS_LABEL,
                        "data": ip_address
                    })
                    log_json("API Response - domains.create_record (A_flower)", resp)
                    log(f"Created A record ({FLOWER_DNS_LABEL}) -> {ip_address}")
            if ipv6_address and not found["AAAA_flower"]:
                if DRY_RUN:
                    log(f"[DRY RUN] Would create AAAA record ({FLOWER_DNS_LABEL}) -> {ipv6_address}")
                else:
                    log_json("API Request - domains.create_record (AAAA_flower)", {"type": "AAAA", "name": FLOWER_DNS_LABEL, "data": ipv6_address})
                    resp = client.domains.create_record(DO_DOMAIN, {
                        "type": "AAAA",
                        "name": FLOWER_DNS_LABEL,
                        "data": ipv6_address
                    })
                    log_json("API Response - domains.create_record (AAAA_flower)", resp)
                    log(f"Created AAAA record ({FLOWER_DNS_LABEL}) -> {ipv6_address}")
            if not updated["A_root"] and not updated["A_www"] and not updated["AAAA_root"]:
                log("No A/AAAA records for root or www found to update or create.")
        except Exception as e:
            err(f"DNS update failed: {e}")
            recovery_ssh_logs(ip_address, SSH_USER, ssh_key_path)
            exit(1)

    ssh_cmd = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-i", ssh_key_path.replace('\\', '/'),
        f"root@{ip_address}",
        "true"  # Just test connection
    ]

    # Wait for SSH to become available (initial boot)
    if not UPDATE_ONLY:
        log(f"Waiting {SSH_INITIAL_WAIT} seconds before first SSH availability check after droplet creation...")
        time.sleep(SSH_INITIAL_WAIT)
    ssh_success = False
    for attempt in range(1, SSH_ATTEMPTS + 1):
        try:
            log(f"SSH availability check attempt {attempt}/{SSH_ATTEMPTS}...")
            result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=SSH_TIMEOUT, encoding="utf-8", errors="replace")
            if result.returncode == 0:
                log("SSH is available. Proceeding to cloud-init log polling for reboot marker.")
                ssh_success = True
                SUMMARY.append(f"SSH available after {attempt} attempts.")
                break
            else:
                log(f"SSH failed: {result.stderr}")
        except Exception as e:
            log(f"SSH check exception: {e}")
        time.sleep(SSH_INTERVAL)
    if not ssh_success:
        log("SSH not available after initial attempts. Proceeding to cloud-init log polling for reboot marker anyway.")
        SUMMARY.append("SSH not available after initial attempts.")

    # Poll cloud-init log for reboot marker BEFORE checking for SSH reboot
    ssh_log_cmd = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-i", ssh_key_path.replace('\\', '/'),
        f"root@{ip_address}",
        "cat /var/log/cloud-init-output.log"
    ]
    log(f"Polling /var/log/cloud-init-output.log until completion marker '{COMPLETION_MARKER}' is found...")
    import re
    completion_found = False
    cloud_init_pattern = re.compile(r"^Cloud-init v\\. .+ finished at")
    # Updated pattern: match any line containing 'Cloud-init v.' and 'finished at' (version, timestamp, and details are variable)
    cloud_init_pattern = re.compile(r"Cloud-init v\\..*finished at")
    for poll in range(1, LOG_POLL_ATTEMPTS + 1):
        try:
            result = subprocess.run(ssh_log_cmd, capture_output=True, text=True, timeout=LOG_POLL_TIMEOUT, encoding="utf-8", errors="replace")
            log(f"Log poll {poll}/{LOG_POLL_ATTEMPTS}")
            log_output = result.stdout if result.stdout is not None else ''
            print("\n--- /var/log/cloud-init-output.log ---\n")
            print(log_output)
            if result.stderr:
                print(f"[stderr] {result.stderr}")
            # Look for any line matching either marker
            for line in log_output.splitlines():
                if COMPLETION_MARKER in line or cloud_init_pattern.search(line.strip()):
                    log("Cloud-init or user-data completion marker found in log. Script finished successfully.")
                    print(f"\n[INFO] Deployment script ran and completion marker was found.\n[DROPLET ID] {droplet_id}\n[IP ADDRESS] {ip_address}\nScript completed correctly.\n")
                    completion_found = True
                    SUMMARY.append(f"Completion marker found in log after {poll} polls.")
                    break
            if completion_found:
                break
            else:
                log("Cloud-init completion marker not found, will retry...")
        except Exception as e:
            err(f"SSH log fetch failed: {e}")
        time.sleep(LOG_POLL_INTERVAL)
    if not UPDATE_ONLY:
        if not completion_found:
            err("Did not find cloud-init completion marker in log after multiple attempts.")
            try:
                result = subprocess.run(ssh_log_cmd, capture_output=True, text=True, timeout=LOG_POLL_TIMEOUT, encoding="utf-8", errors="replace")
                log_output = result.stdout if result.stdout is not None else ''
                print("\n--- Last 50 lines of cloud-init log ---\n")
                print("\n".join(log_output.splitlines()[-50:]))
            except Exception as e:
                err(f"Failed to fetch last lines of cloud-init log: {e}")
            recovery_ssh_logs(ip_address, SSH_USER, ssh_key_path)
            SUMMARY.append("Cloud-init completion marker not found in log.")
            exit(1)
        log("Deployment script completed successfully.")
        SUMMARY.append("Deployment script completed successfully.")

    # Extra stabilization wait to allow services/SSH to settle
    STABILIZATION_WAIT = int(os.getenv("POST_DEPLOY_STABILIZATION_SECONDS", "60"))
    if not UPDATE_ONLY:
        log(f"Waiting {STABILIZATION_WAIT} seconds for SSH/services to stabilize...")
        time.sleep(STABILIZATION_WAIT)

    # --- Post-reboot configuration and service startup ---
    try:
        SSH_USER = os.getenv("SSH_USER", "root")
        repo_path = f"{env_dict.get('DEPLOY_PATH', '/srv/')}{env_dict.get('PROJECT_NAME', 'base2')}"
        log(f"Connecting via SSH to {ip_address} for post-reboot configuration...")
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        def ssh_connect_with_retry(max_attempts: int = 5, delay: int = 15):
            for attempt in range(1, max_attempts + 1):
                try:
                    ssh_client.connect(ip_address, username=SSH_USER, key_filename=ssh_key_path)
                    return True
                except Exception as e:
                    err(f"SSH connect attempt {attempt}/{max_attempts} failed: {e}")
                    time.sleep(delay)
            return False

        if not ssh_connect_with_retry():
            raise RuntimeError("SSH connection failed after retries")

        # Copy local .env to remote repo
        remote_env_path = f"{repo_path}/.env"
        log(f"Uploading .env to {remote_env_path}")
        sftp = ssh_client.open_sftp()
        sftp.put(env_path.replace('\\', '/'), remote_env_path)
        sftp.close()

        # If update-only, ensure repo exists and pull latest
        if UPDATE_ONLY:
            log("[UPDATE-ONLY] Ensuring repo path exists and pulling latest changes...")
            pull_cmd = (
                f"test -d {repo_path} || mkdir -p {repo_path}; "
                f"cd {repo_path} && git rev-parse --is-inside-work-tree >/dev/null 2>&1 && git pull --ff-only || "
                f"(test -d .git || (rm -rf ./*); git init && git remote add origin $(grep '^GIT_REMOTE=' .env | cut -d'=' -f2) && git fetch origin && git reset --hard origin/main)"
            )
            stdin, stdout, stderr = ssh_client.exec_command(pull_cmd)
            print(stdout.read().decode())
            err_out = stderr.read().decode()
            if err_out:
                print(err_out)

        # Run post_reboot_complete.sh to finalize config (with reconnect on drop)
        post_reboot_path = f"{repo_path}/digital_ocean/scripts/post_reboot_complete.sh"
        log(f"Running post-reboot script: {post_reboot_path}")
        try:
            stdin, stdout, stderr = ssh_client.exec_command(f"bash {post_reboot_path}")
            print(stdout.read().decode())
            err_out = stderr.read().decode()
            if err_out:
                print(err_out)
        except Exception as e:
            err(f"Post-reboot exec encountered an error: {e}. Reconnecting and retrying once...")
            ssh_client.close()
            if not ssh_connect_with_retry():
                raise RuntimeError("SSH reconnect failed after post-reboot error")
            stdin, stdout, stderr = ssh_client.exec_command(f"bash {post_reboot_path}")
            print(stdout.read().decode())
            err_out = stderr.read().decode()
            if err_out:
                print(err_out)

        # Start services and follow logs briefly for live visibility
        # Always rebuild to ensure latest images when updating remotely
        start_cmd = (
            f"cd {repo_path} && START_FOLLOW_LOGS=true POST_DEPLOY_LOGS_FOLLOW_SECONDS=60 "
            f"bash scripts/start.sh --build --follow-logs"
        )
        log(f"Starting services: {start_cmd}")
        try:
            stdin, stdout, stderr = ssh_client.exec_command(start_cmd)
            print(stdout.read().decode())
            err_out = stderr.read().decode()
            if err_out:
                print(err_out)
        except Exception as e:
            err(f"Start services encountered an error: {e}. Reconnecting and retrying once...")
            ssh_client.close()
            if not ssh_connect_with_retry():
                raise RuntimeError("SSH reconnect failed after start error")
            stdin, stdout, stderr = ssh_client.exec_command(start_cmd)
            print(stdout.read().decode())
            err_out = stderr.read().decode()
            if err_out:
                print(err_out)

        # Check status and logs
        def parse_ps_health(ps_text: str) -> Dict[str, str]:
            summary: Dict[str, str] = {}
            for line in ps_text.splitlines():
                if not line or line.startswith("NAME"):
                    continue
                parts = re.split(r"\s{2,}", line.strip())
                if len(parts) < 4:
                    # Fallback split by single spaces if columns are condensed
                    parts = line.split()
                if not parts:
                    continue
                name = parts[0]
                # STATUS column usually near the end; search for token containing health
                status_field = next((p for p in parts if "healthy" in p.lower() or "unhealthy" in p.lower() or "exit" in p.lower() or "restarting" in p.lower()), None)
                if status_field:
                    summary[name] = status_field
            return summary

        log("Fetching docker compose status...")
        stdin, stdout, stderr = ssh_client.exec_command(f"cd {repo_path} && docker compose -f local.docker.yml ps")
        ps_output = stdout.read().decode()
        print(ps_output)
        err_out = stderr.read().decode()
        if err_out:
            print(err_out)
        health_summary = parse_ps_health(ps_output)

        def detect_http_errors(log_text: str) -> Tuple[int, int, Dict[str, int]]:
            errors_4xx = 0
            errors_5xx = 0
            paths: Dict[str, int] = {}
            for raw_line in log_text.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                # Try JSON first (Traefik, structured logs)
                try:
                    obj = json.loads(line)
                    status = None
                    for key in ("status", "DownstreamStatus", "downstream_status"):
                        if key in obj:
                            status = obj[key]
                            break
                    if isinstance(status, str) and status.isdigit():
                        status = int(status)
                    if isinstance(status, int):
                        if 400 <= status <= 499:
                            errors_4xx += 1
                        elif 500 <= status <= 599:
                            errors_5xx += 1
                        # Capture path if present
                        path = obj.get("RequestPath") or obj.get("path") or obj.get("requestPath")
                        if path and (400 <= status <= 499 or 500 <= status <= 599):
                            paths[path] = paths.get(path, 0) + 1
                        continue
                except Exception:
                    pass

                # Nginx/combined log format: "GET /path HTTP/1.1" 404 ...
                m = re.search(r"\s([45]\d{2})\s", line)
                if m:
                    code = int(m.group(1))
                    if 400 <= code <= 499:
                        errors_4xx += 1
                    elif 500 <= code <= 599:
                        errors_5xx += 1
                    # Try to extract the path inside quotes
                    pm = re.search(r"\"(?:GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+([^\s\"]+)\s+HTTP/", line)
                    if pm:
                        p = pm.group(1)
                        if 400 <= code <= 499 or 500 <= code <= 599:
                            paths[p] = paths.get(p, 0) + 1
            return errors_4xx, errors_5xx, paths

        log("Fetching key service logs (last 100 lines) and summarizing...")
        svc_errors: Dict[str, Dict[str, object]] = {}
        for svc in ["traefik", "nginx", "backend", "postgres", "pgadmin"]:
            log(f"Logs for {svc}:")
            stdin, stdout, stderr = ssh_client.exec_command(f"cd {repo_path} && docker compose -f local.docker.yml logs --tail=100 {svc}")
            logs_text = stdout.read().decode()
            print(logs_text)
            err_out = stderr.read().decode()
            if err_out:
                print(err_out)
            # Only perform HTTP error detection for web-facing services
            if svc in ("traefik", "nginx", "backend"):
                e4, e5, paths = detect_http_errors(logs_text)
                svc_errors[svc] = {"4xx": e4, "5xx": e5, "paths": paths}

        # Print concise summary
        print("\n===== Deployment Health Summary =====")
        if health_summary:
            print("[Containers]")
            for name, status in health_summary.items():
                print(f"- {name}: {status}")
        else:
            print("[Containers] No explicit health statuses parsed.")
        if svc_errors:
            print("\n[HTTP Errors]")
            for svc, data in svc_errors.items():
                print(f"- {svc}: 4xx={data['4xx']}, 5xx={data['5xx']}")
                hotpaths = sorted(((p, c) for p, c in data.get("paths", {}).items()), key=lambda x: -x[1])[:5]
                if hotpaths:
                    for p, c in hotpaths:
                        print(f"  \u2514 {p}: {c}")
        print("===== End Summary =====\n")

        ssh_client.close()
        log("Post-deploy tasks completed.")
    except Exception as e:
        err(f"Post-deploy workflow failed: {e}")
    exit(0)

