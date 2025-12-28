#!/usr/bin/env bash
set -euo pipefail

python -c "import api.main" >/dev/null

HOST="${API_HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
WORKERS="${API_WORKERS:-2}"
TIMEOUT="${API_TIMEOUT:-60}"
GRACEFUL_TIMEOUT="${API_GRACEFUL_TIMEOUT:-30}"

exec gunicorn api.main:app \
  -k uvicorn.workers.UvicornWorker \
  --bind "${HOST}:${PORT}" \
  --workers "${WORKERS}" \
  --timeout "${TIMEOUT}" \
  --graceful-timeout "${GRACEFUL_TIMEOUT}"
