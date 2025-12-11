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



import re
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



log("Creating droplet via DigitalOcean API...")
try:
    log_json("API Request - droplets.create", droplet_spec)
    droplet = client.droplets.create(droplet_spec)
    log_json("API Response - droplets.create", droplet)

    droplet_id = droplet["droplet"]["id"]
    log(f"Droplet created with ID: {droplet_id}")
    # Update DO_userdata.json to include droplet_id and ip_address
    try:
        with open(do_userdata_json_path, "r", encoding="utf-8") as f:
            do_userdata = json.load(f)
        do_userdata["droplet_id"] = droplet_id
        # Wait for droplet to become active and get IP address
        while True:
            droplet_info = client.droplets.get(droplet_id)["droplet"]
            log_json("API Response - droplets.get", droplet_info)
            if droplet_info["status"] == "active":
                break
            time.sleep(5)
            print("...", flush=True)
        ip_address = droplet_info["networks"]["v4"][0]["ip_address"]
        do_userdata["ip_address"] = ip_address
        with open(do_userdata_json_path, "w", encoding="utf-8") as f:
            json.dump(do_userdata, f, indent=2)
        log(f"Updated {do_userdata_json_path} with droplet_id {droplet_id} and ip_address {ip_address}")
    except Exception as e:
        err(f"Failed to update {do_userdata_json_path} with droplet_id and ip_address: {e}")

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
                    or record["name"] == "traefik"
                    or record["name"] == f"traefik.{DO_DOMAIN}"
                )
                if match_a:
                    # Track root and www for legacy logic
                    if record["name"] == "@" or record["name"] == DO_DOMAIN or record["name"] == "":
                        found["A_root"] = record
                        updated["A_root"] = True
                    if record["name"] == "www" or record["name"] == f"www.{DO_DOMAIN}":
                        found["A_www"] = record
                        updated["A_www"] = True
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
                    or record["name"] == "traefik"
                    or record["name"] == f"traefik.{DO_DOMAIN}"
                ):
                    # Track root for legacy logic
                    if record["name"] == "@" or record["name"] == DO_DOMAIN or record["name"] == "":
                        found["AAAA_root"] = record
                        updated["AAAA_root"] = True
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

    # Automatically run post-deployment script
    post_deploy_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts/post_deploy_base2.sh")).replace("\\", "/")
    log(f"Running post-deployment script: {post_deploy_script} {ip_address}")
    try:
        result = subprocess.run(["bash", post_deploy_script, ip_address], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        log("Post-deployment script completed.")
    except Exception as e:
        err(f"Failed to run post-deployment script: {e}")
    exit(0)
except Exception as e:
    err(f"Droplet creation failed: {e}")
    try:
        recovery_ssh_logs(ip_address, SSH_USER, ssh_key_path)
    except Exception:
        pass
    try:
        print(f"[DROPLET ID] {droplet_id}")
    except Exception:
        print("[DROPLET ID] unknown (not available)")
    exit(1)

