#!/usr/bin/env bash
set -euo pipefail

SKIP_PIP_UPGRADE=false
INSTALL_API=false
INSTALL_DJANGO=false
INSTALL_DO=false

usage() {
  cat <<'EOF'
Usage: ./scripts/bash/install-python-deps.sh [options]

Options:
  --skip-pip-upgrade   Skip pip upgrade step
  --api                Install API dependencies into .venv-api
  --django             Install Django dependencies into .venv-django
  --digital-ocean      Install orchestration dependencies into .venv
  --help, -h           Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-pip-upgrade)
      SKIP_PIP_UPGRADE=true
      shift
      ;;
    --api)
      INSTALL_API=true
      shift
      ;;
    --django)
      INSTALL_DJANGO=true
      shift
      ;;
    --digital-ocean)
      INSTALL_DO=true
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
HOST_PYTHON="$(command -v python3 || command -v python || true)"
if [[ -z "$HOST_PYTHON" ]]; then
  echo "Python executable not found in PATH. Install Python 3.12+ and retry." >&2
  exit 1
fi

echo "==> Python dependency installation starting"

required_version="3.12"
if [[ -f "$REPO_ROOT/.python-version" ]]; then
  required_version="$(head -n1 "$REPO_ROOT/.python-version" | tr -d '[:space:]')"
fi

normalize_version() {
  local version="$1"
  version="${version#v}"
  IFS='.' read -r major minor _rest <<<"$version"
  if [[ -n "$major" && -n "$minor" ]]; then
    echo "${major}.${minor}"
  else
    echo "$version"
  fi
}

expected_version="$(normalize_version "$required_version")"
if [[ -z "$expected_version" ]]; then
  echo "Unable to determine Python version." >&2
  exit 1
fi

targets=()
if $INSTALL_API || $INSTALL_DJANGO || $INSTALL_DO; then
  $INSTALL_API && targets+=(".venv-api:requirements-dev-api.txt")
  $INSTALL_DJANGO && targets+=(".venv-django:requirements-dev-django.txt")
  $INSTALL_DO && targets+=(".venv:digital_ocean/requirements.txt")
else
  targets+=(
    ".venv-api:requirements-dev-api.txt"
    ".venv-django:requirements-dev-django.txt"
    ".venv:digital_ocean/requirements.txt"
  )
fi

ensure_venv() {
  local venv_dir="$1"
  local venv_python="$venv_dir/bin/python"
  if [[ -x "$venv_python" ]] && "$venv_python" -m pip --version >/dev/null 2>&1; then
    return 0
  fi
  echo "Creating isolated environment ${venv_dir#$REPO_ROOT/}..."
  if ! "$HOST_PYTHON" -m venv --clear "$venv_dir"; then
    echo "Standard-library venv unavailable; trying user-local virtualenv..." >&2
    "$HOST_PYTHON" -m virtualenv --clear "$venv_dir"
  fi
  [[ -x "$venv_python" ]] && "$venv_python" -m pip --version >/dev/null 2>&1
}

for target in "${targets[@]}"; do
  venv_name="${target%%:*}"
  req="${target#*:}"
  venv_dir="$REPO_ROOT/$venv_name"
  venv_python="$venv_dir/bin/python"
  req_path="$REPO_ROOT/$req"
  if [[ ! -f "$req_path" ]]; then
    echo "Requirements file not found: $req" >&2
    exit 1
  fi
  if ! ensure_venv "$venv_dir"; then
    echo "Unable to create a usable $venv_name environment." >&2
    exit 1
  fi
  actual_version="$($venv_python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")"
  if [[ "$actual_version" != "$expected_version" ]]; then
    echo "$venv_name uses Python $actual_version but $expected_version is required." >&2
    exit 1
  fi
  if ! $SKIP_PIP_UPGRADE; then
    echo "Upgrading pip in $venv_name..."
    "$venv_python" -m pip install --upgrade pip
  fi
  echo "Installing $req into $venv_name..."
  if ! "$venv_python" -m pip install -r "$req_path"; then
    echo "Initial pip install failed for $venv_name; retrying once without cache..." >&2
    "$venv_python" -m pip install --no-cache-dir -r "$req_path"
  fi
  "$venv_python" -m pip check
done

echo "Python dependencies installed successfully."
