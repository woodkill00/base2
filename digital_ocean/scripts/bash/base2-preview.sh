#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"

if [[ -z "${WSL_DISTRO_NAME:-}" ]] && ! grep -qi microsoft /proc/version 2>/dev/null; then
  printf '%s\n' '{"schemaVersion":1,"ok":false,"code":"RUNTIME_NOT_WSL","secretValuesEmitted":0}'
  exit 2
fi

case "$repo_root" in
  /home/*) ;;
  *)
    printf '%s\n' '{"schemaVersion":1,"ok":false,"code":"RUNTIME_NON_WSL_REPOSITORY","secretValuesEmitted":0}'
    exit 2
    ;;
esac

python_bin="${BASE2_PREVIEW_PYTHON:-$repo_root/.venv/bin/python}"
python_bin="$(readlink -f "$python_bin")"
case "$python_bin" in
  /mnt/*|*.exe|*.EXE)
    printf '%s\n' '{"schemaVersion":1,"ok":false,"code":"RUNTIME_WINDOWS_TOOL","secretValuesEmitted":0}'
    exit 2
    ;;
esac

if [[ ! -x "$python_bin" ]]; then
  printf '%s\n' '{"schemaVersion":1,"ok":false,"code":"RUNTIME_TOOL_MISSING","secretValuesEmitted":0}'
  exit 2
fi

cd "$repo_root"
export PYTHONPATH="$repo_root${PYTHONPATH:+:$PYTHONPATH}"
exec "$python_bin" -m digital_ocean.scripts.python.preview_control "$@"
