#!/bin/bash
set -e

echo "User data script started at $(date)" | tee -a /var/log/cloud-init-output.log

touch /var/log/do_base_complete

echo "User data script completed at $(date)" | tee -a /var/log/cloud-init-output.log
#!/bin/bash

set -e

# Simple DigitalOcean base setup for user_data

log() { echo "[INFO] $1"; }

log "**********RUNNING BASH SCRIPT**********"
log "**********UPDATE'N**********"
DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Options::="--force-confnew" update
log "**********UPGRADING**********"
DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Options::="--force-confnew" --force-yes -fuy upgrade
log "**********UPGRADING END**********"
log "**********DIST-UPGRADING**********"
DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Options::="--force-confnew" --force-yes -fuy dist-upgrade
log "**********DIST-UPGRADING END**********"
log "**********REMOVING**********"
apt autoremove -y
log "**********REMOVING END**********"

# Create a new user (default: deploy)
NEWUSR=deploy
if ! id "$NEWUSR" &>/dev/null; then
    adduser --uid 1000 --disabled-password --gecos GECOS $NEWUSR
    log "**********CREATING USER**********"
    usermod -aG sudo $NEWUSR
    log "**********CREATING USER END**********"
else
    log "User $NEWUSR already exists."
fi

mkdir -p /home/$NEWUSR/.ssh
if [ -f /root/.ssh/authorized_keys ]; then
    cp /root/.ssh/authorized_keys /home/$NEWUSR/.ssh/authorized_keys
else
    touch /home/$NEWUSR/.ssh/authorized_keys
fi
chmod 700 /home/$NEWUSR/.ssh
chmod 600 /home/$NEWUSR/.ssh/authorized_keys
chown 1000:1000 -R /home/$NEWUSR/.ssh

log "**********INSTALLING GIT**********"
apt-get install git-all -y
log "**********INSTALLING GIT END**********"

log "**********CREATING DIRS**********"
mkdir -p /home/$NEWUSR/scripts
mkdir -p /home/$NEWUSR/base
cd /home/$NEWUSR/scripts
if [ ! -d base2 ]; then
    git clone https://github.com/woodkill00/base2.git
fi
chown 1000:1000 -R /home/$NEWUSR/scripts
chown 1000:1000 -R /home/$NEWUSR/base
chmod +x /home/$NEWUSR/scripts/base2/base_setup.sh || true
chmod +x /home/$NEWUSR/scripts/base2/docker_install.sh || true

log "**********CREATING DIRS END**********"

# Set up post-reboot script to log completion
CRON_LINE='@reboot /home/deploy/scripts/base2/digital_ocean/scripts/post_reboot_complete.sh'
crontab -u deploy -l 2>/dev/null | { cat; echo "$CRON_LINE"; } | crontab -u deploy -

log "**********FIXING UFW**********"
ufw allow 443
ufw allow 22
ufw allow 80
ufw --force enable
log "**********FIXING UFW END**********"

log "**********TURNING OFF APACHE**********"
systemctl disable apache2 2>/dev/null || true
systemctl stop apache2 2>/dev/null || true
log "**********TURNING OFF APACHE END**********"

# Set up auto-run after reboot (optional, can be customized)
# Example: echo '@reboot /home/$NEWUSR/scripts/base2/base_setup.sh >> /home/$NEWUSR/base_setup.log 2>&1' | crontab -u $NEWUSR -

log "**********ENDING SCRIPT + REBOOTING**********"
reboot now
