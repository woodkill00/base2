#!/bin/bash

# ==========================================
# Test Script
# Usage: ./scripts/bash/test.sh [--coverage] [--watch] [--self-test]
# Options:
#   --coverage        Run tests with coverage
#   --watch           Run tests in watch mode
#   --self-test       Run script self-test and exit
# ==========================================

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Parse arguments
COVERAGE_FLAG=""
WATCH_FLAG=""
SELF_TEST=false
COMPOSE_FILE="development.docker.yml"
ENV_FILE=".env"

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
        --coverage)
            COVERAGE_FLAG="--coverage"
            shift
            ;;
        --watch)
            WATCH_FLAG="--watch"
            shift
            ;;
        --self-test)
            SELF_TEST=true
            shift
            ;;
        --help|-h)
            echo "Usage: ./scripts/bash/test.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -c, --compose-file FILE  Use a specific compose file"
            echo "  -e, --env-file FILE      Use a specific env file"
            echo "  --coverage        Run tests with coverage"
            echo "  --watch           Run tests in watch mode"
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

if [ ! -f "$COMPOSE_FILE" ]; then
    echo -e "${RED}âŒ compose file not found: $COMPOSE_FILE${NC}"
    exit 1
fi
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}âŒ env file not found: $ENV_FILE${NC}"
    exit 1
fi
COMPOSE_CMD="docker compose --env-file $ENV_FILE -f $COMPOSE_FILE"
USE_LOCAL_STACK=false
if [ "$(basename "$COMPOSE_FILE")" = "local.docker.yml" ] && [ "$(basename "$ENV_FILE")" = ".env.local" ]; then
    USE_LOCAL_STACK=true
fi

COVERAGE_ENV_ARGS="-e COVERAGE_FILE=/tmp/.coverage"
YAML_ENV_ARGS="-e PYTHONYAML_FORCE_PURE=1"
PYTEST_MARKS=(-m "not integration and not perf")
PYTEST_CACHE_ARGS=(-o "cache_dir=/tmp/pytest-cache")
API_PYTEST_CONFIG=(-c "api/pytest.ini")
DJANGO_PYTEST_CONFIG=(-c "pytest.ini")

require_compose_running() {
    if ! command -v docker >/dev/null 2>&1; then
        echo -e "${RED}âŒ Docker is not installed or not on PATH.${NC}"
        echo -e "${BLUE}Run ./scripts/bash/start.sh to start the stack, then re-run tests.${NC}"
        exit 1
    fi

    if [ ! -f "$COMPOSE_FILE" ]; then
        echo -e "${RED}âŒ $COMPOSE_FILE not found. Run this script from the repo root.${NC}"
        exit 1
    fi

    running_services=$($COMPOSE_CMD ps --services --filter "status=running" 2>/dev/null || true)
    if ! echo "$running_services" | grep -q '^api$'; then
        echo -e "${RED}âŒ api container is not running.${NC}"
        echo -e "${BLUE}Run ./scripts/bash/start.sh (or make up) to start the stack.${NC}"
        exit 1
    fi
    if ! echo "$running_services" | grep -q '^django$'; then
        echo -e "${RED}âŒ django container is not running.${NC}"
        echo -e "${BLUE}Run ./scripts/bash/start.sh (or make up) to start the stack.${NC}"
        exit 1
    fi
}

# Self-test function
if [ "$SELF_TEST" = true ]; then
    echo -e "${BLUE}ðŸ”Ž Running test.sh self-test...${NC}"
    # Check Docker
    if ! command -v docker &>/dev/null; then
        echo -e "${RED}âŒ docker not found.${NC}"
        exit 1
    fi
    # Check Node.js
    if ! command -v node &>/dev/null; then
        echo -e "${RED}âŒ Node.js not found.${NC}"
        exit 1
    fi
    # Check npm
    if ! command -v npm &>/dev/null; then
        echo -e "${RED}âŒ npm not found.${NC}"
        exit 1
    fi
    # Check frontend test script
    if ! grep -q 'test' react-app/package.json; then
        echo -e "${RED}âŒ Frontend test script missing in package.json.${NC}"
        exit 1
    fi
    echo -e "${GREEN}âœ… Self-test passed.${NC}"
    exit 0
