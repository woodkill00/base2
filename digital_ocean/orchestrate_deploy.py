#!/usr/bin/env python3
"""
Orchestrate Digital Ocean Droplet deployment, DNS update, .env generation, and service startup.
- Requires: pydo, paramiko (for SSH/SCP), python-dotenv
- Usage: python orchestrate_deploy.py
"""

import os
import time
from pydo import Client
import paramiko
from dotenv import dotenv_values, set_key

def log(msg):
    print(f"\033[1;32m[INFO]\033[0m {msg}")
def err(msg):
    print(f"\033[1;31m[ERROR]\033[0m {msg}", flush=True)


# --- CONFIG ---
DO_API_TOKEN = os.getenv("DO_API_TOKEN")
DO_DOMAIN = os.getenv("DO_DOMAIN")  # e.g. example.com
DO_DROPLET_NAME = os.getenv("DO_DROPLET_NAME", "base2-droplet")
DO_API_REGION = os.getenv("DO_API_REGION", "nyc3")
DO_API_SIZE = os.getenv("DO_API_SIZE", "s-1vcpu-1gb")
DO_API_IMAGE = os.getenv("DO_API_IMAGE", "ubuntu-22-04-x64")
DO_SSH_KEY_ID = os.getenv("DO_SSH_KEY_ID")  # Must be set
LOCAL_ENV_PATH = os.getenv("LOCAL_ENV_PATH", os.path.abspath(os.path.join(os.path.dirname(__file__), "../.env")))
REMOTE_ENV_PATH = "/srv/backend/.env"  # Adjust as needed for your droplet
SSH_USER = os.getenv("SSH_USER", "root")

# --- 1. Create Droplet ---
client = Client(token=DO_API_TOKEN)
droplet_spec = {
    "name": DO_DROPLET_NAME,
    "region": DO_API_REGION,
    "size": DO_API_SIZE,
    "image": DO_API_IMAGE,
    "ssh_keys": [DO_SSH_KEY_ID],
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

log("Updating DNS A records...")
try:
    records = client.domains.records(DO_DOMAIN)["domain_records"]
    for record in records:
        if record["type"] == "A":
            client.domains.update_record(DO_DOMAIN, record["id"], {"data": ip_address})
            log(f"Updated A record {record['name']} -> {ip_address}")
except Exception as e:
    err(f"DNS update failed: {e}")
    exit(1)

# --- 4. Generate/Update .env File Locally ---

log("Updating .env file with new IP/domain...")
try:
    env = dotenv_values(LOCAL_ENV_PATH)
    env["BACKEND_HOST"] = ip_address  # or whatever key you use
    with open(LOCAL_ENV_PATH, "w") as f:
        for k, v in env.items():
            f.write(f"{k}={v}\n")
except Exception as e:
    err(f".env update failed: {e}")
    exit(1)


log("Copying .env to droplet...")
try:
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(ip_address, username=SSH_USER, key_filename=os.path.expanduser("~/.ssh/id_rsa"))
    sftp = ssh_client.open_sftp()
    sftp.put(LOCAL_ENV_PATH, REMOTE_ENV_PATH)
    sftp.close()
except Exception as e:
    err(f"SCP failed: {e}")
    exit(1)

# --- 6. Start Services/Containers with start.sh ---



log("Running scripts/start.sh --build on droplet...")
remote_script_path = "/srv/backend/scripts/start.sh"  # Path on droplet; local script is not used
cmd = f"bash {remote_script_path} --build"
stdin, stdout, stderr = ssh_client.exec_command(cmd)
build_out = stdout.read().decode()
build_err = stderr.read().decode()
if build_out:
    log(build_out)
if build_err:
    err(build_err)

# --- Health Checks ---
log("Checking Docker and service health on droplet...")
health_cmds = [
    "docker ps",
    "docker compose ps || docker-compose ps || true",
    "curl -s -o /dev/null -w '%{http_code}' http://localhost:80",
    "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000 || true"  # adjust ports as needed
]
for hcmd in health_cmds:
    stdin, stdout, stderr = ssh_client.exec_command(hcmd)
    out, err_ = stdout.read().decode(), stderr.read().decode()
    if out.strip():
        log(f"[HEALTH] {hcmd}\n{out}")
    if err_.strip():
        err(f"[HEALTH-ERR] {hcmd}\n{err_}")

ssh_client.close()

log("Deployment complete! All health checks run.")
