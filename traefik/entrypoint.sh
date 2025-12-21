#!/bin/sh
set -e


# Wait for ACME file(s) to exist, then set permissions and ownership

# Start Traefik in the background, monitor for ACME file creation, and fix permissions
su-exec traefik traefik --configFile=/etc/traefik/traefik.yml &
traefik_pid=$!

# Monitor and fix permissions for ACME files for up to 60 seconds
for i in $(seq 1 120); do
    for acmefile in /etc/traefik/acme/acme-staging.json /etc/traefik/acme/acme.json; do
        if [ -e "$acmefile" ]; then
            chmod 600 "$acmefile"
            chown traefik:traefik "$acmefile"
        fi
    done
    sleep 0.5
done

wait $traefik_pid


# Ensure log directory exists and is writable
mkdir -p /var/log/traefik
chown -R traefik:traefik /var/log/traefik
chmod -R 755 /var/log/traefik


# Start Traefik and fix ACME permissions in the background
start_traefik
