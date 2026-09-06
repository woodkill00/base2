#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
iterations="${1:-100}"

if ! [[ "$iterations" =~ ^[1-9][0-9]{0,2}$ ]] || (( iterations > 100 )); then
  printf '%s\n' 'media_repeat_count_invalid' >&2
  exit 2
fi

cd "$root/api"
for ((iteration = 1; iteration <= iterations; iteration += 1)); do
  ../.venv-api/bin/pytest -q -p no:cov -o addopts='' \
    tests/test_media_library_lifecycle.py \
    tests/test_media_library_operations.py \
    tests/test_media_library_governance.py \
    tests/test_media_library_worker.py \
    tests/test_media_library_policy.py \
    >/tmp/base2-media-critical-repeat.log 2>&1 || {
      cat /tmp/base2-media-critical-repeat.log
      exit 1
    }
  if (( iteration % 10 == 0 || iteration == iterations )); then
    printf 'media critical repeat %s/%s passed\n' "$iteration" "$iterations"
  fi
done
