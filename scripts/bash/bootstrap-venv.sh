#!/usr/bin/env bash
set -euo pipefail

FORCE=false

usage() {
  cat <<'EOF'
Usage: ./scripts/bash/bootstrap-venv.sh [--force]

Options:
  --force, -f   Recreate the .venv even if it exists
  --help, -h    Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force|-f)
      FORCE=true
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

PYTHON_CMD=""
if command -v python >/dev/null 2>&1; then
  PYTHON_CMD="python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="python3"
else
  echo "python executable not found in PATH. Install Python 3.12+ and retry." >&2
  exit 1
fi

VENV_DIR="$REPO_ROOT/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"

venv_is_usable() {
  [[ -x "$VENV_PYTHON" ]] && "$VENV_PYTHON" -m pip --version >/dev/null 2>&1
}

create_venv() {
  local clear_arg=()
  if [[ -d "$VENV_DIR" ]]; then
    clear_arg=(--clear)
  fi

  if "$PYTHON_CMD" -m venv "${clear_arg[@]}" "$VENV_DIR"; then
    return 0
  fi

  echo "Standard-library venv is unavailable; checking user-local virtualenv fallback..." >&2
  if "$PYTHON_CMD" -m virtualenv --version >/dev/null 2>&1; then
    "$PYTHON_CMD" -m virtualenv --clear "$VENV_DIR"
    return 0
  fi

  cat >&2 <<'EOF'
Unable to create .venv. Install Ubuntu's python3.12-venv package, or install
virtualenv for the current WSL user, then retry. A partial environment is not
accepted as ready.
EOF
  return 1
}

if ! $FORCE && venv_is_usable; then
  echo "Existing Python virtual environment detected."
else
  echo "Creating Python virtual environment (.venv)..."
  create_venv
fi

if ! venv_is_usable; then
  echo "Virtual environment validation failed: $VENV_PYTHON cannot run pip." >&2
  exit 1
fi

echo "Virtual environment ready at: $VENV_PYTHON"
