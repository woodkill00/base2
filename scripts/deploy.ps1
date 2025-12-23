param(
  [switch]$Full,
  [switch]$UpdateOnly,
  [string]$EnvPath = ".\.env",
  [string]$SshKey = "$env:USERPROFILE\.ssh\base2",
  [string]$DropletIp = "",
  [switch]$SkipAllowlist,
  [string]$LogsDir = ".\local_run_logs",
  [switch]$Timestamped,
  [switch]$Preflight,
  [switch]$RunTests,
  [switch]$TestsJson,
  [switch]$RunRateLimitTest,
  [switch]$RunCeleryCheck,
  [int]$RateLimitBurst = 20,
  [int]$VerifyTimeoutSec = 600,
  [switch]$AsyncVerify,
  [int]$LogsPollMaxAttempts = 30,
  [int]$LogsPollIntervalSec = 10,
  [string]$ReportName = 'post-deploy-report.json'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:ArtifactDir = ''
$script:ResolvedIp = ''
$script:RunStamp = (Get-Date -Format 'yyyyMMdd_HHmmss')

function Write-Section($msg) {
  Write-Host "`n=== $msg ===" -ForegroundColor Cyan
}

function Ensure-ArtifactDir([string]$ip = '') {
  # Always write artifacts into a per-run folder to avoid polluting LogsDir.
  # Folder format: <ip>-<timestamp>. If IP is unknown early in the run, we create
  # unknown-<timestamp> and rename once IP becomes available.
  $safeIp = if ($ip -and $ip.Trim()) { $ip.Trim() } elseif ($script:ResolvedIp) { $script:ResolvedIp } else { 'unknown' }
  $leaf = "$safeIp-$($script:RunStamp)"
  $targetDir = Join-Path $LogsDir $leaf

  if (-not (Test-Path $LogsDir)) { New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null }

  if ($script:ArtifactDir -and (Test-Path $script:ArtifactDir)) {
    # If we created an unknown-* folder earlier, rename it when IP is known.
    try {
      $currentLeaf = Split-Path -Leaf $script:ArtifactDir
      if (($currentLeaf -like 'unknown-*') -and ($safeIp -ne 'unknown')) {
        if (-not (Test-Path $targetDir)) {
          Move-Item -Path $script:ArtifactDir -Destination $targetDir -Force
          $script:ArtifactDir = (Resolve-Path $targetDir).Path
        } else {
          # If target exists, keep current dir to avoid clobber.
          $script:ArtifactDir = (Resolve-Path $script:ArtifactDir).Path
        }
      }
    } catch {}
    return $script:ArtifactDir
  }

  if (-not (Test-Path $targetDir)) { New-Item -ItemType Directory -Path $targetDir -Force | Out-Null }
  $script:ArtifactDir = (Resolve-Path $targetDir).Path
  return $script:ArtifactDir
}

function Write-FailureArtifacts([string]$context, [string]$message) {
  $dest = Ensure-ArtifactDir
  try {
    $support = @()
    $support += "Deploy failed: $context"
    $support += "Message: $message"
    $support += "Time (UTC): $(Get-Date -AsUTC -Format 'yyyy-MM-ddTHH:mm:ssZ')"
    $support += "Tip: Re-run with -Preflight to validate config before cloud actions."
    Set-Content -Path (Join-Path $dest 'support.txt') -Value ($support -join [Environment]::NewLine) -Encoding UTF8
  } catch {}
  try {
    Set-Content -Path (Join-Path $dest 'deploy-error.txt') -Value $message -Encoding UTF8
  } catch {}
  # Ensure the orchestrator knows where to write per-run artifacts.
  try { $env:BASE2_ARTIFACT_DIR = $dest } catch {}
  try {
    & docker compose -f ./local.docker.yml config > (Join-Path $dest 'compose-config-local.yml') 2>$null
  } catch {}
}

function Ensure-Venv {
  if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Section "Creating Python venv (.venv)"
    python -m venv .venv
  }
  Write-Section "Installing Python requirements"
  & .\.venv\Scripts\python.exe -m pip install --upgrade pip | Out-Null
  & .\.venv\Scripts\python.exe -m pip install -r .\digital_ocean\requirements.txt | Out-Null
}

