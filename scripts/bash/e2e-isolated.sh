#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
lock_file="$repo_root/.artifacts/e2e-isolated.lock"
lock_args=(
  python3 "$repo_root/scripts/python/secure_file_lock.py"
  --lock "$lock_file"
  --root "$repo_root"
  --busy-exit 3
)
if [[ -n "${E2E_READY_FD:-}" ]]; then
  [[ "$E2E_READY_FD" =~ ^[0-9]+$ ]] || { printf 'ERROR: invalid E2E_READY_FD\n' >&2; exit 2; }
  lock_args+=(--ready-fd "$E2E_READY_FD")
fi

set +e
"${lock_args[@]}" -- bash "$repo_root/scripts/bash/e2e-isolated-body.sh" "$@"
lock_rc="$?"
set -e
if [[ "$lock_rc" -eq 3 ]]; then
  printf 'ERROR: the fixed isolated E2E project is already in use\n' >&2
fi
exit "$lock_rc"
