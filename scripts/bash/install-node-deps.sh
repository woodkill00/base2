#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  echo "Virtual environment not active. Run ./scripts/bash/first-start.sh to activate .venv before installing Node dependencies." >&2
  exit 1
fi

if ! command -v node >/dev/null 2>&1; then
  echo "node executable not found in PATH. Install Node.js 24.13.1+ and retry." >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm executable not found in PATH. Install npm 11.10.0+ and retry." >&2
  exit 1
fi

parse_version() {
  local version="$1"
  version="${version#v}"
  IFS='.' read -r major minor patch <<<"$version"
  echo "${major:-0} ${minor:-0} ${patch:-0}"
}

version_ge() {
  local left="$1"
  local right="$2"
  local l_major l_minor l_patch r_major r_minor r_patch
  read -r l_major l_minor l_patch <<<"$(parse_version "$left")"
  read -r r_major r_minor r_patch <<<"$(parse_version "$right")"
  if ((l_major > r_major)); then
    return 0
  fi
  if ((l_major < r_major)); then
    return 1
  fi
  if ((l_minor > r_minor)); then
    return 0
  fi
  if ((l_minor < r_minor)); then
    return 1
  fi
  if ((l_patch >= r_patch)); then
    return 0
  fi
  return 1
}

required_node="24.13.1"
node_version="$(node --version)"
if ! version_ge "$node_version" "$required_node"; then
  echo "Node.js version ${required_node}+ is required but found ${node_version}." >&2
  exit 1
fi

required_npm="11.10.0"
npm_version="$(npm --version)"
if ! version_ge "$npm_version" "$required_npm"; then
  echo "npm version ${required_npm}+ required but found ${npm_version}." >&2
  exit 1
fi

echo "Node version: $(node --version); npm version: $(npm --version)"

doinstall() {
  local dir="$1"
  local label="$2"
  local allow_legacy="$3"

  pushd "$dir" >/dev/null
  if ! npm install --no-fund; then
    if [[ "$allow_legacy" == "true" ]]; then
      echo "npm install ($label) failed; retrying with --legacy-peer-deps."
      npm install --no-fund --legacy-peer-deps
    else
      popd >/dev/null
      return 1
    fi
  fi
  popd >/dev/null
}

echo "Installing npm dependencies in repo root..."
doinstall "$REPO_ROOT" "repo root" "false"

for sub in react-app e2e; do
  if [[ -f "$REPO_ROOT/$sub/package.json" ]]; then
    echo "Installing npm dependencies in $sub..."
    allow_legacy="false"
    if [[ "$sub" == "react-app" ]]; then
      allow_legacy="true"
    fi
    doinstall "$REPO_ROOT/$sub" "$sub" "$allow_legacy"
  fi
 done

echo "Node dependencies installed successfully."
