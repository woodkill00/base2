#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
runner="$repo_root/scripts/bash/e2e-isolated.sh"
lock_file="$repo_root/.artifacts/e2e-isolated.lock"
evidence_dir="$(mktemp -d --tmpdir base2-feature-106-concurrency.XXXXXXXX)"
owner_log="$evidence_dir/owner.log"
contender_log="$evidence_dir/contender.log"
owner_pid=''

cleanup() {
  if [[ -n "$owner_pid" ]] && kill -0 "$owner_pid" >/dev/null 2>&1; then
    kill "$owner_pid" >/dev/null 2>&1 || true
    wait "$owner_pid" >/dev/null 2>&1 || true
  fi
  rm -rf -- "$evidence_dir"
}
trap cleanup EXIT INT TERM

mkdir -p "$evidence_dir"
: >"$owner_log"
: >"$contender_log"
coproc OWNER { E2E_READY_FD=3 "$runner" 3>&1 >"$owner_log" 2>&1; }
owner_pid="$OWNER_PID"
if ! read -r -t 20 owner_ready <&"${OWNER[0]}" || [[ "$owner_ready" != ready ]]; then
  printf 'ERROR: owner did not publish isolated E2E lock readiness\n' >&2
  tail -40 "$owner_log" >&2
  exit 1
fi

set +e
"$runner" >"$contender_log" 2>&1
contender_rc="$?"
set -e
if [[ "$contender_rc" -ne 3 ]]; then
  printf 'ERROR: concurrent contender returned %s instead of 3\n' "$contender_rc" >&2
  cat "$contender_log" >&2
  exit 1
fi

set +e
wait "$owner_pid"
owner_rc="$?"
set -e
owner_pid=''
if [[ "$owner_rc" -ne 0 ]]; then
  printf 'ERROR: isolated E2E owner returned %s\n' "$owner_rc" >&2
  tail -80 "$owner_log" >&2
  exit 1
fi

if docker ps -a --format '{{.Names}}' | grep -q '^base2-e2e-isolated-'; then
  printf 'ERROR: exact-project containers remain after owner teardown\n' >&2
  exit 1
fi
if docker volume ls --format '{{.Name}}' | grep -q '^base2-e2e-isolated_'; then
  printf 'ERROR: exact-project volumes remain after owner teardown\n' >&2
  exit 1
fi
if docker network ls --format '{{.Name}}' | grep -q '^base2-e2e-isolated_'; then
  printf 'ERROR: exact-project networks remain after owner teardown\n' >&2
  exit 1
fi

grep -q '4 passed' "$owner_log"
grep -q 'fixed isolated E2E project is already in use' "$contender_log"
printf 'isolated_e2e_concurrency_proof=passed owner_rc=0 contender_rc=3 inventory=empty\n'
