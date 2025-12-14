#!/bin/bash
# Start all Docker services

set -e

COMPOSE_FILE="local.docker.yml"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Synchronize configuration with .env before starting
echo "🔄 Synchronizing configuration..."
if [ -f "$SCRIPT_DIR/sync-env.sh" ]; then
    "$SCRIPT_DIR/sync-env.sh"
    echo ""
fi

# Platform compatibility note
echo "ℹ️  This script requires Bash and is tested on Mac, Linux, and Windows (WSL/Git Bash)."
echo "   For Windows, use WSL or Git Bash for best results."

# Docker Compose version check
REQUIRED_COMPOSE_VERSION="2.0.0"
COMPOSE_VERSION=$(docker-compose version --short 2>/dev/null || echo "")
if [ -z "$COMPOSE_VERSION" ]; then
    echo "⚠️  Docker Compose not found. Please install Docker Compose v$REQUIRED_COMPOSE_VERSION or newer."
    exit 1
fi
if [ "$(printf '%s\n' "$REQUIRED_COMPOSE_VERSION" "$COMPOSE_VERSION" | sort -V | head -n1)" != "$REQUIRED_COMPOSE_VERSION" ]; then
    echo "⚠️  Docker Compose version $COMPOSE_VERSION detected. v$REQUIRED_COMPOSE_VERSION or newer is required."
    exit 1
fi

echo "🚀 Starting Base2 Docker Environment..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if .env file exists and validate required variables
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ Created .env file. Please review and update it if needed."
    else
        echo "❌ Error: .env.example not found. Cannot create .env file."
        exit 1
    fi
fi

# Validate required .env variables relevant to this stack
# Keep concise: domain and core service ports/credentials
REQUIRED_VARS=(WEBSITE_DOMAIN NETWORK_NAME TRAEFIK_PORT BACKEND_PORT POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB)
for VAR in "${REQUIRED_VARS[@]}"; do
    if ! grep -q "^$VAR=" .env; then
        echo "❌ Error: Required environment variable $VAR is missing in .env."
        exit 1
    fi
done

# Parse command line arguments
BUILD=false
DETACHED=true
SELF_TEST=false

while [[ $# -gt 0 ]]; do
    case $1 in
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
        --help|-h)
            echo "Usage: ./start.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -b, --build       Rebuild images before starting"
            echo "  -f, --foreground  Run in foreground (don't detach)"
            echo "  --self-test       Run script self-test and exit"
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

# Self-test function
if [ "$SELF_TEST" = true ]; then
    echo "🔎 Running start.sh self-test..."
    # Check Docker
    if ! command -v docker &>/dev/null; then
        echo "❌ Docker not found."
        exit 1
    fi
    # Check Docker Compose
    if ! command -v docker-compose &>/dev/null; then
        echo "❌ Docker Compose not found."
        exit 1
    fi
    # Check .env
    if [ ! -f .env ]; then
        echo "❌ .env file missing."
        exit 1
    fi
    # Check required variables
    for VAR in "${REQUIRED_VARS[@]}"; do
        if ! grep -q "^$VAR=" .env; then
            echo "❌ Required variable $VAR missing in .env."
            exit 1
        fi
    done
    echo "✅ Self-test passed."
    exit 0
fi

# Build if requested
if [ "$BUILD" = true ]; then
    echo "🔨 Building services..."
    docker-compose -f "$COMPOSE_FILE" build
fi

# Start services
if [ "$DETACHED" = true ]; then
    echo "🐳 Starting services in detached mode..."
    docker-compose -f "$COMPOSE_FILE" up -d
    
    echo ""
    echo "✅ Services started successfully!"
    echo ""
    echo "📊 Service Status:"
    docker-compose -f "$COMPOSE_FILE" ps
    
    echo ""
    echo "🌐 Access services at:"
    # Load env for dynamic endpoints
    if [ -f .env ]; then
        # shellcheck disable=SC2046
        export $(grep -E '^(WEBSITE_DOMAIN|TRAEFIK_HOST_PORT|BACKEND_PORT|PGADMIN_PORT)=' .env | xargs)
    fi
    TRAEFIK_HOST_PORT_PRINT=${TRAEFIK_HOST_PORT:-8080}
    WEBSITE_DOMAIN_PRINT=${WEBSITE_DOMAIN:-localhost}
    echo "  - Frontend (HTTP via Traefik):  http://localhost:${TRAEFIK_HOST_PORT_PRINT}"
    echo "  - Frontend (HTTPS via Traefik): https://${WEBSITE_DOMAIN_PRINT} (staging cert)"
    echo "  - API (via Traefik):            https://${WEBSITE_DOMAIN_PRINT}/api"
    echo "  - PostgreSQL:                   internal-only"
    echo "  - pgAdmin:                      internal-only"
    echo "  - Traefik Dashboard:            disabled insecure access"
    echo ""
    echo "💡 View logs: ./scripts/logs.sh"
else
    echo "🐳 Starting services in foreground mode..."
    docker-compose -f "$COMPOSE_FILE" up
fi
