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
  --api                Install requirements-dev-api.txt
  --django             Install requirements-dev-django.txt
  --digital-ocean      Install digital_ocean/requirements.txt
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
VENV_PYTHON="$REPO_ROOT/.venv/bin/python"

if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "Virtual environment .venv not found. Run ./scripts/bash/bootstrap-venv.sh first." >&2
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

actual_version="$($VENV_PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")"
expected_version="$(normalize_version "$required_version")"

if [[ -z "$actual_version" || -z "$expected_version" ]]; then
  echo "Unable to determine Python version." >&2
  exit 1
fi

if [[ "$actual_version" != "$expected_version" ]]; then
  echo "Virtual environment uses Python $actual_version but $expected_version is required." >&2
  exit 1
fi

if ! $SKIP_PIP_UPGRADE; then
  echo "Upgrading pip..."
  "$VENV_PYTHON" -m pip install --upgrade pip
fi

requirements=()
if $INSTALL_API || $INSTALL_DJANGO || $INSTALL_DO; then
  $INSTALL_API && requirements+=("requirements-dev-api.txt")
  $INSTALL_DJANGO && requirements+=("requirements-dev-django.txt")
  $INSTALL_DO && requirements+=("digital_ocean/requirements.txt")
else
  requirements+=("digital_ocean/requirements.txt")
fi

for req in "${requirements[@]}"; do
  req_path="$REPO_ROOT/$req"
  if [[ -f "$req_path" ]]; then
    echo "Installing Python dependencies from $req..."
    "$VENV_PYTHON" -m pip install -r "$req_path"
  else
    echo "Requirements file not found: $req" >&2
    exit 1
  fi
 done

echo "Python dependencies installed successfully."
