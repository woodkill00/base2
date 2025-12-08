#!/bin/bash
# Edit/Maintain CLI wrapper for Digital Ocean automation
# Usage: ./edit.sh [--dry-run]
# Requires: .env with Digital Ocean variables

set -e

# Activate Python venv if available
if [ -d "../../.venv" ]; then
    source ../../.venv/bin/activate
fi

if [ -z "$DO_API_TOKEN" ]; then
  echo "ERROR: DO_API_TOKEN is not set in environment." >&2
  exit 1
fi

python ../edit.py "$@"
