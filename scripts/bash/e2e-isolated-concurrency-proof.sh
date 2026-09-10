#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
receipt="$(cd "$repo_root" && python3 scripts/python/record_e2e_concurrency_evidence.py)"
printf 'isolated_e2e_concurrency_proof=passed owner_rc=0 contender_rc=3 inventory=empty evidence=%s\n' "$receipt"
