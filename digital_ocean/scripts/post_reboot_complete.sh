#!/bin/bash
set -o errexit
set -o nounset
set -o pipefail

log() { echo -e "\033[1;32m[INFO]\033[0m $1"; }
err() { echo -e "\033[1;31m[ERROR]\033[0m $1" >&2; }
trap 'err "Script failed at line $LINENO"' ERR

DEPLOY_USER="deploy"
DEPLOY_HOME="/home/$DEPLOY_USER"
PROJECT_NAME_SAFE="${PROJECT_NAME:-base2}"
REPO_DIR_OPT="/opt/apps/${PROJECT_NAME_SAFE}"
if [ -d "$REPO_DIR_OPT" ]; then
	REPO_DIR="$REPO_DIR_OPT"
else
	REPO_DIR="${DEPLOY_PATH:-/srv/}${PROJECT_NAME_SAFE}"
fi

log "Ensuring deploy user exists and has docker access..."
if ! id "$DEPLOY_USER" >/dev/null 2>&1; then
	useradd -m -s /bin/bash "$DEPLOY_USER"
fi
usermod -aG docker "$DEPLOY_USER" || true

log "Setting sensible system defaults for builds/runtime..."
sysctl -w fs.inotify.max_user_watches=524288 || true
sysctl -w fs.inotify.max_user_instances=1024 || true

log "Ensuring scripts are executable..."
if [ -f "$REPO_DIR/scripts/start.sh" ]; then
	chmod +x "$REPO_DIR/scripts/start.sh" || true
else
	log "scripts/start.sh not found at $REPO_DIR; skipping chmod"
fi

LOGFILE="$DEPLOY_HOME/setup_complete.log"
mkdir -p "$DEPLOY_HOME"
chown -R "$DEPLOY_USER":"$DEPLOY_USER" "$DEPLOY_HOME" || true
echo "$(date) - Post-reboot configuration completed." | tee -a "$LOGFILE"
log "Post-reboot configuration completed."
