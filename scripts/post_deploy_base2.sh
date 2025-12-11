#!/bin/bash
# SSH into droplet, copy .env, run npm install, and start the app

DROPLET_IP="$1"
SSH_KEY="C:/Users/theju/.ssh/base2"
LOCAL_ENV="../.env"
REMOTE_PATH="/opt/apps/base2"

if [ -z "$DROPLET_IP" ]; then
  echo "Usage: $0 <droplet_ip>"
  exit 1
fi

# Copy .env file to droplet
scp -o StrictHostKeyChecking=no -i "$SSH_KEY" "$LOCAL_ENV" root@"$DROPLET_IP":"$REMOTE_PATH/.env"

# SSH, run setup commands, and continuously stream logs for all running containers until build completes
ssh -o StrictHostKeyChecking=no -i "$SSH_KEY" root@"$DROPLET_IP" "cd $REMOTE_PATH && source venv/bin/activate && npm install && bash scripts/start.sh -build & BUILD_PID=$!; echo '--- Streaming Docker Container Logs ---'; while kill -0 $BUILD_PID 2>/dev/null; do docker ps --format '{{.Names}}' | xargs -I {} sh -c 'echo ==== {} ====; docker logs --tail=20 {}'; sleep 5; done; wait $BUILD_PID; echo 'Build completed.'"
