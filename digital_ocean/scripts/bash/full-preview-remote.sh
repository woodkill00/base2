#!/usr/bin/env bash
set -euo pipefail

stage="argument-validation"
trap 'code=$?; printf "full-preview-stage-failed:%s exit=%s\n" "$stage" "$code" >&2' ERR

fail_stage() {
  local code="$1"
  printf 'full-preview-stage-failed:%s exit=%s\n' "$stage" "$code" >&2
  exit "$code"
}

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
django_username="/run/base2-django.username"
django_email="/run/base2-django.email"
django_password="/run/base2-django.password"
pgadmin_email="/run/base2-pgadmin.email"
pgadmin_password="/run/base2-pgadmin.password"
inspector_private_pem="/run/base2-media-inspector.pem"
compose_file="$repo_root/development.docker.yml"

cleanup_private_inputs() {
  rm -f -- "$inspector_private_pem"
}
trap cleanup_private_inputs EXIT

[[ "$domain" =~ ^[a-z0-9][a-z0-9.-]+\.[a-z]{2,63}$ ]] || fail_stage 2
[[ "$project" =~ ^[a-z0-9][a-z0-9-]{6,62}$ ]] || fail_stage 2
[[ "$source_commit" =~ ^[0-9a-f]{40}$ ]] || fail_stage 2
[[ "$archive_sha256" =~ ^[0-9a-f]{64}$ ]] || fail_stage 2
for private_input in "$operator_auth" "$flower_auth" "$django_username" "$django_email" "$django_password" "$pgadmin_email" "$pgadmin_password"; do
  [[ -f "$private_input" && ! -L "$private_input" ]] || { echo "private authentication input is missing" >&2; exit 2; }
  chmod 600 "$private_input"
done

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
(
  cd "$repo_root"
  python3 -m digital_ocean.scripts.python.render_full_preview_env \
    --source .env.example --target "$env_file" \
    --domain "$domain" --project "$project" --owner-cidr "$owner_cidr" \
    --operator-basic-auth-file "$operator_auth" --flower-basic-auth-file "$flower_auth" \
    --django-username-file "$django_username" --django-email-file "$django_email" \
    --django-password-file "$django_password" --pgadmin-email-file "$pgadmin_email" \
    --pgadmin-password-file "$pgadmin_password" >/dev/null
)
chmod 600 "$env_file"
rm -f -- "$operator_auth" "$flower_auth" "$django_username" "$django_email" "$django_password" "$pgadmin_email" "$pgadmin_password"

stage="media-inspector-attestation"
umask 077
openssl genpkey -algorithm ED25519 -out "$inspector_private_pem" >/dev/null 2>&1
inspector_signing_key="$(openssl pkey -in "$inspector_private_pem" -outform DER | tail -c 32 | base64 -w0)"
inspector_verify_key="$(openssl pkey -in "$inspector_private_pem" -pubout -outform DER | tail -c 32 | base64 -w0)"
[[ "$(printf '%s' "$inspector_signing_key" | base64 -d | wc -c)" -eq 32 ]] || fail_stage 3
[[ "$(printf '%s' "$inspector_verify_key" | base64 -d | wc -c)" -eq 32 ]] || fail_stage 3
sed -i \
  -e '/^MEDIA_INSPECTOR_SIGNING_KEY=/d' \
  -e '/^MEDIA_INSPECTOR_VERIFY_KEY=/d' \
  -e '/^MEDIA_INSPECTOR_BUILD_IDENTITY=/d' \
  "$env_file"
{
  printf 'MEDIA_INSPECTOR_SIGNING_KEY=%s\n' "$inspector_signing_key"
  printf 'MEDIA_INSPECTOR_VERIFY_KEY=%s\n' "$inspector_verify_key"
  # The final value is replaced with the content-addressed image ID after build.
  printf 'MEDIA_INSPECTOR_BUILD_IDENTITY=base2-media-inspector:%064d\n' 0
} >>"$env_file"
unset inspector_signing_key inspector_verify_key
rm -f -- "$inspector_private_pem"

