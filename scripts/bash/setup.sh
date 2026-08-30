#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if ! command -v node >/dev/null 2>&1; then
  echo "ERROR: node is required. Install Node.js 24.20.0+ and re-run." >&2
  exit 127
fi

exec node "${REPO_ROOT}/scripts/setup.js" "$@"
