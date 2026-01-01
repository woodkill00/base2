#!/usr/bin/env bash
set -euo pipefail

# Generate TypeScript types from OpenAPI contract for frontend consumption.
ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")"/.. && pwd)
CONTRACT="$ROOT_DIR/specs/001-django-fastapi-react/contracts/openapi.yaml"
OUT_DIR="$ROOT_DIR/react-app/src/services/api"
mkdir -p "$OUT_DIR"

if ! command -v npx >/dev/null 2>&1; then
  echo "npx is required (Node.js)" >&2
  exit 1
fi

npx openapi-typescript "$CONTRACT" -o "$OUT_DIR/types.d.ts"
echo "Generated: $OUT_DIR/types.d.ts"