#!/bin/sh
set -eu

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${WORKSPACE_DB_USER:?WORKSPACE_DB_USER is required}"
: "${WORKSPACE_DB_PASSWORD:?WORKSPACE_DB_PASSWORD is required}"
: "${WORKSPACE_WORKER_DB_USER:?WORKSPACE_WORKER_DB_USER is required}"
: "${WORKSPACE_WORKER_DB_PASSWORD:?WORKSPACE_WORKER_DB_PASSWORD is required}"

case "$WORKSPACE_DB_USER" in
  *[!A-Za-z0-9_]*|'') echo "workspace_role_invalid" >&2; exit 1 ;;
esac
if [ "${#WORKSPACE_DB_PASSWORD}" -lt 24 ]; then
  echo "workspace_password_invalid" >&2
  exit 1
fi
case "$WORKSPACE_WORKER_DB_USER" in
  *[!A-Za-z0-9_]*|'') echo "workspace_worker_role_invalid" >&2; exit 1 ;;
esac
if [ "$WORKSPACE_WORKER_DB_USER" = "$WORKSPACE_DB_USER" ] || [ "${#WORKSPACE_WORKER_DB_PASSWORD}" -lt 24 ]; then
  echo "workspace_worker_credentials_invalid" >&2
  exit 1
fi

export PGPASSWORD="$POSTGRES_PASSWORD"
psql --host="${DB_HOST:-postgres}" --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" \
  --set=ON_ERROR_STOP=1 --set=runtime_user="$WORKSPACE_DB_USER" \
  --set=runtime_password="$WORKSPACE_DB_PASSWORD" \
  --set=worker_user="$WORKSPACE_WORKER_DB_USER" \
  --set=worker_password="$WORKSPACE_WORKER_DB_PASSWORD" <<'SQL'
SELECT format(
  'CREATE ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS',
  :'runtime_user', :'runtime_password'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'runtime_user')\gexec
SELECT format(
  'ALTER ROLE %I WITH LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS',
  :'runtime_user', :'runtime_password'
)\gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'runtime_user')\gexec
SELECT format(
  'CREATE ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS',
  :'worker_user', :'worker_password'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'worker_user')\gexec
SELECT format(
  'ALTER ROLE %I WITH LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS',
  :'worker_user', :'worker_password'
)\gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'worker_user')\gexec
SQL
unset PGPASSWORD
