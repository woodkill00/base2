#!/bin/sh
set -eu

# Ensure directories exist
mkdir -p /etc/traefik/dynamic /etc/traefik/templates /etc/traefik/acme /var/log/traefik

# Render dynamic config from template using environment variables
TEMPLATE_PATH="/etc/traefik/templates/dynamic.yml.template"
OUTPUT_PATH="/etc/traefik/dynamic/dynamic.yml"
if [ -f "$TEMPLATE_PATH" ]; then
  envsubst < "$TEMPLATE_PATH" > "$OUTPUT_PATH"
fi

# Ensure ACME storage files exist with safe perms
touch /etc/traefik/acme/acme.json /etc/traefik/acme/acme-staging.json
chmod 600 /etc/traefik/acme/acme.json /etc/traefik/acme/acme-staging.json || true
chown -R traefik:traefik /etc/traefik/acme /var/log/traefik || true
chmod -R 755 /var/log/traefik || true

# Drop privileges and run Traefik
exec su-exec traefik:traefik traefik --configFile=/etc/traefik/traefik.yml
