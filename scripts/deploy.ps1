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

function Write-Section($msg) {
  Write-Host "`n=== $msg ===" -ForegroundColor Cyan
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
  # Capture build and up logs for traefik/django/api
  docker compose -f local.docker.yml build --no-cache traefik > /root/logs/build/traefik-build.txt 2>&1 || true
  docker compose -f local.docker.yml build django > /root/logs/build/django-build.txt 2>&1 || true
  docker compose -f local.docker.yml up -d --force-recreate traefik > /root/logs/build/traefik-up.txt 2>&1 || true
  # Ensure Django service is running for admin route
  docker compose -f local.docker.yml up -d django > /root/logs/build/django-up.txt 2>&1 || true
  # If requested, enable celery/flower profiles and build required images
  if [ "${RUN_CELERY_CHECK:-}" = "1" ]; then
    # Build API (used by Celery worker image) if present; ignore if missing
    docker compose -f local.docker.yml build api > /root/logs/build/api-build.txt 2>&1 || true
    # Start Redis, Celery worker and beat under the celery profile; ignore if services not defined
    docker compose -f local.docker.yml --profile celery up -d redis celery-worker celery-beat > /root/logs/build/celery-up.txt 2>&1 || true
    # Start Flower if defined (separate profile)
    docker compose -f local.docker.yml --profile flower up -d flower > /root/logs/build/flower-up.txt 2>&1 || true
  fi
  docker compose -f local.docker.yml ps > /root/logs/compose-ps.txt || true
  docker compose -f local.docker.yml config > /root/logs/compose-config.yml || true
  # Capture logs from all services
  SERVICES=$(docker compose -f local.docker.yml config --services || true)
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
    # Capture backend logs for diagnostics if needed
    BID=$(docker compose -f local.docker.yml ps -q backend || true)
    if [ -n "$BID" ]; then
      docker logs --timestamps --tail=500 "$BID" > /root/logs/backend-logs.txt || true
    else
      echo "MISSING_BACKEND_CID" > /root/logs/backend-logs.txt
    fi
  else
    echo "MISSING_CID" | tee /root/logs/traefik-env.txt /root/logs/traefik-static.yml /root/logs/traefik-dynamic.yml /root/logs/traefik-ls.txt /root/logs/traefik-logs.txt >/dev/null
  fi
  DOMAIN=$(grep -E '^WEBSITE_DOMAIN=' /opt/apps/base2/.env | cut -d'=' -f2 | tr -d '\r')
  if [ -n "$DOMAIN" ]; then
    # Root HEAD
    curl -skI "https://$DOMAIN/" -o /root/logs/curl-root.txt || true

    # API health HEAD (both forms)
    curl -skI "https://$DOMAIN/api/health" -o /root/logs/curl-api-health.txt || true
    curl -skI "https://$DOMAIN/api/health/" -o /root/logs/curl-api-health-slash.txt || true

    # API health GET (capture body and status separately)
    curl -sk -o /root/logs/api-health.json -w "%{http_code}" "https://$DOMAIN/api/health" > /root/logs/api-health.status || true
    curl -sk -o /root/logs/api-health-slash.json -w "%{http_code}" "https://$DOMAIN/api/health/" > /root/logs/api-health-slash.status || true

    # Back-compat: maintain curl-api.txt pointing at preferred health endpoint (non-slash first)
    cp /root/logs/curl-api-health.txt /root/logs/curl-api.txt || true
    if ! grep -q '^HTTP/.* 200' /root/logs/curl-api.txt 2>/dev/null; then
      cp /root/logs/curl-api-health-slash.txt /root/logs/curl-api.txt || true
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
  & $scpExe -i $keyPath @($sshCommon) $tmpScript "root@${ip}:/root/remote_verify.sh" | Out-Null
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
  $outDir = $LogsDir
  if ($Timestamped) {
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $outDir = Join-Path $LogsDir $stamp
  }
  if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }
  $dest = (Resolve-Path $outDir).Path

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
      & $scpExe -i $keyPath -r "root@${ip}:/root/logs" $dest | Out-Null
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
      'compose-ps.txt','traefik-env.txt','traefik-static.yml','traefik-dynamic.yml','traefik-ls.txt','traefik-logs.txt','backend-logs.txt',
      'curl-root.txt','curl-api.txt','curl-api-health.txt','curl-api-health-slash.txt',
      'api-health.json','api-health.status','api-health-slash.json','api-health-slash.status',
      'traefik-dynamic.template.yml','traefik-static.template.yml','remote_verify.done'
    )
    foreach ($f in $files) {
      try { & $scpExe -i $keyPath "root@${ip}:/root/logs/$f" $dest | Out-Null } catch { }
    }
  }

  # Scrub sensitive material from environment snapshots
  try {
    $traefikEnvPath = Join-Path $dest 'traefik-env.txt'
    if (Test-Path $traefikEnvPath) {
      $raw = Get-Content -Path $traefikEnvPath -Raw
      $patterns = @(
        '(?im)^(.*(?:PASS|PASSWORD|SECRET|TOKEN|API_KEY|BASIC_USERS)[^=]*)=.*$'
      )
      foreach ($pat in $patterns) { $raw = [Regex]::Replace($raw, $pat, '$1=REDACTED') }
      Set-Content -Path $traefikEnvPath -Value $raw -Encoding UTF8
    }
  } catch { Write-Warning "Failed to scrub sensitive values: $($_.Exception.Message)" }

  # Droplet info JSON omitted (optional enhancement; non-critical for verification)

}


