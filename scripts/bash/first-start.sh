#!/usr/bin/env bash
set -euo pipefail

FORCE_VENV=false
SKIP_SETUP=false

usage() {
  cat <<'EOF'
Usage: ./scripts/bash/first-start.sh [options]

Options:
  --force-venv   Recreate the .venv even if one already exists
  --skip-setup   Skip running scripts/bash/setup.sh
  --help, -h     Show this help message

Tip: run ./scripts/bash/setup.sh --help for setup options.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force-venv)
      FORCE_VENV=true
      shift
      ;;
    --skip-setup)
      SKIP_SETUP=true
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

BOOTSTRAP_SCRIPT="$SCRIPT_DIR/bootstrap-venv.sh"
PYTHON_DEPS_SCRIPT="$SCRIPT_DIR/install-python-deps.sh"
NODE_DEPS_SCRIPT="$SCRIPT_DIR/install-node-deps.sh"
SETUP_SCRIPT="$SCRIPT_DIR/setup.sh"

cd "$REPO_ROOT"

echo "==> Starting first-start orchestration"

bootstrap_args=()
if $FORCE_VENV; then
  bootstrap_args+=("--force")
fi

echo "==> Bootstrapping virtual environment"
"$BOOTSTRAP_SCRIPT" "${bootstrap_args[@]}"

activate_script="$REPO_ROOT/.venv/bin/activate"
if [[ ! -f "$activate_script" ]]; then
  echo "Activate script not found. Ensure the venv was created successfully." >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$activate_script"
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  echo "Virtual environment activation failed. VIRTUAL_ENV is not set." >&2
  exit 1
fi

expected_venv="$REPO_ROOT/.venv"
if [[ "${VIRTUAL_ENV}" != "$expected_venv" ]]; then
  echo "Unexpected virtual environment active: ${VIRTUAL_ENV} (expected ${expected_venv})." >&2
  exit 1
fi

echo "==> Installing Python dependencies"
"$PYTHON_DEPS_SCRIPT"

echo "==> Installing Node dependencies"
"$NODE_DEPS_SCRIPT"

if ! $SKIP_SETUP; then
  echo "==> Running guided setup (.env generation)"
  "$SETUP_SCRIPT"
else
  echo "==> Skipping guided setup (--skip-setup)"
fi

echo "==> First-start completed successfully"
