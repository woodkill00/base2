#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
compose_file="$repo_root/e2e/docker-compose.e2e.yml"
project="base2-e2e-isolated"
lock_file="$repo_root/.artifacts/e2e-isolated.lock"
if [[ "${BASE2_E2E_LOCK_HELD:-}" != 1 ]]; then
  lock_args=(
    python3 "$repo_root/scripts/python/secure_file_lock.py"
    --lock "$lock_file"
    --root "$repo_root"
    --held-environment BASE2_E2E_LOCK_HELD
    --busy-exit 3
  )
  if [[ -n "${E2E_READY_FD:-}" ]]; then
    [[ "$E2E_READY_FD" =~ ^[0-9]+$ ]] || { printf 'ERROR: invalid E2E_READY_FD\n' >&2; exit 2; }
    lock_args+=(--ready-fd "$E2E_READY_FD")
  fi
  set +e
  "${lock_args[@]}" -- "$0" "$@"
  lock_rc="$?"
  set -e
  if [[ "$lock_rc" -eq 3 ]]; then
    printf 'ERROR: the fixed isolated E2E project is already in use\n' >&2
  fi
  exit "$lock_rc"
fi

E2E_API_PORT="${E2E_API_PORT:-15001}"
E2E_TEST_SUPPORT_PORT="${E2E_TEST_SUPPORT_PORT:-15002}"
E2E_WEB_PORT="${E2E_WEB_PORT:-18080}"

validate_port() {
  local name="$1" value="$2"
  if [[ ! "$value" =~ ^[0-9]{4,5}$ ]] || ((value < 1024 || value > 65535)); then
    printf 'ERROR: %s must be a numeric unprivileged TCP port\n' "$name" >&2
    exit 2
  fi
}

validate_port E2E_API_PORT "$E2E_API_PORT"
validate_port E2E_TEST_SUPPORT_PORT "$E2E_TEST_SUPPORT_PORT"
validate_port E2E_WEB_PORT "$E2E_WEB_PORT"
if [[ "$E2E_API_PORT" == "$E2E_TEST_SUPPORT_PORT" || "$E2E_API_PORT" == "$E2E_WEB_PORT" || "$E2E_TEST_SUPPORT_PORT" == "$E2E_WEB_PORT" ]]; then
  printf 'ERROR: isolated E2E ports must be distinct\n' >&2
  exit 2
fi

export E2E_API_PORT E2E_TEST_SUPPORT_PORT E2E_WEB_PORT
export E2E_WEB_ORIGIN="http://127.0.0.1:$E2E_WEB_PORT"

compose=(docker compose -p "$project" -f "$compose_file")
cleanup() {
  "${compose[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

# The fixed project boundary makes this preclean incapable of touching an
# unrelated Base2 stack while guaranteeing a genuinely empty database volume.
"${compose[@]}" down -v --remove-orphans
"${compose[@]}" up -d --build

ready=false
for _ in $(seq 1 90); do
  if curl -fsS "http://127.0.0.1:$E2E_API_PORT/api/health" >/dev/null \
    && curl -fsS "http://127.0.0.1:$E2E_TEST_SUPPORT_PORT/synthetic-health" >/dev/null \
    && curl -fsS "http://127.0.0.1:$E2E_WEB_PORT/" >/dev/null; then
    ready=true
    break
  fi
  sleep 2
done
if [[ "$ready" != true ]]; then
  "${compose[@]}" ps >&2
  "${compose[@]}" logs --no-color >&2
  printf 'ERROR: isolated E2E stack did not become ready\n' >&2
  exit 1
fi

cd "$repo_root/e2e"
E2E_API_URL="http://127.0.0.1:$E2E_API_PORT" \
E2E_TEST_SUPPORT_URL="http://127.0.0.1:$E2E_TEST_SUPPORT_PORT" \
E2E_BASE_URL="$E2E_WEB_ORIGIN" \
E2E_TEST_KEY=local-e2e-key npm run test:ci