function Activate-Venv {
  Write-Section "Activating venv"
  & .\.venv\Scripts\Activate.ps1
}

function Load-DotEnv([string]$path) {
  Write-Section "Loading .env into process environment"
  if (-not (Test-Path $path)) { Write-Warning "Missing $path"; return }
  Get-Content $path | ForEach-Object {
    $line = $_.Trim()
    if (-not $line) { return }
    if ($line.StartsWith('#')) { return }
    if ($line -match '^[A-Za-z_][A-Za-z0-9_]*=') {
      $kv = $line -split '=', 2
      $k = $kv[0]
      $v = $kv[1]
      # Strip inline comments (anything after an unquoted #)
      $hashIndex = $v.IndexOf('#')
      if ($hashIndex -ge 0) { $v = $v.Substring(0, $hashIndex).TrimEnd() }
      # Strip surrounding quotes if present
      if ($v.StartsWith('"') -and $v.EndsWith('"')) { $v = $v.Substring(1, $v.Length-2) }
      if ($v.StartsWith("'") -and $v.EndsWith("'")) { $v = $v.Substring(1, $v.Length-2) }
      [System.Environment]::SetEnvironmentVariable($k, $v, 'Process')
    }
  }
}
function Assert-EnvNotTracked {
  # If .env is tracked, any git reset/clean/pull on the droplet can overwrite secrets.
  # This should never happen in this repo; .env must remain local-only.
  try {
    $null = Get-Command git -ErrorAction Stop
    & git ls-files --error-unmatch .env 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
      throw ".env is tracked by git. Fix by running: git rm --cached .env (and commit), ensure .gitignore includes .env, then re-run deploy."
    }
  } catch {
    # If git isn't available or check fails in a non-fatal way, don't block deploy.
  }
}

function Update-Allowlist {
  if ($SkipAllowlist) { return }
  Write-Section "Updating pgAdmin IP allowlist in .env"
  & .\scripts\update-pgadmin-allowlist.ps1 -EnvPath $EnvPath
}

function Invoke-Preflight {
  Write-Section "Preflight validation"
  # Runs strict validation of .env, compose labels/ports, and required files.
  # Fails fast on any issue to prevent orchestration.
  & .\scripts\validate-predeploy.ps1 -Strict
}

function Validate-DoCreds {
  Write-Section "Validating DigitalOcean credentials"
  $token = $env:DO_API_TOKEN
  if (-not $token -or -not $token.Trim()) {
    throw "Missing DO_API_TOKEN in environment. Set it in .env or process env before deploy."
  }
  # Lightweight token validation via pydo droplets.list
  $tmpPy = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), 'validate_do_token.py')
  $pyCode = @'
import os
from pydo import Client

token = os.environ.get('DO_API_TOKEN')
if not token:
    raise RuntimeError('missing token')
try:
    c = Client(token=token)
    c.droplets.list(per_page=1)
except Exception as e:
    raise SystemExit(f'invalid_token: {e.__class__.__name__}')
'@
  Set-Content -Path $tmpPy -Value $pyCode -NoNewline
   & .\.venv\Scripts\python.exe $tmpPy 2>$null | Out-Null
  if ($LASTEXITCODE -ne 0) {
    throw "Invalid DO_API_TOKEN or API unreachable. Validate token before continuing."
  }
}

function Get-DropletIp {
  if ($DropletIp) { return $DropletIp }
  $udFile = Join-Path $PSScriptRoot "..\DO_userdata.json"
  if (Test-Path $udFile) {
    try {
      $json = Get-Content $udFile -Raw | ConvertFrom-Json
      if ($json.ip_address) { return [string]$json.ip_address }
    } catch { }
  }
  # Fallback: query DigitalOcean API via pydo using DO_DROPLET_NAME
  $tmpPy = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), 'get_do_ip.py')
  $pyCode = @'
import os, sys
from pydo import Client

