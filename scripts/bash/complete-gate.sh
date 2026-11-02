#!/usr/bin/env bash
set -euo pipefail

script_dir="$(CDPATH='' cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(CDPATH='' cd "$script_dir/../.." && pwd)"
export BASE2_GATE_SHELL=bash
exec "$repo_root/.venv/bin/python" "$repo_root/scripts/python/run_complete_gate.py"
