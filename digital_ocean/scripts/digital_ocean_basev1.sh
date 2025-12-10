#!/bin/bash
set -e

echo "User data script started at $(date)" | tee -a /var/log/cloud-init-output.log

# Install git
apt-get update -y
apt-get install -y git

# Clone repo to /opt/base2
mkdir -p /opt/base2
git clone https://github.com/woodkill00/base2.git /opt/base2

# Set up UFW
ufw allow 22
ufw allow 80
ufw allow 443
ufw --force enable

touch /var/log/do_base_complete

echo "User data script completed at $(date)" | tee -a /var/log/cloud-init-output.log
