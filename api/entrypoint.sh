#!/usr/bin/env bash
set -euo pipefail

python -c "import api.main" >/dev/null

HOST="${API_HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
WORKERS="${API_WORKERS:-2}"
TIMEOUT="${API_TIMEOUT:-60}"
GRACEFUL_TIMEOUT="${API_GRACEFUL_TIMEOUT:-30}"

# Whole-object delivery holds up to three 25 MiB representations per worker.
# Keep this coupled to api.security.upload_capacity.MAX_API_WORKERS so operator
# configuration cannot silently invalidate the 150 MiB delivery-memory bound.
if ! [[ "${WORKERS}" =~ ^[0-9]+$ ]] || (( WORKERS < 1 || WORKERS > 2 )); then
  printf '%s\n' 'API_WORKERS must be an integer between 1 and 2' >&2
  exit 64
fi

exec gunicorn api.main:app \
  -k uvicorn.workers.UvicornWorker \
  --bind "${HOST}:${PORT}" \
  --workers "${WORKERS}" \
  --timeout "${TIMEOUT}" \
  --graceful-timeout "${GRACEFUL_TIMEOUT}"
