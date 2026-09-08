#!/usr/bin/env bash
set -euo pipefail

root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
action="${1:-}"
[[ $# -gt 0 ]] && shift
case "$action" in
  setup) exec "$root/scripts/bash/setup.sh" "$@" ;;
  generate) exec "$root/scripts/create-base2-site.sh" "$@" ;;
  migrate) exec "$root/scripts/bash/migrate.sh" "$@" ;;
  test) exec "$root/scripts/bash/complete-gate.sh" "$@" ;;
  preview) exec "$root/scripts/bash/start.sh" "$@" ;;
  release) exec "$root/scripts/bash/release.sh" promote "$@" ;;
  rollback) exec "$root/scripts/bash/release.sh" rollback "$@" ;;
  recover) exec "$root/scripts/bash/content-workspace-recovery.sh" "$@" ;;
  *) printf 'usage: %s setup|generate|migrate|test|preview|release|recover|rollback [arguments]\n' "$0" >&2; exit 64 ;;
esac
