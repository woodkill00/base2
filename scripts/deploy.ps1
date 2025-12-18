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
  return ""
}

function Run-Orchestrator {
  Write-Section "Running orchestrator"
  $args = @()
  if ($Full -and -not $UpdateOnly) {
    # Full provisioning path (default behavior of the script)
  } else {
    $args += '--update-only'
  }
  & .\.venv\Scripts\python.exe .\digital_ocean\orchestrate_deploy.py @args
}

function Remote-Verify($ip, $keyPath) {
  Write-Section "Remote verification on $ip"
  $sshExe = "ssh"
  $scpExe = "scp"
  $sshArgs = @('-i', $keyPath, "root@$ip")
  $remote = @(
    'set -eu',
    'mkdir -p /root/logs',
    # Compose status
    'cd /opt/apps/base2; docker compose -f local.docker.yml ps > /root/logs/compose-ps.txt || true',
    # Traefik config/env
    'docker exec base2_traefik sh -lc "env | sort" > /root/logs/traefik-env.txt || true',
    'docker exec base2_traefik sh -lc "cat /etc/traefik/traefik.yml" > /root/logs/traefik-static.yml || echo MISSING > /root/logs/traefik-static.yml',
    'docker exec base2_traefik sh -lc "cat /etc/traefik/dynamic/dynamic.yml" > /root/logs/traefik-dynamic.yml || echo MISSING > /root/logs/traefik-dynamic.yml',
    # Recent logs
    'docker logs --timestamps --tail=1000 base2_traefik > /root/logs/traefik-logs.txt || true'
  ) -join '; '
  & $sshExe @sshArgs "$remote" | Out-Null

  Write-Section "Copying verification artifacts"
  $outDir = $LogsDir
  if ($Timestamped) {
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $outDir = Join-Path $LogsDir $stamp
  }
  if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }
  $dest = (Resolve-Path $outDir).Path
  $files = @('compose-ps.txt','traefik-env.txt','traefik-static.yml','traefik-dynamic.yml','traefik-logs.txt')
  foreach ($f in $files) {
    & $scpExe -i $keyPath "root@$ip:/root/logs/$f" $dest | Out-Null
  }
}

Write-Section "Base2 Deploy"
Ensure-Venv
Activate-Venv
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
