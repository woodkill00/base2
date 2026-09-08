#!/bin/sh
set -eu

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${WORKSPACE_DB_USER:?WORKSPACE_DB_USER is required}"
: "${WORKSPACE_DB_PASSWORD:?WORKSPACE_DB_PASSWORD is required}"
: "${WORKSPACE_WORKER_DB_USER:?WORKSPACE_WORKER_DB_USER is required}"
: "${WORKSPACE_WORKER_DB_PASSWORD:?WORKSPACE_WORKER_DB_PASSWORD is required}"
: "${RUNTIME_WORKER_DB_USER:?RUNTIME_WORKER_DB_USER is required}"
: "${RUNTIME_WORKER_DB_PASSWORD:?RUNTIME_WORKER_DB_PASSWORD is required}"
: "${API_RUNTIME_DB_USER:?API_RUNTIME_DB_USER is required}"
: "${API_RUNTIME_DB_PASSWORD:?API_RUNTIME_DB_PASSWORD is required}"
: "${DATA_RIGHTS_WORKER_DB_USER:?DATA_RIGHTS_WORKER_DB_USER is required}"
: "${DATA_RIGHTS_WORKER_DB_PASSWORD:?DATA_RIGHTS_WORKER_DB_PASSWORD is required}"
: "${EMAIL_WORKER_DB_USER:?EMAIL_WORKER_DB_USER is required}"
: "${EMAIL_WORKER_DB_PASSWORD:?EMAIL_WORKER_DB_PASSWORD is required}"

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
case "$RUNTIME_WORKER_DB_USER" in
  *[!A-Za-z0-9_]*|'') echo "runtime_worker_role_invalid" >&2; exit 1 ;;
esac
if [ "$RUNTIME_WORKER_DB_USER" = "$WORKSPACE_DB_USER" ] || \
   [ "$RUNTIME_WORKER_DB_USER" = "$WORKSPACE_WORKER_DB_USER" ] || \
   [ "${#RUNTIME_WORKER_DB_PASSWORD}" -lt 24 ]; then
  echo "runtime_worker_credentials_invalid" >&2
  exit 1
fi
case "$API_RUNTIME_DB_USER" in
  *[!A-Za-z0-9_]*|'') echo "api_runtime_role_invalid" >&2; exit 1 ;;
esac
if [ "$API_RUNTIME_DB_USER" = "$POSTGRES_USER" ] || \
   [ "$API_RUNTIME_DB_USER" = "$WORKSPACE_DB_USER" ] || \
   [ "$API_RUNTIME_DB_USER" = "$WORKSPACE_WORKER_DB_USER" ] || \
   [ "$API_RUNTIME_DB_USER" = "$RUNTIME_WORKER_DB_USER" ] || \
   [ "${#API_RUNTIME_DB_PASSWORD}" -lt 24 ]; then
  echo "api_runtime_credentials_invalid" >&2
  exit 1
fi
case "$EMAIL_WORKER_DB_USER" in
  *[!A-Za-z0-9_]*|'') echo "email_worker_role_invalid" >&2; exit 1 ;;
esac
if [ "$EMAIL_WORKER_DB_USER" = "$WORKSPACE_DB_USER" ] || \
   [ "$EMAIL_WORKER_DB_USER" = "$WORKSPACE_WORKER_DB_USER" ] || \
   [ "$EMAIL_WORKER_DB_USER" = "$RUNTIME_WORKER_DB_USER" ] || \
   [ "${#EMAIL_WORKER_DB_PASSWORD}" -lt 24 ]; then
  echo "email_worker_credentials_invalid" >&2
  exit 1
fi
case "$DATA_RIGHTS_WORKER_DB_USER" in
  *[!A-Za-z0-9_]*|'') echo "data_rights_worker_role_invalid" >&2; exit 1 ;;
esac
if [ "$DATA_RIGHTS_WORKER_DB_USER" = "$WORKSPACE_DB_USER" ] || \
   [ "$DATA_RIGHTS_WORKER_DB_USER" = "$WORKSPACE_WORKER_DB_USER" ] || \
   [ "$DATA_RIGHTS_WORKER_DB_USER" = "$RUNTIME_WORKER_DB_USER" ] || \
   [ "$DATA_RIGHTS_WORKER_DB_USER" = "$API_RUNTIME_DB_USER" ] || \
   [ "$DATA_RIGHTS_WORKER_DB_USER" = "$EMAIL_WORKER_DB_USER" ] || \
   [ "${#DATA_RIGHTS_WORKER_DB_PASSWORD}" -lt 24 ]; then
  echo "data_rights_worker_credentials_invalid" >&2
  exit 1
fi

export PGPASSWORD="$POSTGRES_PASSWORD"
psql --host="${DB_HOST:-postgres}" --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" \
  --set=ON_ERROR_STOP=1 --set=runtime_user="$WORKSPACE_DB_USER" \
  --set=runtime_password="$WORKSPACE_DB_PASSWORD" \
  --set=worker_user="$WORKSPACE_WORKER_DB_USER" \
  --set=worker_password="$WORKSPACE_WORKER_DB_PASSWORD" \
  --set=runtime_worker_user="$RUNTIME_WORKER_DB_USER" \
  --set=runtime_worker_password="$RUNTIME_WORKER_DB_PASSWORD" \
  --set=api_runtime_user="$API_RUNTIME_DB_USER" \
  --set=api_runtime_password="$API_RUNTIME_DB_PASSWORD" \
  --set=data_rights_worker_user="$DATA_RIGHTS_WORKER_DB_USER" \
  --set=data_rights_worker_password="$DATA_RIGHTS_WORKER_DB_PASSWORD" \
  --set=email_worker_user="$EMAIL_WORKER_DB_USER" \
  --set=email_worker_password="$EMAIL_WORKER_DB_PASSWORD" <<'SQL'
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
SELECT format(
  'CREATE ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS',
  :'runtime_worker_user', :'runtime_worker_password'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'runtime_worker_user')\gexec
SELECT format(
  'ALTER ROLE %I WITH LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS',
  :'runtime_worker_user', :'runtime_worker_password'
)\gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'runtime_worker_user')\gexec
SELECT format(
  'CREATE ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS',
  :'api_runtime_user', :'api_runtime_password'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'api_runtime_user')\gexec
SELECT format(
  'ALTER ROLE %I WITH LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS',
  :'api_runtime_user', :'api_runtime_password'
)\gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'api_runtime_user')\gexec
SELECT format(
  'CREATE ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS',
  :'data_rights_worker_user', :'data_rights_worker_password'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'data_rights_worker_user')\gexec
SELECT format(
  'ALTER ROLE %I WITH LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS',
  :'data_rights_worker_user', :'data_rights_worker_password'
)\gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'data_rights_worker_user')\gexec
SELECT format(
  'CREATE ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS',
  :'email_worker_user', :'email_worker_password'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'email_worker_user')\gexec
SELECT format(
  'ALTER ROLE %I WITH LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS',
  :'email_worker_user', :'email_worker_password'
)\gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'email_worker_user')\gexec
SQL
unset PGPASSWORD