stage="acme-bootstrap"
"$repo_root/scripts/bash/bootstrap-acme.sh" --directory "$repo_root/letsencrypt" --uid 1000 --gid 1000
compose=(docker compose --profile celery --profile media-scan --project-name "$project" --env-file "$env_file" -f "$compose_file")
export COMPOSE_ENV_FILE="$env_file" COMPOSE_PARALLEL_LIMIT=1
stage="compose-build"
"${compose[@]}" build
inspector_image_ref="${project}-media-inspector"
inspector_image_id="$(docker image inspect --format '{{.Id}}' "$inspector_image_ref")"
[[ "$inspector_image_id" =~ ^sha256:[a-f0-9]{64}$ ]] || fail_stage 3
inspector_build_identity="base2-media-inspector:${inspector_image_id#sha256:}"
env_replacement="$(mktemp /run/base2-preview-env.XXXXXX)"
chmod 600 "$env_replacement"
awk -v identity="$inspector_build_identity" \
  'BEGIN { replaced=0 }
   /^MEDIA_INSPECTOR_BUILD_IDENTITY=/ { print "MEDIA_INSPECTOR_BUILD_IDENTITY=" identity; replaced=1; next }
   { print }
   END { if (!replaced) exit 3 }' "$env_file" >"$env_replacement" || fail_stage 3
mv -f -- "$env_replacement" "$env_file"
stage="clamav-warmup"
"${compose[@]}" up -d --no-build clamav
for attempt in $(seq 1 180); do
  clamav_id="$("${compose[@]}" ps -q clamav)"
  if [[ -n "$clamav_id" ]]; then
    clamav_state="$(docker inspect --format '{{.State.Status}}' "$clamav_id")"
    clamav_health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{end}}' "$clamav_id")"
    clamav_oom="$(docker inspect --format '{{.State.OOMKilled}}' "$clamav_id")"
    if [[ "$clamav_state" == "running" && "$clamav_health" == "healthy" && "$clamav_oom" == "false" ]]; then
      break
    fi
    if [[ "$clamav_oom" == "true" || "$clamav_state" == "exited" || "$clamav_health" == "unhealthy" ]]; then
      "${compose[@]}" logs --tail 40 clamav >&2 || true
      fail_stage 4
    fi
  fi
  if [[ "$attempt" -eq 180 ]]; then
    "${compose[@]}" logs --tail 40 clamav >&2 || true
    fail_stage 4
  fi
  sleep 2
done
unset clamav_id clamav_state clamav_health clamav_oom
stage="compose-up"
"${compose[@]}" up -d --no-build
stage="media-inspector-identity"
inspector_container_id="$("${compose[@]}" ps -q media-inspector)"
[[ -n "$inspector_container_id" ]] || fail_stage 3
running_inspector_image="$(docker inspect --format '{{.Image}}' "$inspector_container_id")"
[[ "$running_inspector_image" == "$inspector_image_id" ]] || fail_stage 3
unset inspector_image_ref inspector_image_id inspector_build_identity inspector_container_id running_inspector_image
stage="api-migrations"
"${compose[@]}" exec -T api python -m api.scripts.migrate >/dev/null
stage="service-inventory"
mapfile -t services < <("${compose[@]}" config --services)
[[ "${#services[@]}" -gt 0 ]] || exit 3
one_shot_services=(workspace-db-role media-inspector-spool-init)

stage="service-health"
for attempt in $(seq 1 180); do
  ready=0
  pending=()
  for service in "${services[@]}"; do
    container_id="$("${compose[@]}" ps -a -q "$service")"
    if [[ -z "$container_id" ]]; then pending+=("$service:absent"); continue; fi
    state="$(docker inspect --format '{{.State.Status}}' "$container_id")"
    health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{end}}' "$container_id")"
    exit_code="$(docker inspect --format '{{.State.ExitCode}}' "$container_id")"
    if [[ " ${one_shot_services[*]} " == *" $service "* ]]; then
      if [[ "$state" == "exited" && "$exit_code" == "0" ]]; then
        ready=$((ready + 1))
      else
        pending+=("$service:$state:exit-$exit_code")
      fi
      continue
    fi
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
    fail_stage 4
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
