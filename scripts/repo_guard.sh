#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

max_bytes=$((5 * 1024 * 1024))

fail() {
  echo "[repo-guard] FAIL: $1" >&2
  exit 1
}

# 1) Forbidden tracked file names
if git ls-files --error-unmatch docker-compose >/dev/null 2>&1; then
  fail "Tracked forbidden file: docker-compose"
fi

# 2) Forbidden tracked extensions
if git ls-files | grep -E -i '\\.exe$' >/dev/null 2>&1; then
  fail "Tracked forbidden executable(s): *.exe"
fi

# 3) Large tracked blobs (>5MB)
while IFS= read -r -d '' f; do
  [ -f "$f" ] || continue
  size=$(stat -c %s "$f" 2>/dev/null || echo 0)
  if [ "$size" -gt "$max_bytes" ]; then
    fail "Tracked file too large (>5MB): $f (${size} bytes)"
  fi

done < <(git ls-files -z)

# 4) Binary files in repo root (common accidental commits)
while IFS= read -r f; do
  case "$f" in
    */*) continue ;;
  esac
  [ -f "$f" ] || continue

  file_out=$(file -b "$f" 2>/dev/null || true)
  if echo "$file_out" | grep -E -q 'ELF|PE32|Mach-O'; then
    fail "Binary file tracked at repo root: $f ($file_out)"
  fi

done < <(git ls-files)

echo "[repo-guard] OK"
