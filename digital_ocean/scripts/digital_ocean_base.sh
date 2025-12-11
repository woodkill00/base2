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
log "Updating and upgrading system packages..."
dpkg_lock_wait
apt-get update -y && apt-get upgrade -y
apt-get autoremove -y

dpkg_lock_wait
apt-get update -y
apt-get autoremove -y

dpkg_lock_wait
apt-get install -y curl python3-pip python3-venv make build-essential wget git

# --- Node.js and npm Install ---
dpkg_lock_wait
apt-get install -y nodejs npm

# --- Application Setup ---
dpkg_lock_wait
log "Cloning repo to $DEPLOY_PATH$PROJECT_NAME..."
mkdir -p "$DEPLOY_PATH$PROJECT_NAME"
if [ -d "$DEPLOY_PATH$PROJECT_NAME" ] && [ "$(ls -A "$DEPLOY_PATH$PROJECT_NAME")" ]; then
  log "$DEPLOY_PATH$PROJECT_NAME already exists and is not empty, skipping git clone."
else
  git clone https://github.com/woodkill00/base2.git "$DEPLOY_PATH$PROJECT_NAME"
fi

# --- Python Virtual Environment Setup ---
log "Setting up Python virtual environment..."

VENV_PATH="$DEPLOY_PATH$PROJECT_NAME/venv"
python3 -m venv "$VENV_PATH"
source "$VENV_PATH/bin/activate"
log "Virtual environment activated at $VENV_PATH."

log "Upgrading pip in venv..."
pip install --upgrade pip
log "Core tools installed and pip upgraded in venv."

# Ensure all subsequent commands use the venv
export VIRTUAL_ENV="$VENV_PATH"
export PATH="$VENV_PATH/bin:$PATH"

# --- Docker Install ---
log "Removing old Docker versions (if any)..."
dpkg_lock_wait
apt-get remove --yes docker docker-engine docker.io containerd runc || true

log "Installing Docker and Docker Compose (official method)..."
dpkg_lock_wait
apt-get update -y

dpkg_lock_wait
apt-get install -y ca-certificates curl gnupg lsb-release
install -m 0755 -d /etc/apt/keyrings
rm -f /etc/apt/keyrings/docker.gpg
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

dpkg_lock_wait
apt-get update -y

dpkg_lock_wait
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
usermod -aG docker $(whoami)
docker --version
systemctl enable docker
systemctl start docker
log "Docker installed and started successfully."

log "Waiting for Docker to start..."
sleep 5


# --- Docker Compose Standalone Install ---

log "Installing standalone Docker Compose binary..."
DOCKER_COMPOSE_LATEST=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d '"' -f4)
DOWNLOAD_URL="https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_LATEST}/docker-compose-$(uname -s)-$(uname -m)"
TMP_COMPOSE="/tmp/docker-compose"
HTTP_STATUS=$(curl -s -o "$TMP_COMPOSE" -w "%{http_code}" -L "$DOWNLOAD_URL")

if [ "$HTTP_STATUS" = "200" ] && file "$TMP_COMPOSE" | grep -q 'ELF'; then
  mv "$TMP_COMPOSE" /usr/local/bin/docker-compose
  chmod +x /usr/local/bin/docker-compose
  log "Standalone Docker Compose binary installed successfully."
else
  err "Failed to download valid Docker Compose binary (HTTP $HTTP_STATUS). Falling back to apt install."
  apt-get update -y
  apt-get install -y docker-compose
fi

docker compose version || true
docker-compose --version || true
log "Docker Compose (plugin and standalone) installed successfully."

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
