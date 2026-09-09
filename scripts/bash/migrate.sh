#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="development.docker.yml"
ENV_FILE=".env"

usage() {
  cat <<'EOF'
Usage: ./scripts/bash/migrate.sh [options]

Options:
  -c, --compose-file FILE  Use a specific compose file
  -e, --env-file FILE      Use a specific env file
  -h, --help               Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --compose-file|-c)
      COMPOSE_FILE="$2"
      shift 2
      ;;
    --env-file|-e)
      ENV_FILE="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

COMPOSE_PATH="$PROJECT_ROOT/$COMPOSE_FILE"
ENV_PATH="$PROJECT_ROOT/$ENV_FILE"

if [[ ! -f "$COMPOSE_PATH" ]]; then
  echo "Missing $COMPOSE_PATH. Run this script from the repo root." >&2
  exit 1
fi
if [[ ! -f "$ENV_PATH" ]]; then
  echo "Missing $ENV_PATH. Run this script from the repo root." >&2
  exit 1
fi

cd "$PROJECT_ROOT"

compose=(docker compose --env-file "$ENV_PATH" -f "$COMPOSE_PATH")
"${compose[@]}" run --rm workspace-db-role
"${compose[@]}" run --rm --no-deps api-migrate python -m api.scripts.migrate
"${compose[@]}" run --rm --no-deps django python manage.py migrate --noinput
