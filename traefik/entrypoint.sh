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

# Feature 093 is staging-only. A production-looking environment must not turn
# certificate issuance live; that requires a later, separately approved feature.
if [ "${TRAEFIK_CERT_RESOLVER:-le-staging}" != "le-staging" ]; then
  echo "Traefik certificate resolver must remain le-staging" >&2
  exit 78
fi
TRAEFIK_CERT_RESOLVER="le-staging"
export TRAEFIK_CERT_RESOLVER

# Render configs from templates using environment variables
STATIC_TEMPLATE_PATH="/etc/traefik/templates/traefik.yml.template"
STATIC_OUTPUT_PATH="/tmp/traefik.yml"
if [ -f "$STATIC_TEMPLATE_PATH" ]; then
  export TRAEFIK_DYNAMIC_FILE="/tmp/dynamic.yml"
  envsubst < "$STATIC_TEMPLATE_PATH" > "$STATIC_OUTPUT_PATH"
fi

DYNAMIC_TEMPLATE_PATH="/etc/traefik/templates/dynamic.yml.template"
if [ "${TRAEFIK_CANARY_MODE:-false}" = "true" ]; then
  DYNAMIC_TEMPLATE_PATH="/etc/traefik/templates/dynamic-canary.yml.template"
fi
DYNAMIC_OUTPUT_PATH="/tmp/dynamic.yml"
if [ -f "$DYNAMIC_TEMPLATE_PATH" ]; then
  envsubst < "$DYNAMIC_TEMPLATE_PATH" > "$DYNAMIC_OUTPUT_PATH"
fi

# The shared bootstrap prepares storage before startup. This entrypoint only
# verifies the staging file and never creates or selects live ACME storage.
if [ ! -f /etc/traefik/acme/acme-staging.json ]; then
  echo "Staging ACME storage is missing" >&2
  exit 78
fi
chmod 600 /etc/traefik/acme/acme-staging.json || true

# Run Traefik. With cap_drop=ALL, root cannot bypass DAC permissions, so we render configs into
# /tmp (tmpfs) and run using that config file.
exec traefik --configFile=/tmp/traefik.yml
