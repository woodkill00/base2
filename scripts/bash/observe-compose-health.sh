#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/development.docker.yml"
PROJECT_NAME="base2-f093-$$"
ENV_FILE="$(mktemp /tmp/base2-f093-compose.XXXXXX.env)"
ATTEMPTS="${OBSERVE_HEALTH_ATTEMPTS:-90}"
INTERVAL="${OBSERVE_HEALTH_INTERVAL_SECONDS:-2}"
TRAEFIK_CANARY_MODE="${OBSERVE_TRAEFIK_CANARY_MODE:-false}"
CLEANED_UP=false

cleanup() {
  if [[ "$CLEANED_UP" == "true" ]]; then
    return
  fi
  CLEANED_UP=true
  trap - EXIT INT TERM
  COMPOSE_PROJECT_NAME="$PROJECT_NAME" COMPOSE_ENV_FILE="$ENV_FILE" \
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" \
    down -v --remove-orphans >/dev/null 2>&1 || true
  rm -f -- "$ENV_FILE"
}
handle_signal() {
  local exit_code="$1"
  cleanup
  exit "$exit_code"
}
trap cleanup EXIT
trap 'handle_signal 130' INT
trap 'handle_signal 143' TERM

cd "$REPO_ROOT"

python3 - "$ENV_FILE" "$PROJECT_NAME" "$TRAEFIK_CANARY_MODE" <<'PY'
from pathlib import Path
import re
import sys

target, project, canary_mode = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
source = Path(".env.example").read_text(encoding="utf-8")
rendered = re.sub(r"\bYOUR_[A-Z0-9_]+\b", "fixture", source)
rendered = rendered.replace("PROJECT_NAME=fixture", f"PROJECT_NAME={project}")
rendered = rendered.replace(
    "WEBSITE_DOMAIN=fixture", f"WEBSITE_DOMAIN={project}.invalid"
)
rendered = rendered.replace("USER_MAIN_EMAIL=fixture", "USER_MAIN_EMAIL=fixture@example.com")
if canary_mode == "true":
    rendered += "\nTRAEFIK_CANARY_MODE=true\n"
target.write_text(rendered, encoding="utf-8")
PY
chmod 600 "$ENV_FILE"

"$SCRIPT_DIR/bootstrap-acme.sh" \
  --directory "$REPO_ROOT/letsencrypt" --uid 1000 --gid 1000

compose=(
  docker compose
  --project-name "$PROJECT_NAME"
  --env-file "$ENV_FILE"
  -f "$COMPOSE_FILE"
)

COMPOSE_ENV_FILE="$ENV_FILE" "${compose[@]}" up -d --build
mapfile -t services < <(COMPOSE_ENV_FILE="$ENV_FILE" "${compose[@]}" config --services)

if [[ "${#services[@]}" -lt 1 ]]; then
  echo "compose observation found no services" >&2
  exit 1
fi

for attempt in $(seq 1 "$ATTEMPTS"); do
  ready=0
  pending=()
  for service in "${services[@]}"; do
    container_id="$(COMPOSE_ENV_FILE="$ENV_FILE" "${compose[@]}" ps -q "$service")"
    if [[ -z "$container_id" ]]; then
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
  printf 'observation attempt=%s services=%s healthy=%s pending=%s\n' \
    "$attempt" "${#services[@]}" "$ready" "${pending[*]:-none}"
  if [[ "$ready" -eq "${#services[@]}" ]]; then
    break
  fi
  if [[ "$attempt" -eq "$ATTEMPTS" ]]; then
    COMPOSE_ENV_FILE="$ENV_FILE" "${compose[@]}" ps
    COMPOSE_ENV_FILE="$ENV_FILE" "${compose[@]}" logs --tail=80
    exit 1
  fi
  sleep "$INTERVAL"
done

COMPOSE_ENV_FILE="$ENV_FILE" "${compose[@]}" ps
stat -c 'acme-staging mode=%a uid=%u gid=%g size=%s' \
  "$REPO_ROOT/letsencrypt/acme-staging.json"

traefik_id="$(COMPOSE_ENV_FILE="$ENV_FILE" "${compose[@]}" ps -q traefik)"
docker exec "$traefik_id" sh -lc \
  'grep -F "https://acme-staging-v02.api.letsencrypt.org/directory" /tmp/traefik.yml >/dev/null && grep -F "acme-staging.json" /tmp/traefik.yml >/dev/null'

if [[ "$TRAEFIK_CANARY_MODE" == "true" ]]; then
  docker exec "$traefik_id" sh -ec '
    test "$(grep -oF "'"$PROJECT_NAME"'.invalid" /tmp/dynamic.yml | wc -l)" -eq 2
    ! grep -F "www.'"$PROJECT_NAME"'.invalid" /tmp/dynamic.yml >/dev/null
    ! grep -F "sans:" /tmp/dynamic.yml >/dev/null
  '
  echo 'traefik-canary-single-host=verified'
fi

echo 'traefik-staging-config=verified'
echo 'compose-health-observation=passed'