Write-Section "Base2 Deploy"
Ensure-Venv
Activate-Venv
Load-DotEnv -path $EnvPath
Update-Allowlist
if ($Preflight) { Invoke-Preflight }
Validate-DoCreds
Run-Orchestrator

$resolvedIp = Get-DropletIp
if (-not $resolvedIp) {
  Write-Warning "Could not determine droplet IP. Skipping remote verification."
  Write-Section "Remote verify unavailable - saving local artifacts"
  $outDir = $LogsDir
  if ($Timestamped) {
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $outDir = Join-Path $LogsDir $stamp
  }
  if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }
  $dest = (Resolve-Path $outDir).Path
  $support = @()
  $support += "Remote verification skipped due to missing droplet IP."
  $support += "Ensure DNS points to droplet and DO token is valid."
  $support += "Run: ./scripts/deploy.ps1 -Preflight -RunTests -TestsJson"
  $text = ($support -join [Environment]::NewLine)
  Set-Content -Path (Join-Path $dest 'support.txt') -Value $text -Encoding UTF8
  exit 0
}

Remote-Verify -ip $resolvedIp -keyPath $SshKey

if ($RunTests) {
  Write-Section "Running post-deploy tests"
  if ($TestsJson) {
    $testArgs = @{ EnvPath = $EnvPath; LogsDir = $LogsDir; UseLatestTimestamp = $true; Json = $true; CheckDjangoAdmin = $true }
    if ($RunRateLimitTest) { $testArgs.CheckRateLimit = $true; $testArgs.RateLimitBurst = $RateLimitBurst }
      if ($RunCeleryCheck) { $testArgs.CheckCelery = $true }
    $jsonOut = & .\scripts\test.ps1 @testArgs
    $exitCode = $LASTEXITCODE
    # Determine latest timestamped artifact folder
    $artifactDir = $LogsDir
    if (Test-Path $LogsDir) {
      $cands = Get-ChildItem -Path $LogsDir -Directory | Where-Object { $_.Name -match '^\d{8}_\d{6}$' } | Sort-Object Name
      if ($cands.Count -gt 0) { $artifactDir = $cands[-1].FullName }
    }
    $reportPath = Join-Path $artifactDir $ReportName
    try {
      Set-Content -Path $reportPath -Value $jsonOut -Encoding UTF8
      Write-Host "Saved JSON report: $reportPath" -ForegroundColor Yellow
    } catch {
      Write-Warning "Failed to write JSON report: $($_.Exception.Message)"
    }
    if ($exitCode -ne 0) { Write-Warning "Post-deploy tests failed"; exit 1 }
  } else {
    $testArgs2 = @{ EnvPath = $EnvPath; LogsDir = $LogsDir; UseLatestTimestamp = $true; CheckDjangoAdmin = $true }
    if ($RunRateLimitTest) { $testArgs2.CheckRateLimit = $true; $testArgs2.RateLimitBurst = $RateLimitBurst }
      if ($RunCeleryCheck) { $testArgs2.CheckCelery = $true }
    & .\scripts\test.ps1 @testArgs2
    if ($LASTEXITCODE -ne 0) { Write-Warning "Post-deploy tests failed"; exit 1 }
  }
}

Write-Section "Done"
$artDir = (Resolve-Path $LogsDir)
Write-Output ("Artifacts saved to: " + $artDir + ". Use -Timestamped for per-run subfolders.")
