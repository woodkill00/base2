#!/usr/bin/env bash
set -euo pipefail

script_dir="$(CDPATH='' cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(CDPATH='' cd "$script_dir/../.." && pwd)"
exec python3 "$repo_root/scripts/python/validate_feature_093.py" "$@"
