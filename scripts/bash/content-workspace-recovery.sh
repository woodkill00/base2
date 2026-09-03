#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
if [[ $# -ne 3 || ( "$1" != "backup" && "$1" != "restore" ) ]]; then
  echo "usage: content-workspace-recovery.sh backup|restore SOURCE TARGET" >&2
  exit 64
fi
exec "$root/.venv-api/bin/python" "$root/scripts/python/content_workspace_recovery.py" "$1" "$2" "$3"
