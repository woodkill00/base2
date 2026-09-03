#!/bin/bash
# Start all Docker services

set -e

COMPOSE_FILE="development.docker.yml"
ENV_FILE=".env"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_DIR"

stage() {
    echo "[STAGE] $1"
}

# Platform compatibility note
stage "start.sh initialization"
echo "â„¹ï¸  This script requires Bash and is tested on Mac, Linux, and Windows (WSL/Git Bash)."
echo "   For Windows, use WSL or Git Bash for best results."

# Docker Compose version check
stage "docker compose version check"
REQUIRED_COMPOSE_VERSION="2.0.0"
compose_cmd=(docker-compose)
if command -v docker >/dev/null 2>&1 && docker compose version --short >/dev/null 2>&1; then
    compose_cmd=(docker compose)
    COMPOSE_VERSION=$(docker compose version --short 2>/dev/null || echo "")
else
    COMPOSE_VERSION=$(docker-compose version --short 2>/dev/null || echo "")
fi
if [ "${START_USE_DOCKER_COMPOSE_V2:-}" = "true" ] && command -v docker >/dev/null 2>&1 && docker compose version --short >/dev/null 2>&1; then
    compose_cmd=(docker compose)
    COMPOSE_VERSION=$(docker compose version --short 2>/dev/null || echo "")
fi
if [ -z "$COMPOSE_VERSION" ]; then
    echo "âš ï¸  Docker Compose not found. Please install Docker Compose v$REQUIRED_COMPOSE_VERSION or newer."
    exit 1
fi
if [ "$(printf '%s\n' "$REQUIRED_COMPOSE_VERSION" "$COMPOSE_VERSION" | sort -V | head -n1)" != "$REQUIRED_COMPOSE_VERSION" ]; then
    echo "âš ï¸  Docker Compose version $COMPOSE_VERSION detected. v$REQUIRED_COMPOSE_VERSION or newer is required."
    exit 1
fi

echo "ðŸš€ Starting Docker Environment..."
echo "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”"

REQUIRED_VARS=(WEBSITE_DOMAIN NETWORK_NAME TRAEFIK_PORT FASTAPI_PORT DJANGO_PORT POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB WORKSPACE_DB_USER WORKSPACE_DB_PASSWORD WORKSPACE_WORKER_DB_USER WORKSPACE_WORKER_DB_PASSWORD)

# Parse command line arguments
stage "parse CLI args"
BUILD=false
DETACHED=true
SELF_TEST=false
FOLLOW_LOGS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --compose-file|-c)
            COMPOSE_FILE="$2"
            shift 2
            ;;
        --env-file|-e)
            ENV_FILE="$2"
            shift 2
            ;;
        --build|-b)
            BUILD=true
            shift
            ;;
        --foreground|-f)
            DETACHED=false
            shift
            ;;
        --self-test)
            SELF_TEST=true
            shift
            ;;
        --follow-logs)
            FOLLOW_LOGS=true
            shift
            ;;
        --help|-h)
            echo "Usage: ./scripts/bash/start.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -c, --compose-file FILE  Use a specific compose file"
            echo "  -e, --env-file FILE      Use a specific env file"
            echo "  -b, --build       Rebuild images before starting"
            echo "  -f, --foreground  Run in foreground (don't detach)"
            echo "  --self-test       Run script self-test and exit"
            echo "  --follow-logs     After up -d, follow service logs briefly"
            echo "  -h, --help        Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Validate the selected environment only after command-line overrides are known.
stage "env file validation"
if [ ! -f "$ENV_FILE" ]; then
    echo "Error: selected environment file is missing: $ENV_FILE"
    echo "Run: node scripts/setup.js --render-env"
    exit 1
fi
for VAR in "${REQUIRED_VARS[@]}"; do
    if ! grep -q "^$VAR=" "$ENV_FILE"; then
        echo "âŒ Error: Required environment variable $VAR is missing in $ENV_FILE."
        exit 1
    fi
done

# Synchronize configuration with .env before starting
stage "sync configuration"
echo "ðŸ”„ Synchronizing configuration..."
if [ -f "$SCRIPT_DIR/sync-env.sh" ]; then
    "$SCRIPT_DIR/sync-env.sh" --compose-file "$COMPOSE_FILE" --env-file "$ENV_FILE"
    echo ""
fi

# Optional compose tuning for constrained environments
if [ -n "${START_COMPOSE_PARALLEL_LIMIT:-}" ]; then
    export COMPOSE_PARALLEL_LIMIT="$START_COMPOSE_PARALLEL_LIMIT"
fi
if [ -n "${START_COMPOSE_HTTP_TIMEOUT:-}" ]; then
    export COMPOSE_HTTP_TIMEOUT="$START_COMPOSE_HTTP_TIMEOUT"
fi

