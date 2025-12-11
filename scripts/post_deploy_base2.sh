
#!/bin/bash
set -x
# SSH into droplet, copy .env, run npm install, and start the app

DROPLET_IP="$1"
SSH_KEY="C:/Users/theju/.ssh/base2"
LOCAL_ENV="$(dirname "$0")/../.env"
REMOTE_PATH="/opt/apps/base2"

echo "[DEBUG] DROPLET_IP: $DROPLET_IP"
echo "[DEBUG] SSH_KEY: $SSH_KEY"
echo "[DEBUG] LOCAL_ENV: $LOCAL_ENV"
echo "[DEBUG] REMOTE_PATH: $REMOTE_PATH"

if [ -z "$DROPLET_IP" ]; then
  echo "Usage: $0 <droplet_ip>"
  exit 1
fi

if [ ! -f "$SSH_KEY" ]; then
  echo "[ERROR] SSH key not found at $SSH_KEY"
  exit 2
fi

if [ ! -f "$LOCAL_ENV" ]; then
  echo "[ERROR] .env file not found at $LOCAL_ENV"
  exit 3
fi

echo "[INFO] Copying .env file to droplet..."
scp -v -o StrictHostKeyChecking=no -i "$SSH_KEY" "$LOCAL_ENV" root@"$DROPLET_IP":"$REMOTE_PATH/.env"
SCP_EXIT=$?
if [ $SCP_EXIT -ne 0 ]; then
  echo "[ERROR] scp failed with exit code $SCP_EXIT"
  exit $SCP_EXIT
fi

echo "[INFO] Running remote setup and streaming logs..."
ssh -v -o StrictHostKeyChecking=no -i "$SSH_KEY" root@"$DROPLET_IP" "cd $REMOTE_PATH && source venv/bin/activate && npm install && bash scripts/start.sh -build & BUILD_PID=$!; echo '--- Streaming Docker Container Logs ---'; while kill -0 $BUILD_PID 2>/dev/null; do docker ps --format '{{.Names}}' | xargs -I {} sh -c 'echo ==== {} ====; docker logs --tail=20 {}'; sleep 5; done; wait $BUILD_PID; echo 'Build completed.'"
SSH_EXIT=$?
if [ $SSH_EXIT -ne 0 ]; then
  echo "[ERROR] ssh failed with exit code $SSH_EXIT"
  exit $SSH_EXIT
fi
