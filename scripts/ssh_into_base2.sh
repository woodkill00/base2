#!/bin/bash
# SSH into droplet and navigate to /opt/apps/base2, leaving shell open

DROPLET_IP="$1"
SSH_KEY="C:/Users/theju/.ssh/base2"

if [ -z "$DROPLET_IP" ]; then
  echo "Usage: $0 <droplet_ip>"
  exit 1
fi

ssh -o StrictHostKeyChecking=no -i "$SSH_KEY" root@"$DROPLET_IP" 'cd /opt/apps/base2 && source venv/bin/activate && exec bash'
