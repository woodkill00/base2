#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"
if [[ "${WORKSPACE_VISUAL_BASELINE_UPDATE_APPROVAL:-}" != "reviewed-local-only" ]]; then
  printf '%s\n' 'Refusing workspace baseline update without reviewed-local-only approval.' >&2
  exit 64
fi
branch="$(git branch --show-current)"
if [[ "$branch" != *104-universal-content-data-workspace* ]]; then
  printf 'Refusing workspace baseline update outside Feature 104: %s\n' "$branch" >&2
  exit 65
fi
if ! git diff --quiet || ! git diff --cached --quiet; then
  printf '%s\n' 'Refusing workspace baseline update from a dirty tracked worktree.' >&2
  exit 66
fi
cd react-app
npm exec playwright test -- --config=playwright.workspace-release.config.mjs --update-snapshots
