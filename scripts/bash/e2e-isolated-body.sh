#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
compose_file="$repo_root/e2e/docker-compose.e2e.yml"
project="base2-e2e-isolated"
lock_file="$repo_root/.artifacts/e2e-isolated.lock"
lock_fd="${BASE2_SECURE_LOCK_FD:-}"
[[ "$lock_fd" =~ ^[0-9]+$ ]] || { printf 'ERROR: secure E2E lock capability is missing\n' >&2; exit 2; }
python3 "$repo_root/scripts/python/secure_file_lock.py" \
  --lock "$lock_file" --root "$repo_root" --verify-fd "$lock_fd"
unset BASE2_SECURE_LOCK_FD

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

# Local service proof only: loopback HTTP/non-Secure cookies, not edge TLS acceptance.
# A ready asset fixture is not scanner acceptance; controlled-clock calls are not beat proof.
artifacts="$repo_root/e2e/artifacts"
[[ ! -L "$artifacts" ]] || { printf 'ERROR: unsafe E2E artifact directory\n' >&2; exit 2; }
mkdir -p "$artifacts"
chmod 700 "$artifacts"
for name in source-commit.txt playwright.json compose-ps.txt compose.log cleanup.log exit-code.txt; do
  member="$artifacts/$name"
  [[ ! -L "$member" && ( ! -e "$member" || -f "$member" ) ]] || { printf 'ERROR: unsafe E2E artifact member\n' >&2; exit 2; }
  rm -f -- "$member"
done
git -C "$repo_root" rev-parse HEAD > "$artifacts/source-commit.txt"
export PLAYWRIGHT_JSON_OUTPUT_NAME="$artifacts/playwright.json"

compose=(docker compose -p "$project" -f "$compose_file")
cleanup() {
  local rc=$?
  trap - EXIT INT TERM
  "${compose[@]}" ps -a > "$artifacts/compose-ps.txt" 2>&1 || true
  "${compose[@]}" logs --no-color > "$artifacts/compose.log" 2>&1 || true
  "${compose[@]}" down -v --remove-orphans > "$artifacts/cleanup.log" 2>&1 || { ((rc != 0)) || rc=1; }
  printf '%s\n' "$rc" > "$artifacts/exit-code.txt"
  exit "$rc"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

"${compose[@]}" down -v --remove-orphans
"${compose[@]}" up -d --build --wait --wait-timeout 240

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
E2E_TEST_KEY=local-e2e-key npm run test:ci -- --reporter=line,json --workers=1
