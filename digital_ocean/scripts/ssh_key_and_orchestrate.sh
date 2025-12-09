#!/bin/bash
# SSH key setup and orchestration launcher for project
set -euo pipefail


PROJECT_NAME=$(grep '^DO_DROPLET_NAME=' "$(dirname "$0")/../../.env" | cut -d'=' -f2 | tr -d '\r')
KEY_PATH="$HOME/.ssh/project_${PROJECT_NAME}"
KEY_COMMENT="base2 Digital Ocean automation key for $PROJECT_NAME"
ENV_PATH="$(dirname "$0")/../../.env"

if [ -z "$PROJECT_NAME" ]; then
  echo "[ERROR] Could not determine project name from .env (DO_DROPLET_NAME)" >&2
  exit 1
fi

if [ ! -f "$KEY_PATH" ]; then
  echo "[INFO] Generating SSH key: $KEY_PATH"
  ssh-keygen -t ed25519 -f "$KEY_PATH" -C "$KEY_COMMENT" -N ""
else
  echo "[INFO] SSH key already exists: $KEY_PATH"
fi

# Copy public key to .env for DO_API_SSH_KEYS
PUB_KEY=$(cat "$KEY_PATH.pub")
if grep -q '^DO_API_SSH_KEYS=' "$ENV_PATH"; then
  sed -i.bak "/^DO_API_SSH_KEYS=/c\DO_API_SSH_KEYS=\"$PUB_KEY\"" "$ENV_PATH"
else
  echo "DO_API_SSH_KEYS=\"$PUB_KEY\"" >> "$ENV_PATH"
fi
echo "[INFO] Updated .env with DO_API_SSH_KEYS."

# Export for orchestrate script
export DO_SSH_KEY_ID="$KEY_PATH"

# Launch orchestrate_deploy.py from digital_ocean/
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ORCH_PATH="$SCRIPT_DIR/../orchestrate_deploy.py"


if [ ! -f "$ORCH_PATH" ]; then
  echo "[ERROR] Could not find orchestrate_deploy.py at $ORCH_PATH" >&2
  exit 1
fi

# Pass --dry-run if provided to this script
if [[ "$*" == *--dry-run* ]]; then
  python3 "$ORCH_PATH" --dry-run
else
  python3 "$ORCH_PATH"
fi
