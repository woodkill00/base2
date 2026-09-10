#!/usr/bin/env bash
set -euo pipefail

mkdir -p /root/logs
rm -rf /root/logs/* || true
mkdir -p /root/logs/build /root/logs/services /root/logs/meta

DOMAIN=""
if [ -f .env ]; then
  DOMAIN=$(grep -E '^WEBSITE_DOMAIN=' .env 2>/dev/null | cut -d'=' -f2 | sed 's/[[:space:]]*#.*$//' | tr -d '\r')
fi

RESOLVE_DOMAIN=()
if [ -n "$DOMAIN" ]; then
  RESOLVE_DOMAIN=(--resolve "$DOMAIN:443:127.0.0.1")
fi

# Core docker artifacts
(docker compose -f development.docker.yml ps > /root/logs/compose-ps.txt) || true
(docker ps --format '{{.Names}}\t{{.Ports}}' | awk 'NF && $2!="" {print}' > /root/logs/published-ports.txt) || true

# Traefik artifacts
TID=$(docker compose -f development.docker.yml ps -q traefik 2>/dev/null | head -n 1 || true)
if [ -n "$TID" ]; then
  (docker exec "$TID" sh -lc 'for key in WEBSITE_DOMAIN TRAEFIK_CERT_EMAIL TRAEFIK_CERT_RESOLVER TRAEFIK_PREVIEW_MODE OWNER_ALLOWLIST_CSV; do if printenv "$key" >/dev/null 2>&1; then printf "%s=present\n" "$key"; else printf "%s=missing\n" "$key"; fi; done' > /root/logs/traefik-env.txt) || true
  (docker exec "$TID" cat /tmp/traefik.yml > /root/logs/traefik-static.yml) || (docker exec "$TID" cat /etc/traefik/traefik.yml > /root/logs/traefik-static.yml) || echo "EMPTY" > /root/logs/traefik-static.yml
  (docker exec "$TID" cat /tmp/dynamic.yml > /root/logs/traefik-dynamic.yml) || (docker exec "$TID" cat /etc/traefik/dynamic/dynamic.yml > /root/logs/traefik-dynamic.yml) || echo "EMPTY" > /root/logs/traefik-dynamic.yml
  (docker exec "$TID" sh -lc 'ls -l /etc/traefik /etc/traefik/dynamic' > /root/logs/traefik-ls.txt) || true
  (docker exec "$TID" sh -lc 'ls -la /etc/traefik/acme 2>/dev/null || true; for f in /etc/traefik/acme/*.json; do [ -f "$f" ] || continue; stat -c "%a %n" "$f" 2>/dev/null || true; done' > /root/logs/traefik-acme-perms.txt) || true
  (docker exec "$TID" sh -lc 'cat /etc/traefik/templates/dynamic.yml.template 2>/dev/null || echo TEMPLATE_MISSING' > /root/logs/traefik-dynamic.template.yml) || true
  (docker exec "$TID" sh -lc 'cat /etc/traefik/templates/traefik.yml.template 2>/dev/null || echo TEMPLATE_MISSING' > /root/logs/traefik-static.template.yml) || true
  (docker logs --timestamps --tail=1000 "$TID" > /root/logs/traefik-logs.txt) || true
else
  echo "MISSING_CID" | tee /root/logs/traefik-env.txt /root/logs/traefik-static.yml /root/logs/traefik-dynamic.yml /root/logs/traefik-ls.txt /root/logs/traefik-acme-perms.txt /root/logs/traefik-logs.txt /root/logs/traefik-dynamic.template.yml /root/logs/traefik-static.template.yml >/dev/null
fi

# API logs
AID=$(docker compose -f development.docker.yml ps -q api 2>/dev/null | head -n 1 || true)
if [ -n "$AID" ]; then
  (docker logs --timestamps --tail=500 "$AID" > /root/logs/api-logs.txt) || true
else
  echo "MISSING_API_CID" > /root/logs/api-logs.txt
fi

# Migration state, health, and schema checks. Verification never mutates schema.
docker compose -f development.docker.yml exec -T api python -m api.scripts.migrate --check > /root/logs/api-migrate-check.txt 2>&1
docker compose -f development.docker.yml exec -T django python manage.py migrate --check --noinput > /root/logs/django-migrate.txt 2>&1
(docker compose -f development.docker.yml exec -T django python manage.py check --deploy > /root/logs/django-check-deploy.txt 2>&1) || true
(docker compose -f development.docker.yml exec -T django python - <<'PY' > /root/logs/django-internal-health.json 2> /root/logs/django-internal-health.status) || true
import json
import os
import sys
import time
from urllib.error import HTTPError
from urllib.request import urlopen

port = os.environ.get("PORT") or "8000"
url = f"http://127.0.0.1:{port}/internal/health"
status = 0
body = "{}"
last_error = ""

for _ in range(20):
  try:
    with urlopen(url, timeout=5) as resp:
      status = getattr(resp, "status", None) or resp.getcode() or 200
      body = resp.read().decode("utf-8")
      break
  except HTTPError as e:
    status = e.code
    try:
      body = e.read().decode("utf-8")
    except Exception:
      body = json.dumps({"ok": False, "service": "django", "db_ok": False})
    break
  except Exception as e:
    last_error = str(e)
    status = 0
    time.sleep(1)

if status == 0 and not body.strip():
  body = json.dumps({"ok": False, "service": "django", "db_ok": False, "error": last_error})

sys.stdout.write(body)
sys.stderr.write(str(status))
PY

set +e
(docker compose -f development.docker.yml exec -T django python manage.py schema_compat_check --json > /root/logs/schema-compat-check.json 2> /root/logs/schema-compat-check.err)
SCHEMA_STATUS=$?
echo $SCHEMA_STATUS > /root/logs/schema-compat-check.status
set -e

# Curl artifacts (use Traefik via localhost, avoid DNS propagation)
if [ -n "$DOMAIN" ]; then
  curl -sSI "${RESOLVE_DOMAIN[@]}" "https://$DOMAIN/" -o /root/logs/curl-root.txt
  curl -sSI "${RESOLVE_DOMAIN[@]}" "https://$DOMAIN/api/health" -o /root/logs/curl-api-health.txt
  curl -sSI "${RESOLVE_DOMAIN[@]}" "https://$DOMAIN/api/health/" -o /root/logs/curl-api-health-slash.txt
  curl -sS "${RESOLVE_DOMAIN[@]}" "https://$DOMAIN/api/health" -o /root/logs/api-health.json -w "%{http_code}\n" > /root/logs/api-health.status
  curl -sS "${RESOLVE_DOMAIN[@]}" "https://$DOMAIN/api/health/" -o /root/logs/api-health-slash.json -w "%{http_code}\n" > /root/logs/api-health-slash.status
  cp /root/logs/curl-api-health.txt /root/logs/curl-api.txt || true
  if ! grep -q '^HTTP/.* 200' /root/logs/curl-api.txt 2>/dev/null; then
    cp /root/logs/curl-api-health-slash.txt /root/logs/curl-api.txt || true
  fi
fi

# Request-id log propagation
set +e
RID=$(cat /proc/sys/kernel/random/uuid 2>/dev/null || true)
if [ -z "$RID" ]; then
  RID=$(python3 -c 'import uuid; print(str(uuid.uuid4()))' 2>/dev/null || true)
fi
export RID
: > /root/logs/request-id-health.headers || true
: > /root/logs/request-id-health.body || true
if [ -n "$DOMAIN" ]; then
  curl -sS "${RESOLVE_DOMAIN[@]}" -X POST \
    -H "X-Request-Id: $RID" \
    -H 'Content-Type: application/json' \
    -d '{"email":"request-id-probe@example.com","password":"not-a-real-password"}' \
    -D /root/logs/request-id-health.headers \
    -o /root/logs/request-id-health.body \
    "https://$DOMAIN/api/users/login" || true
fi

TIDS=$(docker compose -f development.docker.yml ps -q traefik 2>/dev/null || true)
AIDS=$(docker compose -f development.docker.yml ps -q api 2>/dev/null || true)
DJIDS=$(docker compose -f development.docker.yml ps -q django 2>/dev/null || true)

: > /root/logs/services/request-id-traefik.txt || true
: > /root/logs/services/request-id-api.txt || true
: > /root/logs/services/request-id-django.txt || true

if [ -n "$DJIDS" ]; then
  : > /root/logs/request-id-django-probe.txt || true
  docker compose -f development.docker.yml exec -T django python - <<PY > /root/logs/request-id-django-probe.txt 2>&1 || true
import http.client
import os

rid = "${RID}"
port = int(os.environ.get('PORT') or '8000')

print(f"rid_literal={rid}")
conn = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
conn.request('GET', '/internal/health', headers={'X-Request-Id': rid})
resp = conn.getresponse()
body = resp.read()
print(f"status={resp.status}")
print(f"resp_x_request_id={resp.getheader('X-Request-Id','')}")
print(f"body_len={len(body)}")
PY
fi

POLL_MAX=10
POLL_SLEEP=2
if [ -n "$TIDS" ]; then
  for i in $(seq 1 $POLL_MAX); do
    : > /root/logs/services/request-id-traefik.txt || true
    for id in $TIDS; do
      docker exec "$id" sh -lc "(grep -F \"$RID\" /var/log/traefik/access.log 2>/dev/null || true) | tail -n 50" >> /root/logs/services/request-id-traefik.txt 2>&1 || true
    done
    if [ -s /root/logs/services/request-id-traefik.txt ]; then break; fi
    sleep $POLL_SLEEP
  done
fi
if [ -n "$AIDS" ]; then
  for i in $(seq 1 $POLL_MAX); do
    : > /root/logs/services/request-id-api.txt || true
    for id in $AIDS; do
      docker logs --timestamps --since=10m "$id" 2>&1 | grep -F "$RID" >> /root/logs/services/request-id-api.txt || true
    done
    tail -n 50 /root/logs/services/request-id-api.txt > /root/logs/services/request-id-api.txt.tmp 2>/dev/null || true
    mv -f /root/logs/services/request-id-api.txt.tmp /root/logs/services/request-id-api.txt 2>/dev/null || true
    if [ -s /root/logs/services/request-id-api.txt ]; then break; fi
    sleep $POLL_SLEEP
  done
fi
if [ -n "$DJIDS" ]; then
  for i in $(seq 1 $POLL_MAX); do
    : > /root/logs/services/request-id-django.txt || true
    for id in $DJIDS; do
      docker logs --timestamps --since=10m "$id" 2>&1 | grep -F "$RID" >> /root/logs/services/request-id-django.txt || true
    done
    tail -n 50 /root/logs/services/request-id-django.txt > /root/logs/services/request-id-django.txt.tmp 2>/dev/null || true
    mv -f /root/logs/services/request-id-django.txt.tmp /root/logs/services/request-id-django.txt 2>/dev/null || true
    if [ -s /root/logs/services/request-id-django.txt ]; then break; fi
    sleep $POLL_SLEEP
  done
fi

python3 -c "import json, os; from pathlib import Path;\
rt=lambda p: (Path(p).read_text(encoding='utf-8', errors='replace').strip() if Path(p).exists() else '');\
rid=os.environ.get('RID','');\
found={\
  'traefik': bool(rt('/root/logs/services/request-id-traefik.txt')),\
  'api': bool(rt('/root/logs/services/request-id-api.txt')),\
  'django': bool(rt('/root/logs/services/request-id-django.txt'))\
};\
payload={'request_id': rid, 'ok': bool(rid) and found['api'] and found['django'], 'found': found};\
print(json.dumps(payload))" > /root/logs/request-id-log-propagation.json 2> /root/logs/request-id-log-propagation.err || true
set -e

# Optional celery check (for all-tests)
# Always create placeholder artifacts so the test runner doesn't fail on missing files.
python3 - <<'PY' > /root/logs/celery-ping.json 2>/dev/null || true
import json
print(json.dumps({"skipped": True, "reason": "celery check not executed"}))
PY
python3 - <<'PY' > /root/logs/celery-result.json 2>/dev/null || true
import json
print(json.dumps({"skipped": True, "reason": "celery check not executed"}))
PY

if [ "${RUN_CELERY_CHECK:-}" = "1" ] && [ -n "$DOMAIN" ]; then
  curl -sS "${RESOLVE_DOMAIN[@]}" -X POST "https://$DOMAIN/api/celery/ping" -H 'Content-Type: application/json' -d '{}' -o /root/logs/celery-ping.json || true
  TASK_ID=$(python3 - <<'PY'
import json
try:
  data=json.load(open('/root/logs/celery-ping.json'))
  print(data.get('task_id',''))
except Exception:
  print('')
PY
  )
  if [ -n "$TASK_ID" ]; then
    for i in $(seq 1 12); do
      curl -sS "${RESOLVE_DOMAIN[@]}" "https://$DOMAIN/api/celery/result/$TASK_ID" -o /root/logs/celery-result.json || true
      if grep -q '"successful": *true' /root/logs/celery-result.json 2>/dev/null; then
        break
      fi
      sleep 5
    done
  else
    python3 - <<'PY' > /root/logs/celery-result.json 2>/dev/null || true
import json
print(json.dumps({"ok": False, "reason": "missing task_id"}))
PY
  fi
fi