token = os.environ.get('DO_API_TOKEN')
name = os.environ.get('DO_DROPLET_NAME') or 'base2-droplet'
if not token:
    print('')
    sys.exit(0)
try:
    c = Client(token=token)
    # List droplets and find by name
    resp = c.droplets.list(per_page=200)
    droplets = resp.get('droplets', [])
    ip = None
    for d in droplets:
        if d.get('name') == name:
            for n in d.get('networks', {}).get('v4', []):
                if n.get('type') == 'public':
                    ip = n.get('ip_address')
                    break
            break
    print(ip or '')
except Exception:
    print('')
'@
  Set-Content -Path $tmpPy -Value $pyCode -NoNewline
   $ipGuess = & .\.venv\Scripts\python.exe $tmpPy 2>$null
  if ($LASTEXITCODE -eq 0 -and $ipGuess) { return [string]$ipGuess.Trim() }
  return ""
}

function Run-Orchestrator {
  Write-Section "Running orchestrator"
  $cliArgs = @()
  if (-not $Full -and $UpdateOnly) { $cliArgs += '--update-only' }
  & .\.venv\Scripts\python.exe .\digital_ocean\orchestrate_deploy.py @cliArgs
}

function Remote-Verify($ip, $keyPath) {
  Write-Section "Remote verification on $ip"
  $null = Ensure-ArtifactDir -ip $ip
  $sshExe = "ssh"
  $scpExe = "scp"
  $sshCommon = @('-o','ConnectTimeout=20','-o','ServerAliveInterval=15','-o','ServerAliveCountMax=4','-o','StrictHostKeyChecking=no')
  $sshArgs = @('-i', $keyPath) + $sshCommon + @("root@$ip")
  # Create a remote verification script to avoid quoting pitfalls
  $tmpScript = Join-Path $env:TEMP "remote_verify.sh"
  $scriptContent = @'
set -eu
mkdir -p /root/logs
if [ -d /opt/apps/base2 ]; then
  cd /opt/apps/base2
  # Prepare log directories
  mkdir -p /root/logs/build /root/logs/services || true
  # Preserve the active .env across git reset/clean (the repo may track a template .env)
  if [ -f .env ]; then
    cp -f .env /root/logs/build/env-backup.env || true
  fi
  # Ensure latest repo and rebuild traefik to render new templates
  if command -v git >/dev/null 2>&1; then
    # Determine branch from .env (DO_APP_BRANCH), default to main
    BRANCH=$(grep -E '^DO_APP_BRANCH=' .env 2>/dev/null | cut -d'=' -f2 | tr -d '\r')
    if [ -z "$BRANCH" ]; then BRANCH=main; fi
    git fetch --all --prune || true
    # Backup and remove potential untracked files that can block checkout (e.g., ACME storage)
    if [ -d letsencrypt ]; then
      tar -czf /root/logs/build/letsencrypt-backup.tgz letsencrypt || true
      rm -rf letsencrypt || true
    fi
    # Reset any local changes and clean untracked files to avoid checkout failures
    git reset --hard HEAD || true
    git clean -fd || true
    # Force checkout to track remote branch and hard reset to remote to avoid rebase or merge prompts
    if git show-ref --verify --quiet "refs/remotes/origin/$BRANCH"; then
      git checkout -B "$BRANCH" "origin/$BRANCH" || git checkout -f "$BRANCH" || true
      git reset --hard "origin/$BRANCH" || true
    else
      git checkout -f "$BRANCH" || true
      git pull --rebase || true
    fi
  fi
  # Restore .env after repo sync so Compose uses the deployed values
  if [ -f /root/logs/build/env-backup.env ]; then
    cp -f /root/logs/build/env-backup.env .env || true
  fi

  # Guardrail: htpasswd strings must not be double-escaped in the droplet .env.
  # Compose treats $$ as an escape for a literal $, so a $$$$ run would land as $$ in the container,
  # breaking htpasswd hashes that require single-$ delimiters.
  python3 - <<'PY' > /root/logs/build/env-dollar-check.txt 2>&1
import re
from pathlib import Path

p = Path('/opt/apps/base2/.env')
raw = p.read_text(encoding='utf-8', errors='replace')
keys = ['TRAEFIK_DASH_BASIC_USERS', 'FLOWER_BASIC_USERS']

def get_val(key: str):
    for line in raw.splitlines():
        if line.startswith(key + '='):
            return line.split('=', 1)[1].strip().rstrip('\r')
    return None

bad = []
for k in keys:
    v = get_val(k)
    if not v:
        continue
    runs = [len(m.group(0)) for m in re.finditer(r"\$+", v)]
    max_run = max(runs) if runs else 0
    total = v.count('$')
    print(f"{k}: len={len(v)} dollar_total={total} dollar_max_run={max_run}")
    if max_run > 2:
        bad.append(k)

if bad:
    print('ERROR: Detected over-escaped $ runs in .env for: ' + ', '.join(bad))
    raise SystemExit(2)
PY
  # Capture build and up logs for the core stack
  docker compose -f local.docker.yml build --no-cache traefik > /root/logs/build/traefik-build.txt 2>&1 || true
  docker compose -f local.docker.yml build django > /root/logs/build/django-build.txt 2>&1 || true
  docker compose -f local.docker.yml build api > /root/logs/build/api-build.txt 2>&1 || true
  docker compose -f local.docker.yml build react-app > /root/logs/build/react-build.txt 2>&1 || true

  # Bring up core services needed for edge routing (avoid 502 due to missing upstreams)
  docker compose -f local.docker.yml up -d --remove-orphans postgres django api react-app nginx-static traefik redis pgadmin flower > /root/logs/build/compose-up-core.txt 2>&1 || true
  docker compose -f local.docker.yml up -d --force-recreate traefik > /root/logs/build/traefik-up.txt 2>&1 || true

  # Ensure Flower is started (kept as a separate log artifact)
  docker compose -f local.docker.yml up -d flower > /root/logs/build/flower-up.txt 2>&1 || true

  # Ensure Django service is running for admin route
  docker compose -f local.docker.yml up -d django > /root/logs/build/django-up.txt 2>&1 || true
  # Capture Django migration output into a dedicated artifact
  docker compose -f local.docker.yml exec -T django python manage.py migrate --noinput > /root/logs/django-migrate.txt 2>&1 || true
  # Django deploy checks (security + config sanity)
  docker compose -f local.docker.yml exec -T django python manage.py check --deploy > /root/logs/django-check-deploy.txt 2>&1 || true
  # Schema compatibility check (fails if migrations unapplied or schema drift)
  set +e
  docker compose -f local.docker.yml exec -T django python manage.py schema_compat_check --json > /root/logs/schema-compat-check.json 2> /root/logs/schema-compat-check.err
  echo $? > /root/logs/schema-compat-check.status
  set -e
  # If requested, enable celery/flower profiles and build required images
  if [ "${RUN_CELERY_CHECK:-}" = "1" ]; then
    # Tune host sysctl for Redis memory overcommit (best-effort, ignore errors)
    (sysctl -w vm.overcommit_memory=1 && echo 'vm.overcommit_memory=1' > /etc/sysctl.d/99-redis.conf && sysctl --system) || true
    # Build API (used by Celery worker image) if present; ignore if missing
    docker compose -f local.docker.yml build api > /root/logs/build/api-build.txt 2>&1 || true
    # Start Redis, Celery worker and beat under the celery profile; ignore if services not defined
    docker compose -f local.docker.yml --profile celery up -d redis celery-worker celery-beat > /root/logs/build/celery-up.txt 2>&1 || true
    # Start Flower if defined
    docker compose -f local.docker.yml up -d flower > /root/logs/build/flower-up.txt 2>&1 || true
  fi
  docker compose -f local.docker.yml ps > /root/logs/compose-ps.txt || true
  docker compose -f local.docker.yml config > /root/logs/compose-config.yml || true
  # Published host ports report (Traefik should be the only one)
  docker ps --format '{{.Names}}\t{{.Ports}}' | awk 'NF && $2!="" {print}' > /root/logs/published-ports.txt || true
  # Capture logs from all services
  # Collect logs for services across default and profiled stacks (celery, flower)
  S_DEF=$(docker compose -f local.docker.yml config --services || true)
  S_CEL=$(docker compose -f local.docker.yml --profile celery config --services || true)
  S_FLO=$(docker compose -f local.docker.yml --profile flower config --services || true)
  SERVICES=$(printf "%s\n%s\n%s\n" "$S_DEF" "$S_CEL" "$S_FLO" | awk 'NF && !x[$0]++')
  for s in $SERVICES; do
    docker compose -f local.docker.yml logs --no-color --timestamps --tail=2000 "$s" > "/root/logs/services/${s}.log" 2>&1 || true
  done
  CID=$(docker compose -f local.docker.yml ps -q traefik || true)
  if [ -n "$CID" ]; then
    docker exec "$CID" sh -lc 'env | sort' > /root/logs/traefik-env.txt || true
    if docker exec "$CID" test -s /etc/traefik/traefik.yml; then
      docker exec "$CID" cat /etc/traefik/traefik.yml > /root/logs/traefik-static.yml || true
    else
      echo "EMPTY" > /root/logs/traefik-static.yml
    fi
    if docker exec "$CID" test -s /etc/traefik/dynamic/dynamic.yml; then
      docker exec "$CID" cat /etc/traefik/dynamic/dynamic.yml > /root/logs/traefik-dynamic.yml || true
    else
      echo "EMPTY" > /root/logs/traefik-dynamic.yml
    fi
    docker exec "$CID" sh -lc 'ls -l /etc/traefik /etc/traefik/dynamic' > /root/logs/traefik-ls.txt || true
    # Capture the templates used inside the container for debugging
    docker exec "$CID" sh -lc 'cat /etc/traefik/templates/dynamic.yml.template 2>/dev/null || echo TEMPLATE_MISSING' > /root/logs/traefik-dynamic.template.yml || true
    docker exec "$CID" sh -lc 'cat /etc/traefik/templates/traefik.yml.template 2>/dev/null || echo TEMPLATE_MISSING' > /root/logs/traefik-static.template.yml || true
    docker logs --timestamps --tail=1000 "$CID" > /root/logs/traefik-logs.txt || true
    # Capture API logs for quick diagnostics (in addition to per-service logs)
    AID=$(docker compose -f local.docker.yml ps -q api || true)
    if [ -n "$AID" ]; then
      docker logs --timestamps --tail=500 "$AID" > /root/logs/api-logs.txt || true
    else
      echo "MISSING_API_CID" > /root/logs/api-logs.txt
    fi
  else
    echo "MISSING_CID" | tee /root/logs/traefik-env.txt /root/logs/traefik-static.yml /root/logs/traefik-dynamic.yml /root/logs/traefik-ls.txt /root/logs/traefik-logs.txt /root/logs/api-logs.txt >/dev/null
  fi
  DOMAIN=$(grep -E '^WEBSITE_DOMAIN=' /opt/apps/base2/.env | cut -d'=' -f2 | tr -d '\r')
  if [ -n "$DOMAIN" ]; then
    # Ensure expected curl artifacts exist even if curl/DNS/TLS fails
    : > /root/logs/curl-root.txt || true
    : > /root/logs/curl-api-health.txt || true
    : > /root/logs/curl-api-health-slash.txt || true
    : > /root/logs/curl-api.txt || true
    : > /root/logs/curl-admin-head.txt || true
    : > /root/logs/api-health.json || true
    : > /root/logs/api-health.status || true
    : > /root/logs/api-health-slash.json || true
    : > /root/logs/api-health-slash.status || true

    # Curl against the local Traefik listener, but use the real hostname for SNI/Host.
    RESOLVE_DOMAIN=(--resolve "$DOMAIN:443:127.0.0.1")

    # Root HEAD
    curl -skI "${RESOLVE_DOMAIN[@]}" "https://$DOMAIN/" -o /root/logs/curl-root.txt || true

    # API health HEAD (both forms)
    curl -skI "${RESOLVE_DOMAIN[@]}" "https://$DOMAIN/api/health" -o /root/logs/curl-api-health.txt || true
    curl -skI "${RESOLVE_DOMAIN[@]}" "https://$DOMAIN/api/health/" -o /root/logs/curl-api-health-slash.txt || true

    # API health GET (capture body and status separately)
    curl -sk "${RESOLVE_DOMAIN[@]}" -o /root/logs/api-health.json -w "%{http_code}" "https://$DOMAIN/api/health" > /root/logs/api-health.status || true
    curl -sk "${RESOLVE_DOMAIN[@]}" -o /root/logs/api-health-slash.json -w "%{http_code}" "https://$DOMAIN/api/health/" > /root/logs/api-health-slash.status || true

    # Back-compat: maintain curl-api.txt pointing at preferred health endpoint (non-slash first)
    cp /root/logs/curl-api-health.txt /root/logs/curl-api.txt || true
    if ! grep -q '^HTTP/.* 200' /root/logs/curl-api.txt 2>/dev/null; then
      cp /root/logs/curl-api-health-slash.txt /root/logs/curl-api.txt || true
    fi

    # Flower 401 check via Traefik (no credentials) -> expect 401 if guarded
    FL_LABEL=$(grep -E '^FLOWER_DNS_LABEL=' /opt/apps/base2/.env | cut -d'=' -f2 | tr -d '\r')
    if [ -n "$FL_LABEL" ]; then
      FHOST="$FL_LABEL.$DOMAIN"
      curl -skI --resolve "$FHOST:443:127.0.0.1" "https://$FHOST/" -o /root/logs/curl-flower.txt || true
    fi

    # Django admin HEAD (no credentials) -> expect 401/403 when guarded
    ADM_LABEL=$(grep -E '^DJANGO_ADMIN_DNS_LABEL=' /opt/apps/base2/.env | cut -d'=' -f2 | tr -d '\r')
    if [ -n "$ADM_LABEL" ]; then
      AHOST="$ADM_LABEL.$DOMAIN"
      curl -skI --resolve "$AHOST:443:127.0.0.1" "https://$AHOST/" -o /root/logs/curl-admin-head.txt || true
    fi

    # Celery roundtrip: enqueue ping and poll for result
    if [ "${RUN_CELERY_CHECK:-}" = "1" ]; then
      curl -sk -X POST "https://$DOMAIN/api/celery/ping" -H 'Content-Type: application/json' -d '{}' -o /root/logs/celery-ping.json || true
      TASK_ID=$(python3 - <<'PY'
import json,sys
try:
    print(json.load(open('/root/logs/celery-ping.json'))['task_id'])
except Exception:
    print('')
PY
)
      if [ -n "$TASK_ID" ]; then
        for i in $(seq 1 30); do
          curl -sk "https://$DOMAIN/api/celery/result/$TASK_ID" -o /root/logs/celery-result.json || true
          if grep -q '"successful": *true' /root/logs/celery-result.json 2>/dev/null; then
            break
          fi
          sleep 2
        done
      fi
    fi
  fi
  # mark completion
  date -u +"%Y-%m-%dT%H:%M:%SZ" > /root/logs/remote_verify.done || true
fi
'@
  # Ensure Unix LF endings and no BOM for remote bash
  $unixScript = $scriptContent -replace "`r`n","`n"
  Set-Content -Path $tmpScript -Value $unixScript -Encoding Ascii -NoNewline
  # Upload and execute the script
  & $scpExe -i $keyPath @($sshCommon) $tmpScript "root@${ip}:/root/remote_verify.sh" 2>$null | Out-Null
  # Clear previous completion flag to avoid copying stale logs immediately
  try { & $sshExe @sshArgs "rm -f /root/logs/remote_verify.done" | Out-Null } catch { }
  if ($AsyncVerify) {
    if ($RunCeleryCheck) {
      & $sshExe @sshArgs "RUN_CELERY_CHECK=1 nohup bash /root/remote_verify.sh > /root/remote_verify.out 2>&1 & echo \$! > /root/remote_verify.pid" | Out-Null
    } else {
      & $sshExe @sshArgs "nohup bash /root/remote_verify.sh > /root/remote_verify.out 2>&1 & echo \$! > /root/remote_verify.pid" | Out-Null
    }
  } else {
    $timeoutCmd = "if command -v timeout >/dev/null 2>&1; then timeout -k 15s $VerifyTimeoutSec bash /root/remote_verify.sh; else bash /root/remote_verify.sh; fi"
    if ($RunCeleryCheck) {
      & $sshExe @sshArgs "RUN_CELERY_CHECK=1 sh -lc '$timeoutCmd'" | Out-Null
    } else {
      & $sshExe @sshArgs "sh -lc '$timeoutCmd'" | Out-Null
    }
  }

  Write-Section "Copying verification artifacts"
  $dest = Ensure-ArtifactDir

  # Robust copy with polling when async: wait for /root/logs/remote_verify.done, then scp
  $attempts = 1
  if ($AsyncVerify) { $attempts = [Math]::Max(3, [int]$LogsPollMaxAttempts) }
  $interval = [Math]::Max(2, [int]$LogsPollIntervalSec)
  $copied = $false
  for ($i = 1; $i -le $attempts; $i++) {
    try {
      if ($AsyncVerify) {
        $flag = & $sshExe @sshArgs "test -f /root/logs/remote_verify.done && echo DONE || echo WAIT"
        if (-not ($flag -match 'DONE')) {
          Start-Sleep -Seconds $interval
          continue
        }
      }
      # Copy entire remote logs directory (build + services + snapshots)
      & $scpExe -i $keyPath -r "root@${ip}:/root/logs" $dest 2>$null | Out-Null
      $copied = $true
      break
    } catch {
      Start-Sleep -Seconds $interval
    }
  }

  if (-not $copied) {
    Write-Warning "Remote logs not yet available after $attempts attempts; continuing. You can re-run copy later."
  } else {
    # Best-effort copy of individual files to the root of $dest for convenience
    $files = @(
      'compose-ps.txt','traefik-env.txt','traefik-static.yml','traefik-dynamic.yml','traefik-ls.txt','traefik-logs.txt','api-logs.txt',
      'django-migrate.txt',
      'django-check-deploy.txt',
      'schema-compat-check.json','schema-compat-check.err','schema-compat-check.status',
      'published-ports.txt',
      'curl-root.txt','curl-api.txt','curl-api-health.txt','curl-api-health-slash.txt',
      'curl-admin-head.txt',
      'api-health.json','api-health.status','api-health-slash.json','api-health-slash.status',
      'traefik-dynamic.template.yml','traefik-static.template.yml','remote_verify.done'
    )
    foreach ($f in $files) {
      try { & $scpExe -i $keyPath "root@${ip}:/root/logs/$f" $dest 2>$null | Out-Null } catch { }
    }
  }

  # Scrub sensitive material from environment snapshots
  try {
    $traefikEnvPath = Join-Path $dest 'traefik-env.txt'
    if (Test-Path $traefikEnvPath) {
      $raw = Get-Content -Path $traefikEnvPath -Raw
      $patterns = @(
        # Redact common secret env vars in copied artifacts.
        # Include *_PW to catch vars like TRAEFIK_ACTUAL_PW.
        '(?im)^(.*(?:PASS|PASSWORD|SECRET|TOKEN|API_KEY|BASIC_USERS|\bPW\b|_PW\b)[^=]*)=.*$'
      )
      foreach ($pat in $patterns) { $raw = [Regex]::Replace($raw, $pat, '$1=REDACTED') }
      Set-Content -Path $traefikEnvPath -Value $raw -Encoding UTF8
    }
  } catch { Write-Warning "Failed to scrub sensitive values: $($_.Exception.Message)" }

  # Droplet info JSON omitted (optional enhancement; non-critical for verification)

}


