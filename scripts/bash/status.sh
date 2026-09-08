#!/bin/bash
# Check status of Docker services

set -e

COMPOSE_FILE="development.docker.yml"
ENV_FILE=".env"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

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
        --help|-h)
            echo "Usage: ./status.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -c, --compose-file FILE  Use a specific compose file"
            echo "  -e, --env-file FILE      Use a specific env file"
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

if [ ! -f "$COMPOSE_FILE" ]; then
    echo "âŒ Error: compose file not found: $COMPOSE_FILE"
    exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
    echo "âŒ Error: env file not found: $ENV_FILE"
    exit 1
fi

# Derive values from .env when present
get_env_var() {
    local key="$1"
    local line
    line=$(grep -E "^${key}=" "$ENV_FILE" 2>/dev/null | head -n1 || true)
    if [ -n "$line" ]; then
        line=$(echo "$line" | sed 's/ *#.*//' | sed 's/[[:space:]]*$//')
        echo "$line" | cut -d'=' -f2-
    fi
}

COMPOSE_PROJECT_NAME="$(get_env_var COMPOSE_PROJECT_NAME)"
if [ -z "$COMPOSE_PROJECT_NAME" ]; then COMPOSE_PROJECT_NAME="$(get_env_var PROJECT_NAME)"; fi
if [ -z "$COMPOSE_PROJECT_NAME" ]; then COMPOSE_PROJECT_NAME="app"; fi

echo "ðŸ“Š Docker Environment Status"
echo "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”"
echo ""

# Check if docker-compose is running
if docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps -q | grep -q .; then
    echo "ðŸ³ Container Status:"
    docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps

    echo ""
    echo "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”"
    echo "ðŸ¥ Health Check Status:"
    echo ""

    # Check health of each service
    for service in traefik react-app api django postgres nginx nginx-static pgadmin redis celery-worker celery-content-worker celery-email-worker celery-beat flower; do
        container_name="${COMPOSE_PROJECT_NAME}_${service}"
        if docker ps --filter "name=${container_name}" --format "{{.Names}}" | grep -q "${container_name}"; then
            health=$(docker inspect --format='{{.State.Health.Status}}' "${container_name}" 2>/dev/null || echo "no healthcheck")
            status=$(docker inspect --format='{{.State.Status}}' "${container_name}")

            if [ "$health" = "healthy" ]; then
                echo "  âœ… ${service}: ${status} (healthy)"
            elif [ "$health" = "unhealthy" ]; then
                echo "  âŒ ${service}: ${status} (unhealthy)"
            elif [ "$health" = "starting" ]; then
                echo "  ðŸ”„ ${service}: ${status} (starting)"
            else
                if [ "$status" = "running" ]; then
                    echo "  ðŸŸ¢ ${service}: ${status}"
                else
                    echo "  ðŸ”´ ${service}: ${status}"
                fi
            fi
        else
            echo "  âš« ${service}: not running"
        fi
    done

    echo ""
    echo "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”"
    echo "ðŸ“Š Resource Usage:"
    echo ""
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" $(docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps -q)

    echo ""
    echo "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”"
    echo "ðŸŒ Service URLs (via Traefik):"
    domain=${WEBSITE_DOMAIN:-$(get_env_var WEBSITE_DOMAIN)}
    if [ -z "$domain" ]; then domain=localhost; fi
    echo "  - Frontend:          https://${domain}/"
    echo "  - API health:        https://${domain}/api/health"
    echo "  - Static:            https://${domain}/static/"
    echo "  - Traefik Dashboard: https://${TRAEFIK_DNS_LABEL:-traefik}.${domain}/ (guarded)"
    echo "  - Django Admin:      https://${DJANGO_ADMIN_DNS_LABEL:-admin}.${domain}/admin (guarded)"
else
    echo "âš ï¸  No containers are running"
    echo ""
    echo "ðŸ’¡ Start services: ./scripts/bash/start.sh"
fi
