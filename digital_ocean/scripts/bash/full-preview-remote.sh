#!/usr/bin/env bash
set -euo pipefail

stage="argument-validation"
trap 'code=$?; printf "full-preview-stage-failed:%s exit=%s\n" "$stage" "$code" >&2' ERR

if [[ "$#" -ne 5 ]]; then
  echo "usage: full-preview-remote.sh <domain> <project> <commit> <archive-sha256> <owner-cidr>" >&2
  exit 2
fi

domain="$1"
project="$2"
source_commit="$3"
archive_sha256="$4"
owner_cidr="$5"
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
env_file="/run/base2-full-preview.env"
operator_auth="/run/base2-operator.htpasswd"
flower_auth="/run/base2-flower.htpasswd"
compose_file="$repo_root/development.docker.yml"

[[ "$domain" =~ ^[a-z0-9][a-z0-9.-]+\.[a-z]{2,63}$ ]] || exit 2
[[ "$project" =~ ^[a-z0-9][a-z0-9-]{6,62}$ ]] || exit 2
[[ "$source_commit" =~ ^[0-9a-f]{40}$ ]] || exit 2
[[ "$archive_sha256" =~ ^[0-9a-f]{64}$ ]] || exit 2
[[ -f "$operator_auth" && -f "$flower_auth" ]] || { echo "private edge-auth files are missing" >&2; exit 2; }
chmod 600 "$operator_auth" "$flower_auth"

export DEBIAN_FRONTEND=noninteractive
stage="cloud-init-wait"
if command -v cloud-init >/dev/null 2>&1; then cloud-init status --wait >/dev/null; fi
stage="docker-install"
if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  apt-get update -qq
  apt-get install -y -qq ca-certificates curl docker.io docker-compose-v2
fi
stage="docker-start"
systemctl enable --now docker >/dev/null

stage="env-render"
python3 "$repo_root/digital_ocean/scripts/python/render_full_preview_env.py" \
  --source "$repo_root/.env.example" --target "$env_file" \
  --domain "$domain" --project "$project" --owner-cidr "$owner_cidr" \
  --operator-basic-auth-file "$operator_auth" --flower-basic-auth-file "$flower_auth" >/dev/null
chmod 600 "$env_file"
rm -f -- "$operator_auth" "$flower_auth"

stage="acme-bootstrap"
"$repo_root/scripts/bash/bootstrap-acme.sh" --directory "$repo_root/letsencrypt" --uid 1000 --gid 1000
compose=(docker compose --profile celery --project-name "$project" --env-file "$env_file" -f "$compose_file")
export COMPOSE_ENV_FILE="$env_file" COMPOSE_PARALLEL_LIMIT=1
stage="compose-build"
"${compose[@]}" build
stage="compose-up"
"${compose[@]}" up -d --no-build
stage="service-inventory"
mapfile -t services < <("${compose[@]}" config --services)
[[ "${#services[@]}" -gt 0 ]] || exit 3

stage="service-health"
for attempt in $(seq 1 180); do
  ready=0
  pending=()
  for service in "${services[@]}"; do
    container_id="$("${compose[@]}" ps -q "$service")"
    if [[ -z "$container_id" ]]; then pending+=("$service:absent"); continue; fi
    state="$(docker inspect --format '{{.State.Status}}' "$container_id")"
    health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{end}}' "$container_id")"
    if [[ "$state" == "running" && "$health" == "healthy" ]]; then
      ready=$((ready + 1))
    else
      pending+=("$service:$state:${health:-none}")
    fi
  done
  [[ "$ready" -eq "${#services[@]}" ]] && break
  if [[ "$attempt" -eq 180 ]]; then
    printf 'full preview services did not become healthy: %s\n' "${pending[*]}" >&2
    "${compose[@]}" ps >&2
    for service in "${services[@]}"; do "${compose[@]}" logs --tail 40 "$service" >&2 || true; done
    exit 4
  fi
  sleep 2
done

stage="traefik-policy"
traefik_id="$("${compose[@]}" ps -q traefik)"
docker exec "$traefik_id" sh -ec '
  grep -F "https://acme-staging-v02.api.letsencrypt.org/directory" /tmp/traefik.yml >/dev/null
  grep -F "acme-staging.json" /tmp/traefik.yml >/dev/null
  ! grep -F "acme-v02.api.letsencrypt.org/directory" /tmp/traefik.yml >/dev/null
  grep -F "operator-basic-auth" /tmp/dynamic.yml >/dev/null
  grep -F "owner-allow-ip" /tmp/dynamic.yml >/dev/null
'

stage="receipt"
python3 - "$source_commit" "$archive_sha256" "${#services[@]}" <<'PY'
import json, sys
print(json.dumps({
    "ok": True, "sourceCommit": sys.argv[1], "sourceArchiveSha256": sys.argv[2],
    "servicesHealthy": int(sys.argv[3]), "certificateMode": "letsencrypt-staging-only",
    "mode": "full-preview", "secretValuesEmitted": 0,
}, sort_keys=True))
PY
