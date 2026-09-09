#!/bin/bash
# Digital Ocean droplet base setup script
# Run as root or with sudo, or via cloud-init user_data
set -o errexit
set -o nounset
set -o pipefail

export DEBIAN_FRONTEND=noninteractive
IFS=$(printf '\n\t')

# --- Logging Functions ---
log() { echo -e "\033[1;32m[INFO]\033[0m $1"; }
err() { echo -e "\033[1;31m[ERROR]\033[0m $1" >&2; }
trap 'err "Script failed at line $LINENO"' ERR

# Wait for dpkg/apt locks to be released
dpkg_lock_wait() {
  while fuser /var/lib/dpkg/lock >/dev/null 2>&1 || \
        fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 ; do
    echo "Waiting for other package managers to finish..." >&2
    sleep 3
  done
}

log "User data script started at $(date)"
echo "User data script started at $(date)" | tee -a /var/log/cloud-init-output.log

# --- System Update & Core Tools ---
log "Installing distribution-signed bootstrap packages..."
dpkg_lock_wait
apt-get update -y
apt-get install -y ca-certificates curl docker-compose-v2 docker.io git gnupg python3-venv ufw

# --- Application Setup ---
dpkg_lock_wait
log "Preparing an empty application directory; source transfer waits for pinned SSH enrollment..."
mkdir -p "$DEPLOY_PATH$PROJECT_NAME"

# --- Docker Install ---
usermod -aG docker $(whoami)
docker --version
systemctl enable docker
systemctl start docker
log "Docker installed and started successfully."

log "Waiting for Docker to start..."
sleep 5


docker compose version
log "Distribution-signed Docker Compose plugin is available."

# --- Docker Socket Permissions (optional) ---
if [ -S /var/run/docker.sock ]; then
  chown $(whoami) /var/run/docker.sock || true
fi

# --- Security and System Hardening ---
log "Hardening SSH configuration..."
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
systemctl enable ssh
systemctl start ssh
systemctl reload sshd

log "Setting up UFW firewall..."
dpkg_lock_wait
# Robust retry for ufw install if dpkg lock error occurs
for i in {1..10}; do
  apt-get install -y ufw && break
  log "ufw install failed due to lock, retrying in 5s (attempt $i)..."
  sleep 5
  dpkg_lock_wait
done
ufw default deny incoming
ufw default allow outgoing

# Safety: ensure Docker remote API ports are NOT exposed
ufw delete allow 2375/tcp >/dev/null 2>&1 || true
ufw delete allow 2376/tcp >/dev/null 2>&1 || true

ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
# Add more ports as needed for your services
ufw --force enable
ufw status verbose

touch /var/log/do_base_complete
log "User data script completed at $(date)"
echo "User data script completed at $(date)" | tee -a /var/log/cloud-init-output.log

log "Rebooting system to complete setup..."
echo "Rebooting system to complete setup..." | tee -a /var/log/cloud-init-output.log
sleep 2
reboot
