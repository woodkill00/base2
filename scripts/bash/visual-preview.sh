#!/usr/bin/env bash
set -euo pipefail

port="${1:-}"
if [[ ! "$port" =~ ^[0-9]{4,5}$ ]] || ((port < 1024 || port > 65535)); then
  printf 'ERROR: visual preview port must be numeric and between 1024 and 65535\n' >&2
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
app_root="$repo_root/react-app"
build_root="$repo_root/.artifacts/visual-previews"
build_dir="$build_root/$port"
preview_pid=''

cleanup() {
  if [[ -n "$preview_pid" ]]; then
    kill "$preview_pid" >/dev/null 2>&1 || true
    wait "$preview_pid" >/dev/null 2>&1 || true
  fi
  rm -rf -- "$build_dir"
}
trap cleanup EXIT INT TERM

mkdir -p "$build_root"
rm -rf -- "$build_dir"
cd "$app_root"
VITE_SITE_PROFILE=base2-obsidian npm run build -- --outDir "$build_dir"
npm exec vite preview -- --outDir "$build_dir" --host 127.0.0.1 --port "$port" --strictPort &
preview_pid="$!"
wait "$preview_pid"
