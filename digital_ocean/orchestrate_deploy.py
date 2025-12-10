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
LOG_POLL_ATTEMPTS = 36
LOG_POLL_TIMEOUT = 30  # seconds
LOG_POLL_INTERVAL = 10  # seconds
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
        for log_path in ["/var/log/cloud-init-output.log", "/var/log/do_base.log"]:
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
import sys
DRY_RUN = "--dry-run" in sys.argv
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


# --- Read digital_ocean_basev1.sh for user_data ---

base_script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "scripts/digital_ocean_basev1.sh"))
log(f"Loading user_data script from {base_script_path}")
with open(base_script_path, "r") as f:
    user_data_script = f.read()
log("Loaded digital_ocean_basev1.sh for user_data:")
print("--- user_data script ---\n" + user_data_script + "\n--- end user_data script ---")

# --- 1. Create Droplet ---

log("Preparing droplet spec...")
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
    log(f"Droplet created with ID: {droplet_id}")

    log("Waiting for droplet to become active...")
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

    # --- 3. Update DNS Records ---
    log("Updating DNS A/AAAA records for domain and www...")
    try:
        log_json("API Request - domains.list_records", {"domain": DO_DOMAIN})
        records = client.domains.list_records(DO_DOMAIN)["domain_records"]
        log_json("API Response - domains.list_records", records)
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
                    log_json("API Request - domains.update_record (A_root)", {"id": record["id"], "data": ip_address})
                    resp = client.domains.update_record(DO_DOMAIN, record["id"], {
                        "type": "A",
                        "name": record["name"],
                        "data": ip_address
                    })
                    log_json("API Response - domains.update_record (A_root)", resp)
                    log(f"Updated root A record ({record['name']}) -> {ip_address}")
                updated["A_root"] = True
            # www A record
            if record["type"] == "A" and (record["name"] == "www" or record["name"] == f"www.{DO_DOMAIN}"):
                found["A_www"] = record
                if DRY_RUN:
                    log(f"[DRY RUN] Would update www A record ({record['name']}) -> {ip_address}")
                else:
                    log_json("API Request - domains.update_record (A_www)", {"id": record["id"], "data": ip_address})
                    resp = client.domains.update_record(DO_DOMAIN, record["id"], {
                        "type": "A",
                        "name": record["name"],
                        "data": ip_address
                    })
                    log_json("API Response - domains.update_record (A_www)", resp)
                    log(f"Updated www A record ({record['name']}) -> {ip_address}")
                updated["A_www"] = True
            # Root AAAA record
            if record["type"] == "AAAA" and (record["name"] == "@" or record["name"] == DO_DOMAIN or record["name"] == ""):
                found["AAAA_root"] = record
                if ipv6_address:
                    if DRY_RUN:
                        log(f"[DRY RUN] Would update root AAAA record ({record['name']}) -> {ipv6_address}")
                    else:
                        log_json("API Request - domains.update_record (AAAA_root)", {"id": record["id"], "data": ipv6_address})
                        resp = client.domains.update_record(DO_DOMAIN, record["id"], {
                            "type": "AAAA",
                            "name": record["name"],
                            "data": ipv6_address
                        })
                        log_json("API Response - domains.update_record (AAAA_root)", resp)
                        log(f"Updated root AAAA record ({record['name']}) -> {ipv6_address}")
                    updated["AAAA_root"] = True

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
    log(f"Polling /var/log/cloud-init-output.log until any reboot marker {REBOOT_MARKERS} is found...")
    reboot_found = False
    for poll in range(1, LOG_POLL_ATTEMPTS + 1):
        try:
            result = subprocess.run(ssh_log_cmd, capture_output=True, text=True, timeout=LOG_POLL_TIMEOUT, encoding="utf-8", errors="replace")
            log(f"Log poll {poll}/{LOG_POLL_ATTEMPTS}")
            log_output = result.stdout if result.stdout is not None else ''
            print("\n--- /var/log/cloud-init-output.log ---\n")
            print(log_output)
            if result.stderr:
                print(f"[stderr] {result.stderr}")
            if any(marker in log_output for marker in REBOOT_MARKERS):
                log("Reboot marker found in log. Reboot has already occurred.")
                reboot_found = True
                SUMMARY.append(f"Reboot marker found in log after {poll} polls.")
                # Prompt user for keep/destroy
                print("\nDroplet setup complete. Would you like to keep or destroy this droplet?")
                print("Type 'keep' to keep, or 'destroy' to destroy the droplet.")
                user_choice = input("[keep/destroy]: ").strip().lower()
                if user_choice == "destroy":
                    print(f"Destroying droplet {droplet_id}...")
                    # Call destroy_droplet.py with droplet_id
                    import subprocess
                    subprocess.run([sys.executable, "destroy_droplet.py", str(droplet_id)], check=False)
                    print("Droplet destroy command sent.")
                else:
                    print("Droplet will be kept.")
                break
            else:
                log("Reboot marker not found, will retry...")
        except Exception as e:
            err(f"SSH log fetch failed: {e}")
        time.sleep(LOG_POLL_INTERVAL)
    if not reboot_found:
        err("Did not find reboot marker in cloud-init log after multiple attempts.")
        # Print last 50 lines for diagnostics
        try:
            result = subprocess.run(ssh_log_cmd, capture_output=True, text=True, timeout=LOG_POLL_TIMEOUT, encoding="utf-8", errors="replace")
            log_output = result.stdout if result.stdout is not None else ''
            print("\n--- Last 50 lines of cloud-init log ---\n")
            print("\n".join(log_output.splitlines()[-50:]))
        except Exception as e:
            err(f"Failed to fetch last lines of cloud-init log: {e}")
        recovery_ssh_logs(ip_address, SSH_USER, ssh_key_path)
        SUMMARY.append("Reboot marker not found in cloud-init log.")
        exit(1)

    # Wait for SSH to go down (reboot starts)
    log("Waiting for SSH to go down (reboot in progress)...")
    reboot_detected = False
    for _ in range(24):
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=SSH_TIMEOUT, encoding="utf-8", errors="replace")
        if result.returncode != 0:
            log("SSH is down. Reboot detected.")
            reboot_detected = True
            SUMMARY.append("SSH down for reboot detected.")
            break
        time.sleep(5)
    if not reboot_detected:
        err("SSH never went down for reboot.")
        SUMMARY.append("SSH never went down for reboot.")
        exit(1)

    # Wait for SSH to come back up (post-reboot)
    log("Waiting for SSH to come back up after reboot...")
    ssh_up_post_reboot = False
    for _ in range(36):
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=SSH_TIMEOUT, encoding="utf-8", errors="replace")
        if result.returncode == 0:
            log("SSH is available after reboot. Proceeding to final cloud-init log polling.")
            ssh_up_post_reboot = True
            SUMMARY.append("SSH available after reboot.")
            break
        time.sleep(5)
    if not ssh_up_post_reboot:
        err("SSH did not come back up after reboot.")
        SUMMARY.append("SSH did not come back up after reboot.")
        exit(1)

    # Final poll for completion marker in cloud-init log
    log(f"Polling /var/log/cloud-init-output.log until completion marker '{COMPLETION_MARKER}' is found...")
    completion_found = False
    for poll in range(1, LOG_POLL_ATTEMPTS + 1):
        try:
            result = subprocess.run(ssh_log_cmd, capture_output=True, text=True, timeout=LOG_POLL_TIMEOUT, encoding="utf-8", errors="replace")
            log(f"Log poll {poll}/{LOG_POLL_ATTEMPTS}")
            log_output = result.stdout if result.stdout is not None else ''
            print("\n--- /var/log/cloud-init-output.log ---\n")
            print(log_output)
            if result.stderr:
                print(f"[stderr] {result.stderr}")
            if COMPLETION_MARKER in log_output:
                log("Completion marker found in log. Script finished successfully.")
                completion_found = True
                SUMMARY.append(f"Completion marker found in log after {poll} polls.")
                break
            else:
                log("Completion marker not found, will retry...")
        except Exception as e:
            err(f"SSH log fetch failed: {e}")
        time.sleep(LOG_POLL_INTERVAL)
    if not completion_found:
        err("Did not find completion marker in cloud-init log after multiple attempts.")
        try:
            result = subprocess.run(ssh_log_cmd, capture_output=True, text=True, timeout=LOG_POLL_TIMEOUT, encoding="utf-8", errors="replace")
            log_output = result.stdout if result.stdout is not None else ''
            print("\n--- Last 50 lines of cloud-init log ---\n")
            print("\n".join(log_output.splitlines()[-50:]))
        except Exception as e:
            err(f"Failed to fetch last lines of cloud-init log: {e}")
        recovery_ssh_logs(ip_address, SSH_USER, ssh_key_path)
        SUMMARY.append("Completion marker not found in cloud-init log.")
        exit(1)
    log("Deployment script completed successfully.")
    SUMMARY.append("Deployment script completed successfully.")
    print("\n--- Deployment Summary ---\n" + "\n".join(SUMMARY))
    exit(0)
except Exception as e:
    err(f"Droplet creation failed: {e}")
    # Only run recovery for main droplet creation failure
    try:
        recovery_ssh_logs(ip_address, SSH_USER, ssh_key_path)
    except Exception:
        pass
    exit(1)

