param(
  [switch]$Full,
  [switch]$UpdateOnly = $true,
  [string]$EnvPath = ".\.env",
  [string]$SshKey = "$env:USERPROFILE\.ssh\base2",
  [string]$DropletIp = "",
  [switch]$SkipAllowlist,
  [string]$LogsDir = ".\local_run_logs",
  [switch]$Timestamped
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
  $ipGuess = & .\\.venv\\Scripts\\python.exe $tmpPy
  if ($LASTEXITCODE -eq 0 -and $ipGuess) { return [string]$ipGuess.Trim() }
  return ""
}

function Run-Orchestrator {
  Write-Section "Running orchestrator"
  $args = @()
    if (-not $Full) { $args += '--update-only' }
  & .\.venv\Scripts\python.exe .\digital_ocean\orchestrate_deploy.py @args
}

function Remote-Verify($ip, $keyPath) {
  Write-Section "Remote verification on $ip"
  $sshExe = "ssh"
  $scpExe = "scp"
  $sshArgs = @('-i', $keyPath, "root@$ip")
  # Create a remote verification script to avoid quoting pitfalls
  $tmpScript = Join-Path $env:TEMP "remote_verify.sh"
  $scriptContent = @'
set -eu
mkdir -p /root/logs
if [ -d /opt/apps/base2 ]; then
  cd /opt/apps/base2
  docker compose -f local.docker.yml ps > /root/logs/compose-ps.txt || true
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
    docker logs --timestamps --tail=1000 "$CID" > /root/logs/traefik-logs.txt || true
  else
    echo "MISSING_CID" | tee /root/logs/traefik-env.txt /root/logs/traefik-static.yml /root/logs/traefik-dynamic.yml /root/logs/traefik-ls.txt /root/logs/traefik-logs.txt >/dev/null
  fi
  DOMAIN=$(grep -E '^WEBSITE_DOMAIN=' /opt/apps/base2/.env | cut -d'=' -f2 | tr -d '\r')
  if [ -n "$DOMAIN" ]; then
    curl -skI "https://$DOMAIN/" -o /root/logs/curl-root.txt || true
    curl -skI "https://$DOMAIN/api/" -o /root/logs/curl-api.txt || true
  fi
fi
'@
  # Ensure Unix LF endings and no BOM for remote bash
  $unixScript = $scriptContent -replace "`r`n","`n"
  Set-Content -Path $tmpScript -Value $unixScript -Encoding Ascii -NoNewline
  # Upload and execute the script
  & $scpExe -i $keyPath $tmpScript "root@${ip}:/root/remote_verify.sh" | Out-Null
  & $sshExe @sshArgs "bash /root/remote_verify.sh" | Out-Null

  Write-Section "Copying verification artifacts"
  $outDir = $LogsDir
  if ($Timestamped) {
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $outDir = Join-Path $LogsDir $stamp
  }
  if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }
  $dest = (Resolve-Path $outDir).Path
  $files = @('compose-ps.txt','traefik-env.txt','traefik-static.yml','traefik-dynamic.yml','traefik-ls.txt','traefik-logs.txt','curl-root.txt','curl-api.txt')
  foreach ($f in $files) {
    & $scpExe -i $keyPath "root@${ip}:/root/logs/$f" $dest | Out-Null
  }

  # Write droplet info JSON into the same timestamped folder
  try {
    $tmpPy = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), 'get_do_details.py')
    $pyCode = @'
import os, json
from pydo import Client

token = os.environ.get('DO_API_TOKEN')
name = os.environ.get('DO_DROPLET_NAME') or 'base2-droplet'
out_path = os.environ.get('OUT_PATH')
result = {
  'name': name,
  'ip_address': None,
  'droplet_id': None,
  'region': None,
  'size': None,
  'image': None,
  'created_at': None,
}
if token:
  try:
    c = Client(token=token)
    resp = c.droplets.list(per_page=200)
    for d in resp.get('droplets', []):
      if d.get('name') == name:
        result['droplet_id'] = d.get('id')
        result['region'] = (d.get('region') or {}).get('slug')
        result['size'] = d.get('size_slug') or (d.get('size') or {}).get('slug')
        result['image'] = (d.get('image') or {}).get('slug')
        result['created_at'] = d.get('created_at')
        for n in d.get('networks', {}).get('v4', []):
          if n.get('type') == 'public':
            result['ip_address'] = n.get('ip_address')
            break
        break
  except Exception:
    pass
try:
  if out_path:
    with open(out_path, 'w', encoding='utf-8') as f:
      json.dump(result, f, indent=2)
except Exception:
  pass
'@
    Set-Content -Path $tmpPy -Value $pyCode -NoNewline
    $outJson = Join-Path $dest 'droplet-info.json'
    $env:OUT_PATH = $outJson
    & .\.venv\Scripts\python.exe $tmpPy | Out-Null
  } catch {}
}

Write-Section "Base2 Deploy"
Ensure-Venv
Activate-Venv
Load-DotEnv -path $EnvPath
Update-Allowlist
Run-Orchestrator

$resolvedIp = Get-DropletIp
if (-not $resolvedIp) {
  Write-Warning "Could not determine droplet IP. Skipping remote verification."
  exit 0
}

Remote-Verify -ip $resolvedIp -keyPath $SshKey

Write-Section "Done"
Write-Host "Artifacts saved to: $(Resolve-Path $LogsDir). Use -Timestamped for per-run subfolders." -ForegroundColor Green
