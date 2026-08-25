#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -ne 4 ]]; then
  echo "usage: live-canary-remote.sh <fqdn> <project> <commit> <archive-sha256>" >&2
  exit 2
fi

fqdn="$1"
project="$2"
source_commit="$3"
archive_sha256="$4"
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
env_file="/run/base2-feature093-canary.env"
compose_file="$repo_root/development.docker.yml"

[[ "$fqdn" =~ ^[a-z0-9][a-z0-9.-]+\.[a-z]{2,63}$ ]] || exit 2
[[ "$project" =~ ^[a-z0-9][a-z0-9-]{6,62}$ ]] || exit 2
[[ "$source_commit" =~ ^[0-9a-f]{40}$ ]] || exit 2
[[ "$archive_sha256" =~ ^[0-9a-f]{64}$ ]] || exit 2

export DEBIAN_FRONTEND=noninteractive
if command -v cloud-init >/dev/null 2>&1; then
  cloud-init status --wait >/dev/null
fi
if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  apt-get update -qq
  apt-get install -y -qq ca-certificates curl docker.io docker-compose-v2
fi
systemctl enable --now docker >/dev/null

python3 "$repo_root/digital_ocean/scripts/python/render_live_canary_env.py" \
  --source "$repo_root/.env.example" \
  --target "$env_file" \
  --domain "$fqdn" \
  --project "$project" >/dev/null
chmod 600 "$env_file"

"$repo_root/scripts/bash/bootstrap-acme.sh" \
  --directory "$repo_root/letsencrypt" --uid 1000 --gid 1000

compose=(
  docker compose
  --project-name "$project"
  --env-file "$env_file"
  -f "$compose_file"
)
COMPOSE_ENV_FILE="$env_file" "${compose[@]}" up -d --build
mapfile -t services < <(COMPOSE_ENV_FILE="$env_file" "${compose[@]}" config --services)
[[ "${#services[@]}" -gt 0 ]] || exit 3

for attempt in $(seq 1 120); do
  ready=0
  pending=()
  for service in "${services[@]}"; do
    container_id="$(COMPOSE_ENV_FILE="$env_file" "${compose[@]}" ps -q "$service")"
    if [[ -z "$container_id" ]]; then
      pending+=("$service:absent")
      continue
    fi
    state="$(docker inspect --format '{{.State.Status}}' "$container_id")"
    health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{end}}' "$container_id")"
    if [[ "$state" == "running" && "$health" == "healthy" ]]; then
      ready=$((ready + 1))
    else
      pending+=("$service:$state:${health:-none}")
    fi
  done
  if [[ "$ready" -eq "${#services[@]}" ]]; then
    break
  fi
  if [[ "$attempt" -eq 120 ]]; then
    printf 'live canary services did not become healthy: %s\n' "${pending[*]}" >&2
    COMPOSE_ENV_FILE="$env_file" "${compose[@]}" ps >&2
    exit 4
  fi
  sleep 2
done

traefik_id="$(COMPOSE_ENV_FILE="$env_file" "${compose[@]}" ps -q traefik)"
docker exec "$traefik_id" sh -ec '
  grep -F "https://acme-staging-v02.api.letsencrypt.org/directory" /tmp/traefik.yml >/dev/null
  grep -F "acme-staging.json" /tmp/traefik.yml >/dev/null
  ! grep -F "acme-v02.api.letsencrypt.org/directory" /tmp/traefik.yml >/dev/null
'
rendered_dynamic="$(docker exec "$traefik_id" cat /tmp/dynamic.yml)"
[[ "$(grep -oF "$fqdn" <<<"$rendered_dynamic" | wc -l)" -eq 2 ]]
for forbidden in "www.$fqdn" "admin.$fqdn" "swagger.$fqdn" "pgadmin.$fqdn"; do
  ! grep -F "$forbidden" <<<"$rendered_dynamic" >/dev/null
done

python3 - "$source_commit" "$archive_sha256" "${#services[@]}" <<'PY'
import json, sys
print(json.dumps({
    "ok": True,
    "sourceCommit": sys.argv[1],
    "sourceArchiveSha256": sys.argv[2],
    "servicesHealthy": int(sys.argv[3]),
    "certificateMode": "letsencrypt-staging-only",
    "secretValuesEmitted": 0,
}, sort_keys=True))
PY