if [ ! -f "$COMPOSE_FILE" ]; then
    echo "âŒ Error: compose file not found: $COMPOSE_FILE"
    exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
    echo "âŒ Error: env file not found: $ENV_FILE"
    exit 1
fi

# Self-test function
if [ "$SELF_TEST" = true ]; then
    echo "ðŸ”Ž Running start.sh self-test..."
    # Check Docker
    if ! command -v docker &>/dev/null; then
        echo "âŒ Docker not found."
        exit 1
    fi
    # Check Docker Compose
    if ! command -v docker-compose &>/dev/null && ! (command -v docker >/dev/null 2>&1 && docker compose version --short >/dev/null 2>&1); then
        echo "âŒ Docker Compose not found."
        exit 1
    fi
    # Check .env
    if [ ! -f "$ENV_FILE" ]; then
        echo "âŒ .env file missing."
        exit 1
    fi
    # Check required variables
    for VAR in "${REQUIRED_VARS[@]}"; do
        if ! grep -q "^$VAR=" "$ENV_FILE"; then
            echo "âŒ Required variable $VAR missing in .env."
            exit 1
        fi
    done
    echo "âœ… Self-test passed."
    exit 0
fi

# Ensure Traefik ACME storage exists and is writable by the Traefik user.
stage "prepare traefik acme storage"
ACME_DIR="$PROJECT_DIR/letsencrypt"
"$PROJECT_DIR/scripts/bash/bootstrap-acme.sh" --directory "$ACME_DIR" --uid 1000 --gid 1000

# Build if requested
if [ "$BUILD" = true ]; then
    stage "docker compose build"
    echo "ðŸ”¨ Building services..."
    build_args=()
    compose_build_cmd=("${compose_cmd[@]}")
    if [ "${compose_cmd[0]}" = "docker" ] && [ -n "${START_BUILD_PROGRESS:-}" ]; then
        compose_build_cmd=(docker compose --progress "$START_BUILD_PROGRESS")
    fi
    if [ -n "${START_BUILD_TIMEOUT_SECONDS:-}" ] && command -v timeout >/dev/null 2>&1; then
        timeout "$START_BUILD_TIMEOUT_SECONDS" "${compose_build_cmd[@]}" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" build "${build_args[@]}"
    else
        "${compose_build_cmd[@]}" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" build "${build_args[@]}"
    fi
fi

# Start services
if [ "$DETACHED" = true ]; then
    stage "docker compose up (detached)"
    echo "ðŸ³ Starting services in detached mode..."
    "${compose_cmd[@]}" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d

    echo ""
    echo "âœ… Services started successfully!"
    echo ""
    echo "ðŸ“Š Service Status:"
    "${compose_cmd[@]}" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps

    echo ""
    echo "ðŸŒ Access services at:"
    # Load env for dynamic endpoints
    if [ -f "$ENV_FILE" ]; then
        # shellcheck disable=SC2046
        export $(grep -E '^(WEBSITE_DOMAIN)=' "$ENV_FILE" | xargs)
    fi
    WEBSITE_DOMAIN_PRINT=${WEBSITE_DOMAIN:-localhost}
    echo "  - Frontend (HTTP via Traefik):  http://localhost"
    echo "  - Frontend (HTTPS via Traefik): https://${WEBSITE_DOMAIN_PRINT} (staging cert)"
    echo "  - API (via Traefik):            https://${WEBSITE_DOMAIN_PRINT}/api"
    echo "  - PostgreSQL:                   internal-only"
    echo "  - pgAdmin:                      internal-only"
    echo "  - Traefik Dashboard:            disabled insecure access"
    echo ""
    echo "ðŸ’¡ View logs: ./scripts/bash/logs.sh"

    # Optionally follow logs for a short window (useful for orchestrated deploys)
    if [ "$FOLLOW_LOGS" = true ] || [ "${START_FOLLOW_LOGS:-}" = "true" ]; then
        DURATION=${POST_DEPLOY_LOGS_FOLLOW_SECONDS:-60}
        stage "follow service logs"
        echo "\nðŸ”Ž Following logs for ${DURATION}s (traefik, api, django, nginx, pgadmin)..."
        # Use timeout to avoid hanging forever; fallback if timeout is not available
        if command -v timeout >/dev/null 2>&1; then
            timeout "$DURATION" "${compose_cmd[@]}" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" logs -f --tail=100 traefik api django nginx pgadmin || true
        else
            # Portable fallback: run in background and kill after duration
            ( "${compose_cmd[@]}" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" logs -f --tail=100 traefik api django nginx pgadmin & LOG_PID=$!; \
              sleep "$DURATION"; \
              kill "$LOG_PID" 2>/dev/null || true )
        fi
    fi
else
    stage "docker compose up (foreground)"
    echo "ðŸ³ Starting services in foreground mode..."
    "${compose_cmd[@]}" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up
fi
