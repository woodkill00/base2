
#!/bin/bash
# Digital Ocean droplet base setup script
# Run as root or with sudo, or via cloud-init user_data
set -o errexit
set -o nounset
set -o pipefail

export DEBIAN_FRONTEND=noninteractive
IFS=$(printf '\n\t')

# Update, upgrade, and clean
apt-get update -y && apt-get upgrade -y
apt-get autoremove -y

apt-get update -y
apt-get autoremove -y
apt-get install -y curl python3-pip python3-venv make build-essential wget git

# Upgrade pip
python3 -m pip install --upgrade pip

printf '\nCore tools installed and pip upgraded\n\n'

# Docker install (official method)
apt-get remove --yes docker docker-engine docker.io containerd runc || true
apt-get update -y
apt-get install -y ca-certificates curl gnupg lsb-release
install -m 0755 -d /etc/apt/keyrings
rm -f /etc/apt/keyrings/docker.gpg
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo \
	"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
	$(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
usermod -aG docker $(whoami)
docker --version
systemctl enable docker
systemctl start docker
printf '\nDocker installed and started successfully\n\n'

printf 'Waiting for Docker to start...\n\n'
sleep 5

# Docker Compose v2 (plugin)
docker compose version
printf '\nDocker Compose (plugin) installed successfully\n\n'

# Fix permissions for docker socket (optional, not always needed)
if [ -S /var/run/docker.sock ]; then
	chown $(whoami) /var/run/docker.sock || true
fi



# === Security and System Hardening ===

# 1. System update and upgrade (already done above, but repeat for safety)
apt-get update -y && apt-get upgrade -y


# 2. SSH hardening: disable password authentication
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
systemctl enable ssh
systemctl start ssh
systemctl reload sshd

# 3. UFW Firewall setup
apt-get install -y ufw
ufw default deny incoming

#!/bin/bash
# Digital Ocean droplet base setup script
# Run as root or with sudo, or via cloud-init user_data
# This script is idempotent and logs all major steps.
set -o errexit
set -o nounset
set -o pipefail

export DEBIAN_FRONTEND=noninteractive
IFS=$(printf '\n\t')

log() { echo -e "\033[1;32m[INFO]\033[0m $1"; }
err() { echo -e "\033[1;31m[ERROR]\033[0m $1" >&2; }

trap 'err "Script failed at line $LINENO"' ERR

log "Updating and upgrading system packages..."
apt-get update -y && apt-get upgrade -y
apt-get autoremove -y

log "Installing core tools..."
apt-get install -y curl python3-pip python3-venv make build-essential wget git

log "Upgrading pip..."
python3 -m pip install --upgrade pip

log "Removing old Docker versions (if any)..."
apt-get remove --yes docker docker-engine docker.io containerd runc || true

log "Installing Docker and Docker Compose (official method)..."
apt-get update -y
apt-get install -y ca-certificates curl gnupg lsb-release
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
usermod -aG docker $(whoami)
docker --version
systemctl enable docker
systemctl start docker

log "Waiting for Docker to start..."
sleep 5

docker compose version
log "Docker Compose (plugin) installed successfully."

# Fix permissions for docker socket (optional, not always needed)
if [ -S /var/run/docker.sock ]; then
	chown $(whoami) /var/run/docker.sock || true
fi

# === Security and System Hardening ===
log "Hardening SSH configuration..."
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
systemctl reload sshd

log "Setting up UFW firewall..."
apt-get install -y ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
# Add more ports as needed for your services
ufw --force enable
ufw status verbose

# === Secure Multi-Service Setup ===
log "Creating system users and directories for backend and frontend..."
useradd --system --no-create-home --shell /usr/sbin/nologin backend || true
useradd --system --no-create-home --shell /usr/sbin/nologin frontend || true
mkdir -p /srv/backend /srv/frontend
chown backend:backend /srv/backend
chown frontend:frontend /srv/frontend

log "Copying service code from local project root..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cp -r "$PROJECT_ROOT/backend/"* /srv/backend/
cp -r "$PROJECT_ROOT/react-app/"* /srv/frontend/
chown -R backend:backend /srv/backend
chown -R frontend:frontend /srv/frontend

log "Installing dependencies for backend and frontend..."
sudo -u backend bash -c 'cd /srv/backend && npm install'
sudo -u frontend bash -c 'cd /srv/frontend && npm install'

log "Setting up systemd services for backend and frontend..."
cat >/etc/systemd/system/backend.service <<EOF
[Unit]
Description=Base2 Backend Service
After=network.target

[Service]
Type=simple
User=backend
WorkingDirectory=/srv/backend
ExecStart=/usr/bin/npm run start
Restart=always

[Install]
WantedBy=multi-user.target
EOF

cat >/etc/systemd/system/frontend.service <<EOF
[Unit]
Description=Base2 Frontend Service
After=network.target

[Service]
Type=simple
User=frontend
WorkingDirectory=/srv/frontend
ExecStart=/usr/bin/npm run start
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable backend frontend
systemctl start backend frontend

log "All base setup and service steps completed."