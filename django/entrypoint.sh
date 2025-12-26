#!/usr/bin/env bash
set -euo pipefail

wait_for_db() {
  local attempts=${DJANGO_DB_WAIT_ATTEMPTS:-30}
  local sleep_seconds=${DJANGO_DB_WAIT_SLEEP_SECONDS:-2}

  for ((i=1; i<=attempts; i++)); do
    if python manage.py check --database default >/dev/null 2>&1; then
      return 0
    fi
    echo "[entrypoint] waiting for database (${i}/${attempts})..." >&2
    sleep "$sleep_seconds"
  done

  echo "[entrypoint] database not ready after ${attempts} attempts" >&2
  return 1
}

wait_for_db

python manage.py migrate --noinput

python manage.py collectstatic --noinput

python -m project.create_superuser || true

exec gunicorn project.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${DJANGO_WORKERS:-2}" \
  --timeout "${DJANGO_TIMEOUT:-60}" \
  --access-logfile - \
  --error-logfile -
