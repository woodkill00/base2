#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

if [[ "${VISUAL_BASELINE_UPDATE_APPROVAL:-}" != "reviewed-local-only" ]]; then
  printf '%s\n' 'Refusing baseline update: set VISUAL_BASELINE_UPDATE_APPROVAL=reviewed-local-only after reviewing the intended visual change.' >&2
  exit 64
fi

branch="$(git branch --show-current)"
if [[ "$branch" != 093-* ]]; then
  printf 'Refusing baseline update outside a Feature 093 branch: %s\n' "$branch" >&2
  exit 65
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
  printf '%s\n' 'Refusing baseline update from a dirty tracked worktree. Commit the reviewed UI change first.' >&2
  exit 66
fi

cd react-app
npm exec playwright test -- --config=playwright.visual.config.mjs --update-snapshots
printf '%s\n' 'Visual candidates updated locally. Review every PNG diff; this command does not commit, publish, or deploy.'