Write-Section "Base2 Deploy"
try {
  $null = Ensure-ArtifactDir
  # Provide the orchestrator a per-run artifact directory. It will write DO_userdata.json
  # into this folder during the same run (even before the droplet IP is known).
  try { $env:BASE2_ARTIFACT_DIR = (Ensure-ArtifactDir) } catch {}

  Ensure-Venv
  Activate-Venv
  Load-DotEnv -path $EnvPath
  Assert-EnvNotTracked
  Update-Allowlist
  if ($Preflight) {
    Invoke-Preflight
    Write-Section "Preflight only"
    Write-Output "Preflight passed. No cloud actions executed."
    exit 0
  }
  Validate-DoCreds
  Run-Orchestrator

  $resolvedIp = Get-DropletIp
  if (-not $resolvedIp) {
    Write-Warning "Could not determine droplet IP. Skipping remote verification."
    Write-Section "Remote verify unavailable - saving local artifacts"
    $dest = Ensure-ArtifactDir
    try { $env:BASE2_ARTIFACT_DIR = $dest } catch {}

    # Capture minimal local Compose artifacts for troubleshooting
    try { & docker compose -f ./local.docker.yml ps > (Join-Path $dest 'compose-ps-local.txt') 2>$null } catch {}
    try { & docker compose -f ./local.docker.yml config > (Join-Path $dest 'compose-config-local.yml') 2>$null } catch {}

    $support = @()
    $support += "Remote verification skipped due to missing droplet IP."
    $support += "Ensure DNS points to droplet and DO token is valid."
    $support += "Run: ./scripts/deploy.ps1 -Preflight -RunTests -TestsJson"
    Set-Content -Path (Join-Path $dest 'support.txt') -Value ($support -join [Environment]::NewLine) -Encoding UTF8
    exit 0
  }

  $script:ResolvedIp = $resolvedIp
  $null = Ensure-ArtifactDir -ip $resolvedIp

  Remote-Verify -ip $resolvedIp -keyPath $SshKey
} catch {
  $msg = $_.Exception.Message
  Write-Warning "Deploy failed: $msg"
  Write-FailureArtifacts -context 'exception' -message $msg
  exit 1
}

