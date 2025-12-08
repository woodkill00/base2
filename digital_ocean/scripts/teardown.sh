#!/bin/bash
# Teardown CLI wrapper for Digital Ocean automation
# Usage: ./teardown.sh [--dry-run]
# Requires: .env with Digital Ocean variables

set -e

if [ -z "$DO_API_TOKEN" ]; then
  echo "ERROR: DO_API_TOKEN is not set in environment." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/../.."
cd "$PROJECT_ROOT/digital_ocean"

if [ "$1" == "--dry-run" ]; then
    python teardown.py --dry-run
else
    python teardown.py
fi
