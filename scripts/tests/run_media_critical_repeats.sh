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
    tests/test_media_library_processor.py \
    tests/test_media_library_storage.py \
    tests/test_media_library_repository.py::test_transition_exact_replay_precedes_stale_version_rejection \
    tests/test_media_library_repository.py::test_transition_changed_replay_is_an_idempotency_conflict \
    tests/test_media_inspector_isolation.py::test_service_failure_marker_preserves_bounded_classification \
    tests/test_content_workspace_worker.py::test_media_scan_attempt_token_is_single_use_and_backoff_bound \
    tests/test_content_workspace_worker.py::test_media_scan_worker_results_complete_running_lease \
    tests/test_content_workspace_worker.py::test_unexpected_media_scan_failure_is_recovered_immediately \
    tests/test_content_workspace_tasks.py::test_workspace_media_scan_duplicate_token_is_noop \
    tests/test_content_workspace_tasks.py::test_workspace_media_scan_unexpected_exception_is_durably_recovered \
    >/tmp/base2-media-critical-repeat.log 2>&1 || {
      cat /tmp/base2-media-critical-repeat.log
      exit 1
    }
  if (( iteration % 10 == 0 || iteration == iterations )); then
    printf 'media critical repeat %s/%s passed\n' "$iteration" "$iterations"
  fi
done