if ($RunTests) {
  Write-Section "Running post-deploy tests"
  if ($TestsJson) {
    $testArgs = @{ EnvPath = $EnvPath; LogsDir = $LogsDir; UseLatestTimestamp = $true; Json = $true; CheckDjangoAdmin = $true; ResolveIp = $script:ResolvedIp }
    if ($RunRateLimitTest) { $testArgs.CheckRateLimit = $true; $testArgs.RateLimitBurst = $RateLimitBurst }
      if ($RunCeleryCheck) { $testArgs.CheckCelery = $true }
    $jsonOut = & .\scripts\test.ps1 @testArgs
    $exitCode = $LASTEXITCODE
    $artifactDir = Ensure-ArtifactDir
    $reportPath = Join-Path $artifactDir $ReportName
    try {
      Set-Content -Path $reportPath -Value $jsonOut -Encoding UTF8
      Write-Host "Saved JSON report: $reportPath" -ForegroundColor Yellow
    } catch {
      Write-Warning "Failed to write JSON report: $($_.Exception.Message)"
    }
    if ($exitCode -ne 0) { Write-Warning "Post-deploy tests failed"; exit 1 }
  } else {
    $testArgs2 = @{ EnvPath = $EnvPath; LogsDir = $LogsDir; UseLatestTimestamp = $true; CheckDjangoAdmin = $true; ResolveIp = $script:ResolvedIp }
    if ($RunRateLimitTest) { $testArgs2.CheckRateLimit = $true; $testArgs2.RateLimitBurst = $RateLimitBurst }
      if ($RunCeleryCheck) { $testArgs2.CheckCelery = $true }
    & .\scripts\test.ps1 @testArgs2
    if ($LASTEXITCODE -ne 0) { Write-Warning "Post-deploy tests failed"; exit 1 }
  }
}

Write-Section "Done"
$artDir = Ensure-ArtifactDir
Write-Output ("Artifacts saved to: " + $artDir)