fi

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}Running All Tests${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

BACKEND_EXIT_CODE=0
echo -e "${BLUE}Running backend tests inside Docker compose...${NC}"
require_compose_running

if [ "$USE_LOCAL_STACK" = true ]; then
    $COMPOSE_CMD exec -T redis sh -lc 'redis-cli -a "$REDIS_PASSWORD" FLUSHALL' >/dev/null 2>&1 || true
fi

set +e
if [ "$USE_LOCAL_STACK" = true ]; then
    # Repository-contract tests intentionally inspect a small, fixed set of
    # cross-service sources. Keep those sources out of the long-running API
    # container and expose them read-only only to this ephemeral test runner.
    $COMPOSE_CMD run --rm -T --no-deps \
        -v "$PWD/django:/app/django:ro" \
        -v "$PWD/docs:/app/docs:ro" \
        -v "$PWD/local.docker.yml:/app/local.docker.yml:ro" \
        -v "$PWD/development.docker.yml:/app/development.docker.yml:ro" \
        -v "$PWD/.coveragerc:/app/.coveragerc:ro" \
        $COVERAGE_ENV_ARGS $YAML_ENV_ARGS api \
        pytest "${PYTEST_MARKS[@]}" "${PYTEST_CACHE_ARGS[@]}" "${API_PYTEST_CONFIG[@]}" api/tests
    API_EXIT_CODE=$?
else
    $COMPOSE_CMD exec -T $COVERAGE_ENV_ARGS $YAML_ENV_ARGS api pytest "${PYTEST_MARKS[@]}" "${PYTEST_CACHE_ARGS[@]}" "${API_PYTEST_CONFIG[@]}" api/tests
    API_EXIT_CODE=$?
fi
$COMPOSE_CMD exec -T $COVERAGE_ENV_ARGS $YAML_ENV_ARGS django pytest "${PYTEST_MARKS[@]}" "${PYTEST_CACHE_ARGS[@]}" "${DJANGO_PYTEST_CONFIG[@]}"
DJANGO_EXIT_CODE=$?
set -e

if [ $API_EXIT_CODE -ne 0 ] || [ $DJANGO_EXIT_CODE -ne 0 ]; then
    BACKEND_EXIT_CODE=1
fi

echo ""
echo -e "${GREEN}Running Frontend Tests...${NC}"
cd react-app

if [ ! -d "node_modules" ]; then
    echo -e "${RED}Frontend dependencies not installed. Run 'npm install' first.${NC}"
    exit 1
fi

run_frontend_tests() {
    if [ -n "$WATCH_FLAG" ]; then
        npm run test:watch
    elif [ -n "$COVERAGE_FLAG" ]; then
        npm run test
    else
        npm run test:ci
    fi
}

set +e
run_frontend_tests
FRONTEND_EXIT_CODE=$?
set -e

# A native V8 crash is an infrastructure failure, not a test assertion. Retry
# that exact runtime once so a transient WSL fault cannot silently terminate the
# gate; a second crash or any ordinary test failure remains a hard failure.
if [ "$FRONTEND_EXIT_CODE" -eq 139 ]; then
    echo -e "${RED}Frontend Node runtime crashed with SIGSEGV; retrying once.${NC}"
    set +e
    run_frontend_tests
    FRONTEND_EXIT_CODE=$?
    set -e
fi

cd ..

echo ""
echo -e "${BLUE}================================================${NC}"

if [ $BACKEND_EXIT_CODE -eq 0 ] && [ $FRONTEND_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}âœ“ All tests passed!${NC}"
    echo -e "${BLUE}================================================${NC}"
    exit 0
else
    echo -e "${RED}âœ— Some tests failed${NC}"
    echo -e "${BLUE}================================================${NC}"
    exit 1
fi
