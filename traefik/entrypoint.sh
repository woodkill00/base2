#!/bin/sh
set -eu

# Ensure directories exist
mkdir -p /etc/traefik/dynamic /etc/traefik/templates /etc/traefik/acme /var/log/traefik

# ---- FIX: unescape $$ -> $ for htpasswd/bcrypt user strings ----
unescape_dollars() {
  # usage: unescape_dollars VAR_NAME
  name="$1"
  eval "val=\${$name:-}"
  if [ -n "${val:-}" ]; then
    # replace all occurrences of $$ with $
    val=$(printf '%s' "$val" | sed 's/\$\$/\$/g')
    eval "export $name=\"\$val\""
  fi
}

# Variables used in traefik dynamic config (basicAuth users)
unescape_dollars TRAEFIK_DASH_BASIC_USERS
unescape_dollars FLOWER_BASIC_USERS
# add any other *BASIC_USERS vars you have here
# ---------------------------------------------------------------

# Render configs from templates using environment variables
STATIC_TEMPLATE_PATH="/etc/traefik/templates/traefik.yml.template"
STATIC_OUTPUT_PATH="/etc/traefik/traefik.yml"
if [ -f "$STATIC_TEMPLATE_PATH" ]; then
  envsubst < "$STATIC_TEMPLATE_PATH" > "$STATIC_OUTPUT_PATH"
fi

DYNAMIC_TEMPLATE_PATH="/etc/traefik/templates/dynamic.yml.template"
DYNAMIC_OUTPUT_PATH="/etc/traefik/dynamic/dynamic.yml"
if [ -f "$DYNAMIC_TEMPLATE_PATH" ]; then
  envsubst < "$DYNAMIC_TEMPLATE_PATH" > "$DYNAMIC_OUTPUT_PATH"
fi

# Ensure ACME storage files exist with safe perms
touch /etc/traefik/acme/acme.json /etc/traefik/acme/acme-staging.json
chmod 600 /etc/traefik/acme/acme.json /etc/traefik/acme/acme-staging.json || true
chown -R traefik:traefik /etc/traefik/acme /var/log/traefik || true
chmod -R 755 /var/log/traefik || true

# Drop privileges and run Traefik
exec su-exec traefik:traefik traefik --configFile=/etc/traefik/traefik.yml
