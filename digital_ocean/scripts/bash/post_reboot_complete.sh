#!/bin/bash
set -o errexit
set -o nounset
set -o pipefail

log() { echo -e "\033[1;32m[INFO]\033[0m $1"; }
err() { echo -e "\033[1;31m[ERROR]\033[0m $1" >&2; }
stage() { log "[STAGE] $1"; }
trap 'err "Script failed at line $LINENO"' ERR

DEPLOY_USER="deploy"
DEPLOY_HOME="/home/$DEPLOY_USER"
PROJECT_NAME_SAFE="${PROJECT_NAME:-app}"
REPO_DIR_OPT="/opt/apps/${PROJECT_NAME_SAFE}"
if [ -d "$REPO_DIR_OPT" ]; then
	REPO_DIR="$REPO_DIR_OPT"
else
	if [ -d "/opt/apps" ]; then
		CAND=$(ls -1 /opt/apps 2>/dev/null | head -n 1 || true)
		if [ -n "$CAND" ] && [ -d "/opt/apps/$CAND" ]; then
			REPO_DIR="/opt/apps/$CAND"
		else
			REPO_DIR="${DEPLOY_PATH:-/srv/}${PROJECT_NAME_SAFE}"
		fi
	else
		REPO_DIR="${DEPLOY_PATH:-/srv/}${PROJECT_NAME_SAFE}"
	fi
fi

stage "prepare traefik acme storage"
log "Ensuring Traefik ACME storage is writable by UID 1000..."
ACME_DIR="$REPO_DIR/letsencrypt"
"$REPO_DIR/scripts/bash/bootstrap-acme.sh" --directory "$ACME_DIR" --uid 1000 --gid 1000

stage "ensure deploy user"
log "Ensuring deploy user exists and has docker access..."
if ! id "$DEPLOY_USER" >/dev/null 2>&1; then
	useradd -m -s /bin/bash "$DEPLOY_USER"
fi
usermod -aG docker "$DEPLOY_USER" || true

stage "tune kernel defaults"
log "Setting sensible system defaults for builds/runtime..."
sysctl -w fs.inotify.max_user_watches=524288 || true
sysctl -w fs.inotify.max_user_instances=1024 || true

stage "ensure nodejs 24"
log "Ensuring Node.js 24.13.1+ is installed for frontend tests..."
if command -v node >/dev/null 2>&1; then
	NODE_MAJOR=$(node -v | sed 's/^v//' | cut -d'.' -f1)
else
	NODE_MAJOR=0
fi
if [ "${NODE_MAJOR}" -lt 24 ]; then
	apt-get update -y
	apt-get install -y ca-certificates curl gnupg
	# Remove distro-provided node packages that conflict with NodeSource.
	apt-get remove -y nodejs libnode-dev libnode72 nodejs-doc npm || true
	curl -fsSL https://deb.nodesource.com/setup_24.x | bash -
	apt-get install -y nodejs
fi

stage "ensure scripts executable"
log "Ensuring scripts are executable..."
if [ -f "$REPO_DIR/scripts/bash/start.sh" ]; then
	chmod +x "$REPO_DIR/scripts/bash/start.sh" || true
else
	log "scripts/bash/start.sh not found at $REPO_DIR; skipping chmod"
fi

LOGFILE="$DEPLOY_HOME/setup_complete.log"
mkdir -p "$DEPLOY_HOME"
chown -R "$DEPLOY_USER":"$DEPLOY_USER" "$DEPLOY_HOME" || true
stage "post-reboot complete"
echo "$(date) - Post-reboot configuration completed." | tee -a "$LOGFILE"
log "Post-reboot configuration completed."
