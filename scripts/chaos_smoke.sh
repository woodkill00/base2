#!/usr/bin/env bash
set -euo pipefail

# Chaos smoke: restart DB/Redis briefly to validate graceful failure/recovery.
# Requires local/docker access to the compose project.

if ! command -v docker >/dev/null; then
  echo "docker not found" >&2
  exit 1
fi

PROJECT=${COMPOSE_PROJECT_NAME:-base2}

echo "[INFO] Restarting postgres and redis containers for chaos smoke..."
docker compose restart postgres redis

echo "[INFO] Waiting 10s for services to settle..."
sleep 10

echo "[INFO] Probing API health"
curl -fsS http://localhost:8000/api/health || echo "[WARN] API health probe failed (expected during chaos)"

echo "[INFO] Done"
