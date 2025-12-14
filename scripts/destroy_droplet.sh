#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

if ! command -v python &>/dev/null && ! command -v python3 &>/dev/null; then
  echo "❌ Python is required to run teardown."
  exit 1
fi

PY=python
command -v python >/dev/null 2>&1 || PY=python3

echo "🧹 Destroying droplet and cleaning DNS (A/AAAA for @, www, traefik)..."
"$PY" digital_ocean/orchestrate_teardown.py --clean-dns
