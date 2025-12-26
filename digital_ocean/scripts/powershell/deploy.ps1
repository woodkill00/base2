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
  [switch]$AllTests,
  [switch]$TestsJson,
  [switch]$RunRateLimitTest,
  [switch]$RunCeleryCheck,
  [int]$RateLimitBurst = 20,
  # Remote verification can include container rebuilds and test runs; 10 minutes is often too low.
  [int]$VerifyTimeoutSec = 1800,
  [switch]$AsyncVerify,
  [int]$LogsPollMaxAttempts = 30,
  [int]$LogsPollIntervalSec = 10,
  [string]$ReportName = 'post-deploy-report.json'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Ensure relative paths work regardless of where the script is invoked from.
$script:RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
Push-Location $script:RepoRoot

$script:ArtifactDir = ''
$script:ResolvedIp = ''
$script:RunStamp = (Get-Date -Format 'yyyyMMdd_HHmmss')
$script:TranscriptStarted = $false
$script:ExitCode = 0
$script:EarlyExitSentinel = '__BASE2_EARLY_EXIT__'
$script:PendingArtifactRenameTo = ''

function Write-Section($msg) {
  Write-Host "`n=== $msg ===" -ForegroundColor Cyan
}

function Get-UtcTimestamp {
  # Windows PowerShell 5.1 doesn't support Get-Date -AsUTC.
  return (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
}

function Get-ArtifactServiceSubdir([string]$fileName) {
  # Map known artifact files to per-service folders.
  # Keep meta files (deploy-console.log, post-deploy-report.json, etc.) under meta/.
  switch -Regex ($fileName) {
    '^DO_userdata\.json$' { return 'digital_ocean' }

    '^compose-ps\.txt$' { return 'docker' }
    '^compose-config\.yml$' { return 'docker' }
    '^published-ports\.txt$' { return 'docker' }

    '^remote_verify\.done$' { return 'meta' }
    '^post-deploy-report\.json$' { return 'meta' }
    '^deploy-mode\.json$' { return 'meta' }

    '^manual-test-out\.json$' { return 'meta' }

    '^traefik-.*\.yml$' { return 'traefik' }
    '^traefik-.*\.template\.yml$' { return 'traefik' }
    '^traefik-.*\.txt$' { return 'traefik' }

    '^django-.*\.txt$' { return 'django' }

    '^api-logs\.txt$' { return 'api' }
    '^api-.*\.txt$' { return 'api' }
    '^api-health(\-slash)?\.(json|status)$' { return 'api' }

    '^curl-.*\.txt$' { return 'smoke' }

    '^schema-compat-check\.(json|err|status)$' { return 'database' }

    '^celery-(ping|result)\.json$' { return 'celery' }

    '^env-dollar-check\.(txt|status)$' { return 'meta' }
    default { return '' }
  }
}

function Get-ServiceFolderForServiceLog([string]$logFileName) {
  # Map /root/logs/services/<service>.log to top-level per-service folders.
  $serviceName = [System.IO.Path]::GetFileNameWithoutExtension($logFileName)
  switch -Regex ($serviceName) {
    '^traefik$' { return 'traefik' }
    '^nginx$' { return 'nginx' }
    '^nginx-static$' { return 'nginx' }
    '^django$' { return 'django' }
    '^api$' { return 'api' }
    '^postgres$' { return 'database' }
    '^redis$' { return 'database' }
    '^pgadmin$' { return 'database' }
    '^(celery-worker|celery-beat|flower)$' { return 'celery' }
    '^react-app$' { return 'react-app' }
    default { return '' }
  }
}

function Resolve-ArtifactFilePath([string]$artifactDir, [string]$fileName) {
  # Look for a file in the root, then in the service folder, then in legacy subfolders.
  $candidates = @()
  $candidates += (Join-Path $artifactDir $fileName)

  $sub = Get-ArtifactServiceSubdir -fileName $fileName
  if ($sub) { $candidates += (Join-Path (Join-Path $artifactDir $sub) $fileName) }

  # Current layout (renamed from logs/)
  $candidates += (Join-Path (Join-Path $artifactDir 'container_logs') $fileName)
  $candidates += (Join-Path (Join-Path (Join-Path $artifactDir 'container_logs') 'build') $fileName)

  # Legacy paths from older implementations
  $candidates += (Join-Path (Join-Path $artifactDir 'logs') $fileName)
  $candidates += (Join-Path (Join-Path (Join-Path $artifactDir 'logs') 'build') $fileName)

  foreach ($p in $candidates) {
    if (Test-Path $p) { return $p }
  }
  return ''
}

function Organize-ArtifactsByService {
  # Move known artifacts from the run root into per-service folders.
  # Rename logs/ -> container_logs/ and keep container_logs clean (only build/ and services/).
  # Copy per-container service logs (container_logs/services/*.log) into their matching top-level service folder.
  try {
    $dest = Ensure-ArtifactDir
    if (-not (Test-Path $dest)) { return }

    # Rename logs -> container_logs (best effort; preserve backward compat).
    $logsDir = Join-Path $dest 'logs'
    $containerLogsDir = Join-Path $dest 'container_logs'
    try {
      if ((-not (Test-Path $containerLogsDir)) -and (Test-Path $logsDir)) {
        Rename-Item -LiteralPath $logsDir -NewName 'container_logs' -Force
      }
    } catch {}

    $files = @(Get-ChildItem -LiteralPath $dest -File -ErrorAction Stop)
    foreach ($f in $files) {
      $sub = Get-ArtifactServiceSubdir -fileName $f.Name
      if (-not $sub) { continue }

      $targetDir = Join-Path $dest $sub
      if (-not (Test-Path $targetDir)) { New-Item -ItemType Directory -Path $targetDir -Force | Out-Null }
      $targetPath = Join-Path $targetDir $f.Name
      try {
        Move-Item -LiteralPath $f.FullName -Destination $targetPath -Force
      } catch {}
    }

    # Copy service logs into their service folder for convenience.
    try {
      $containerLogsDir = Join-Path $dest 'container_logs'
      $svcDir = Join-Path $containerLogsDir 'services'
      if (Test-Path $svcDir) {
        $svcLogs = @(Get-ChildItem -LiteralPath $svcDir -File -Filter '*.log' -ErrorAction Stop)
        foreach ($lf in $svcLogs) {
          $svcSub = Get-ServiceFolderForServiceLog -logFileName $lf.Name
          if (-not $svcSub) { continue }
          $targetDir = Join-Path $dest $svcSub
          if (-not (Test-Path $targetDir)) { New-Item -ItemType Directory -Path $targetDir -Force | Out-Null }
          $targetPath = Join-Path $targetDir $lf.Name
          try { Copy-Item -LiteralPath $lf.FullName -Destination $targetPath -Force } catch {}
        }
      }
    } catch {}

    # Keep container_logs/ clean: only build/ and services/ remain.
    # Anything else is moved into its mapped service folder (or meta/ if unknown).
    try {
      $containerLogsDir = Join-Path $dest 'container_logs'
      if (Test-Path $containerLogsDir) {
        $children = @(Get-ChildItem -LiteralPath $containerLogsDir -Force -ErrorAction Stop)
        foreach ($c in $children) {
          if ($c.Name -in @('build','services')) { continue }

          $sub = Get-ArtifactServiceSubdir -fileName $c.Name
          if (-not $sub) { $sub = 'meta' }

          $targetDir = Join-Path $dest $sub
          if (-not (Test-Path $targetDir)) { New-Item -ItemType Directory -Path $targetDir -Force | Out-Null }

          $targetPath = Join-Path $targetDir $c.Name
          try {
            Move-Item -LiteralPath $c.FullName -Destination $targetPath -Force
          } catch {
            # If move fails (e.g., cross-device or locked), try copy then delete.
            try {
              if ($c.PSIsContainer) {
                Copy-Item -LiteralPath $c.FullName -Destination $targetPath -Recurse -Force
                Remove-Item -LiteralPath $c.FullName -Recurse -Force
              } else {
                Copy-Item -LiteralPath $c.FullName -Destination $targetPath -Force
                Remove-Item -LiteralPath $c.FullName -Force
              }
            } catch {}
          }
        }
      }
    } catch {}
  } catch {}
}

function Start-DeployTranscript {
  $dest = Ensure-ArtifactDir
  $path = Join-Path $dest 'deploy-console.log'
  try {
    if (-not $script:TranscriptStarted) {
      Start-Transcript -Path $path -Append | Out-Null
      $script:TranscriptStarted = $true
    }
  } catch {
    # Non-fatal: transcript can fail in some hosts.
    $script:TranscriptStarted = $false
  }
}

function Stop-DeployTranscript {
  try {
    if ($script:TranscriptStarted) {
      Stop-Transcript | Out-Null
      $script:TranscriptStarted = $false
    }
  } catch {}
}

function Finalize-ArtifactDirRename {
  # If we had to defer unknown-* -> <ip>-* rename because transcript had the folder locked,
  # attempt it once after Stop-Transcript.
  try {
    if (-not $script:PendingArtifactRenameTo) { return }
    if (-not $script:ArtifactDir) { return }
    if (-not (Test-Path $script:ArtifactDir)) { return }
    if (Test-Path $script:PendingArtifactRenameTo) {
      $script:PendingArtifactRenameTo = ''
      return
    }
    Move-Item -Path $script:ArtifactDir -Destination $script:PendingArtifactRenameTo -Force
    $script:ArtifactDir = (Resolve-Path $script:PendingArtifactRenameTo).Path
    try { $env:BASE2_ARTIFACT_DIR = $script:ArtifactDir } catch {}
  } catch {}
  finally {
    $script:PendingArtifactRenameTo = ''
  }
}

function Append-RemoteArtifactsToConsoleLog {
  # Start-Transcript captures local console output. Remote verification artifacts are usually copied,
  # not printed. Append a curated set into deploy-console.log for one-stop review.
  try {
    $dest = Ensure-ArtifactDir
    $logPath = Join-Path $dest 'deploy-console.log'
    if (-not (Test-Path $logPath)) { return }

    $safeFiles = @(
      'compose-ps.txt','published-ports.txt',
      'traefik-static.yml','traefik-dynamic.yml','traefik-ls.txt','traefik-logs.txt','traefik-env.txt',
      'api-logs.txt','django-migrate.txt','django-check-deploy.txt',
      'curl-root.txt','curl-api.txt','curl-api-health.txt','curl-api-health-slash.txt','curl-admin-head.txt',
      'api-health.json','api-health.status','api-health-slash.json','api-health-slash.status',
      'schema-compat-check.json','schema-compat-check.err','schema-compat-check.status',
      'env-dollar-check.txt','env-dollar-check.status'
    )

    $sb = New-Object System.Text.StringBuilder
    $null = $sb.AppendLine('')
    $null = $sb.AppendLine('===== BEGIN APPENDED REMOTE ARTIFACTS =====')
    $null = $sb.AppendLine(('Time (UTC): ' + (Get-UtcTimestamp)))
    $null = $sb.AppendLine('Note: This section is appended locally from downloaded /root/logs artifacts.')
    foreach ($name in $safeFiles) {
      $path = Resolve-ArtifactFilePath -artifactDir $dest -fileName $name
      if (-not $path) { continue }

      $null = $sb.AppendLine('')
      $null = $sb.AppendLine(('----- FILE: ' + $name + ' -----'))

      try {
        $item = Get-Item -LiteralPath $path -ErrorAction Stop
        # Avoid exploding the console log; include full content for small files, tail for large.
        if ($item.Length -le 200000) {
          $null = $sb.AppendLine((Get-Content -LiteralPath $path -Raw -ErrorAction Stop))
        } else {
          $null = $sb.AppendLine(('(file is large: ' + $item.Length + ' bytes)'))
          $null = $sb.AppendLine('--- last 400 lines ---')
          $null = $sb.AppendLine((Get-Content -LiteralPath $path -Tail 400 -ErrorAction Stop | Out-String))
        }
      } catch {
        $null = $sb.AppendLine(('(failed to read file: ' + $_.Exception.Message + ')'))
      }
    }
    $null = $sb.AppendLine('===== END APPENDED REMOTE ARTIFACTS =====')

    Add-Content -LiteralPath $logPath -Value $sb.ToString() -Encoding UTF8
  } catch {}
}

function Write-RemoteArtifactsBundle {
  # Always write a separate file containing key droplet artifacts/logs.
  # This avoids relying on Start-Transcript (which only captures local console output).
  try {
    $dest = Ensure-ArtifactDir
    $outPath = Join-Path $dest 'deploy-remote-artifacts.log'

    $safeFiles = @(
      'compose-ps.txt','published-ports.txt',
      'traefik-static.yml','traefik-dynamic.yml','traefik-ls.txt','traefik-logs.txt','traefik-env.txt',
      'api-logs.txt','django-migrate.txt','django-check-deploy.txt',
      'curl-root.txt','curl-api.txt','curl-api-health.txt','curl-api-health-slash.txt','curl-admin-head.txt',
      'api-health.json','api-health.status','api-health-slash.json','api-health-slash.status',
      'schema-compat-check.json','schema-compat-check.err','schema-compat-check.status',
      'env-dollar-check.txt','env-dollar-check.status'
    )

    $sb = New-Object System.Text.StringBuilder
    $null = $sb.AppendLine('===== REMOTE ARTIFACTS BUNDLE =====')
    $null = $sb.AppendLine(('Time (UTC): ' + (Get-UtcTimestamp)))
    $null = $sb.AppendLine('Source: downloaded /root/logs artifacts from droplet')

    foreach ($name in $safeFiles) {
      $path = Resolve-ArtifactFilePath -artifactDir $dest -fileName $name
      if (-not $path) { continue }

      $null = $sb.AppendLine('')
      $null = $sb.AppendLine(('----- FILE: ' + $name + ' -----'))
      try {
        $item = Get-Item -LiteralPath $path -ErrorAction Stop
        if ($item.Length -le 500000) {
          $null = $sb.AppendLine((Get-Content -LiteralPath $path -Raw -ErrorAction Stop))
        } else {
          $null = $sb.AppendLine(('(file is large: ' + $item.Length + ' bytes)'))
          $null = $sb.AppendLine('--- last 800 lines ---')
          $null = $sb.AppendLine((Get-Content -LiteralPath $path -Tail 800 -ErrorAction Stop | Out-String))
        }
      } catch {
        $null = $sb.AppendLine(('(failed to read file: ' + $_.Exception.Message + ')'))
      }
    }

    Set-Content -LiteralPath $outPath -Value $sb.ToString() -Encoding UTF8
  } catch {}
}

function Switch-TranscriptToResolvedArtifactDir([string]$ip) {
  # If the transcript is writing into unknown-<timestamp>, that folder cannot be renamed.
  # Stop the transcript, rename the folder, then restart the transcript in the new folder.
  try {
    if (-not $ip -or -not $ip.Trim()) { return }
    if (-not $script:TranscriptStarted) {
      $null = Ensure-ArtifactDir -ip $ip
      return
    }

    Stop-DeployTranscript
    $null = Ensure-ArtifactDir -ip $ip
    Start-DeployTranscript
  } catch {
    # Non-fatal; deploy can continue even if transcript switching fails.
    try { Start-DeployTranscript } catch {}
  }
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
          if ($script:TranscriptStarted) {
            # Transcript holds an open file handle inside the folder. Defer rename until transcript stops.
            $script:PendingArtifactRenameTo = $targetDir
          } else {
            Move-Item -Path $script:ArtifactDir -Destination $targetDir -Force
            $script:ArtifactDir = (Resolve-Path $targetDir).Path
          }
        } else {
          # If target exists, keep current dir to avoid clobber.
          $script:ArtifactDir = (Resolve-Path $script:ArtifactDir).Path
        }
      }
    } catch {}
    try { $env:BASE2_ARTIFACT_DIR = [string]$script:ArtifactDir } catch {}
    return $script:ArtifactDir
  }

  if (-not (Test-Path $targetDir)) { New-Item -ItemType Directory -Path $targetDir -Force | Out-Null }
  $script:ArtifactDir = (Resolve-Path $targetDir).Path
  try { $env:BASE2_ARTIFACT_DIR = [string]$script:ArtifactDir } catch {}
  return $script:ArtifactDir
}

function Write-FailureArtifacts([string]$context, [string]$message) {
  $dest = Ensure-ArtifactDir
  try {
    $support = @()
    $support += "Deploy failed: $context"
    $support += "Message: $message"
    $support += "Time (UTC): $(Get-UtcTimestamp)"
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
    # In Windows PowerShell 5.1, piping native output (even to Out-Null) can raise
    # "The pipeline has been stopped". Avoid pipelines; rely on exit codes instead.
    # Avoid `git ls-files --error-unmatch` because it can emit a terminating error record
    # under strict error settings. Use output presence to detect tracking, without pipelines.
    $tracked = & git ls-files .env 2>$null
    if ($tracked) {
      throw ".env is tracked by git. Fix by running: git rm --cached .env (and commit), ensure .gitignore includes .env, then re-run deploy."
    }
    $LASTEXITCODE = 0
  } catch {
    # If git isn't available or check fails in a non-fatal way, don't block deploy.
    try { $LASTEXITCODE = 0 } catch {}
  }
}

function Update-Allowlist {
  if ($SkipAllowlist) { return }
  Write-Section "Updating pgAdmin IP allowlist in .env"
  & .\digital_ocean\scripts\powershell\update-pgadmin-allowlist.ps1 -EnvPath $EnvPath
}

function Invoke-Preflight {
  Write-Section "Preflight validation"
  # Runs strict validation of .env, compose labels/ports, and required files.
  # Fails fast on any issue to prevent orchestration.
  & .\digital_ocean\scripts\powershell\validate-predeploy.ps1 -Strict
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

  # Prefer per-run artifacts over workspace-root files.
  $artifactDir = ''
  try {
    if ($env:BASE2_ARTIFACT_DIR) { $artifactDir = [string]$env:BASE2_ARTIFACT_DIR }
    elseif ($script:ArtifactDir) { $artifactDir = [string]$script:ArtifactDir }
    else { $artifactDir = Ensure-ArtifactDir }
  } catch {}

  if ($artifactDir) {
    $udFile = Resolve-ArtifactFilePath -artifactDir $artifactDir -fileName 'DO_userdata.json'
    if ($udFile -and (Test-Path $udFile)) {
      try {
        $json = Get-Content $udFile -Raw | ConvertFrom-Json
        if ($json.ip_address) { return [string]$json.ip_address }
      } catch { }
    }
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
  & .\.venv\Scripts\python.exe .\digital_ocean\scripts\python\orchestrate_deploy.py @cliArgs
}

function Remote-Verify($ip, $keyPath) {
  Write-Section "Remote verification on $ip"
  $null = Ensure-ArtifactDir -ip $ip
  $sshExe = "ssh"
  $scpExe = "scp"
  # Be resilient to transient SSH/SCP handshake slowness; OpenSSH on Windows sometimes hits
  # "Connection timed out during banner exchange" on busy or briefly unreachable hosts.
  $sshCommon = @(
    '-o','ConnectTimeout=60',
    '-o','ConnectionAttempts=3',
    '-o','ServerAliveInterval=15',
    '-o','ServerAliveCountMax=4',
    '-o','StrictHostKeyChecking=no',
    '-o','BatchMode=yes'
  )
  $sshArgs = @('-i', $keyPath) + $sshCommon + @("root@$ip")
  $prevEap = $ErrorActionPreference
  try {
    $ErrorActionPreference = 'Continue'

  # Ensure droplet has the current local .env so docker compose has required variables.
  $localEnvPath = ''
  try {
    if (-not (Test-Path $EnvPath)) { throw "Env file not found: $EnvPath" }
    $localEnvPath = (Resolve-Path $EnvPath).Path
  } catch {
    throw "Unable to resolve EnvPath '$EnvPath': $($_.Exception.Message)"
  }
  # Ensure repo directory exists (user_data should create it, but be defensive)
  & $sshExe @sshArgs "mkdir -p /opt/apps/base2" *> $null
  if ($LASTEXITCODE -ne 0) { throw "Failed to create /opt/apps/base2 on droplet (ssh exit $LASTEXITCODE)" }
  # Upload .env (secrets) to droplet repo root
  & $scpExe -i $keyPath @($sshCommon) $localEnvPath "root@${ip}:/opt/apps/base2/.env" *> $null
  if ($LASTEXITCODE -ne 0) { throw "Failed to upload .env to droplet (scp exit $LASTEXITCODE)" }

  # Create a remote verification script to avoid quoting pitfalls
  $tmpScript = Join-Path $env:TEMP "remote_verify.sh"
  $scriptContent = @'
set -eu
mkdir -p /root/logs
if [ -d /opt/apps/base2 ]; then
  cd /opt/apps/base2
  # Prepare log directories; clear stale artifacts from previous runs.
  rm -rf /root/logs/* || true
  mkdir -p /root/logs/build /root/logs/services /root/logs/meta || true
  # Prevent noisy stdout/stderr (git, docker build progress) from flowing back over SSH.
  # Windows PowerShell 5.1 can treat remote stderr as terminating errors under strict settings.
  exec > /root/logs/build/remote-verify-console.txt 2>&1
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
  set +e
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
  STATUS=$?
  set -e
  echo $STATUS > /root/logs/build/env-dollar-check.status || true
  # IMPORTANT: We have observed Docker caching causing stale FastAPI code to persist across
  # UpdateOnly deploys. Use a targeted no-cache rebuild for the `api` service to ensure the
  # running container matches the git checkout (keeps overall verification time reasonable).
  docker compose -f local.docker.yml build --no-cache api > /root/logs/build/api-build-nocache.txt 2>&1 || true

  # Bring up services. `up --build` is generally sufficient to rebuild when inputs change.
  # Bring up core services needed for edge routing (avoid 502 due to missing upstreams)
  # Also start Celery worker/beat by default (Option A: no profile gating).
  docker compose -f local.docker.yml up -d --build --remove-orphans postgres django api react-app nginx nginx-static traefik redis pgadmin flower celery-worker celery-beat > /root/logs/build/compose-up-core.txt 2>&1 || true
  # Ensure API container uses the freshly built image
  docker compose -f local.docker.yml up -d --build --force-recreate --no-deps api > /root/logs/build/api-up.txt 2>&1 || true
  docker compose -f local.docker.yml up -d --build --force-recreate --no-deps traefik > /root/logs/build/traefik-up.txt 2>&1 || true

  # Ensure Flower is started (kept as a separate log artifact)
  docker compose -f local.docker.yml up -d --build flower > /root/logs/build/flower-up.txt 2>&1 || true

  # Ensure Django service is running for admin route
  docker compose -f local.docker.yml up -d --build django > /root/logs/build/django-up.txt 2>&1 || true
  # Capture Django migration output into a dedicated artifact
  docker compose -f local.docker.yml exec -T django python manage.py migrate --noinput > /root/logs/django-migrate.txt 2>&1 || true
  # Django deploy checks (security + config sanity)
  docker compose -f local.docker.yml exec -T django python manage.py check --deploy > /root/logs/django-check-deploy.txt 2>&1 || true
  # Django internal HTTP health (avoid probing admin HTML); capture JSON body + HTTP status
  docker compose -f local.docker.yml exec -T django python - <<'PY' > /root/logs/django-internal-health.json 2> /root/logs/django-internal-health.status || true
import json
import os
import sys
from urllib.error import HTTPError
from urllib.request import urlopen

port = os.environ.get("PORT") or "8000"
url = f"http://127.0.0.1:{port}/internal/health"
status = 0
body = "{}"

try:
    with urlopen(url, timeout=5) as resp:
        status = getattr(resp, "status", None) or resp.getcode() or 200
        body = resp.read().decode("utf-8")
except HTTPError as e:
    status = e.code
    try:
        body = e.read().decode("utf-8")
    except Exception:
        body = json.dumps({"ok": False, "service": "django", "db_ok": False})
except Exception as e:
    status = 0
    body = json.dumps({"ok": False, "service": "django", "db_ok": False, "error": str(e)})

sys.stdout.write(body)
sys.stderr.write(str(status))
PY
  # Schema compatibility check (fails if migrations unapplied or schema drift)
  set +e
  docker compose -f local.docker.yml exec -T django python manage.py schema_compat_check --json > /root/logs/schema-compat-check.json 2> /root/logs/schema-compat-check.err
  echo $? > /root/logs/schema-compat-check.status
  set -e
  # If requested, enable celery/flower profiles and build required images
  if [ "${RUN_CELERY_CHECK:-}" = "1" ]; then
    # Tune host sysctl for Redis memory overcommit (best-effort, ignore errors)
    (sysctl -w vm.overcommit_memory=1 && echo 'vm.overcommit_memory=1' > /etc/sysctl.d/99-redis.conf && sysctl --system) || true
    # Build Celery services (Django-based) if present; ignore if missing
    docker compose -f local.docker.yml build celery-worker > /root/logs/build/celery-worker-build.txt 2>&1 || true
    docker compose -f local.docker.yml build celery-beat > /root/logs/build/celery-beat-build.txt 2>&1 || true
    # Start Redis, Celery worker and beat under the celery profile; ignore if services not defined
    docker compose -f local.docker.yml --profile celery up -d --build redis celery-worker celery-beat > /root/logs/build/celery-up.txt 2>&1 || true
    # Start Flower if defined
    docker compose -f local.docker.yml up -d --build flower > /root/logs/build/flower-up.txt 2>&1 || true
  fi
  # Best-effort: wait for key services to report healthy before snapshotting.
  # This reduces false negatives where compose-ps.txt is captured during startup.
  set +e
  : > /root/logs/build/health-wait.txt || true
  for i in $(seq 1 60); do
    PS_OUT=$(docker compose -f local.docker.yml ps 2>/dev/null)
    echo "--- attempt $i ---" >> /root/logs/build/health-wait.txt
    echo "$PS_OUT" >> /root/logs/build/health-wait.txt
    OK=1
    for s in traefik nginx nginx-static django api postgres redis react-app celery-worker celery-beat flower; do
      echo "$PS_OUT" | grep -E "\s${s}\s" >/dev/null 2>&1 || { OK=0; break; }
      echo "$PS_OUT" | grep -E "\s${s}\s.*\(healthy\)" >/dev/null 2>&1 || { OK=0; break; }
    done
    if [ "$OK" = "1" ]; then
      echo "READY" >> /root/logs/build/health-wait.txt
      break
    fi
    sleep 2
  done
  set -e

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
    OUT="/root/logs/services/${s}.log"
    echo "===== SERVICE LOG: ${s} =====" > "$OUT" || true
    echo "Time: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$OUT" || true

    # If the service isn't running (e.g., profiled services like celery-*), record that explicitly.
    CIDS=$(docker compose -f local.docker.yml ps -q "$s" 2>/dev/null || true)
    if [ -z "$CIDS" ]; then
      echo "NOTE: No running containers found for service '$s'." >> "$OUT" || true
      echo "      If this is a profiled service (e.g., celery), ensure the profile is enabled." >> "$OUT" || true
      continue
    fi

    # Prefer docker logs for exact container output.
    for cid in $CIDS; do
      echo "" >> "$OUT" || true
      echo "--- docker logs (cid=$cid) ---" >> "$OUT" || true
      docker logs --timestamps --tail=2000 "$cid" >> "$OUT" 2>&1 || true
    done

    # Also include compose logs as a fallback/aggregate view.
    echo "" >> "$OUT" || true
    echo "--- docker compose logs (service=$s) ---" >> "$OUT" || true
    docker compose -f local.docker.yml logs --no-color --timestamps --tail=2000 "$s" >> "$OUT" 2>&1 || true
  done

  # Some services may log primarily to files inside the container/volume.
  # Traefik: try /var/log/traefik/*
  TID=$(docker compose -f local.docker.yml ps -q traefik 2>/dev/null || true)
  if [ -n "$TID" ]; then
    OUT="/root/logs/services/traefik.log"
    echo "" >> "$OUT" || true
    echo "--- /var/log/traefik (file-based logs) ---" >> "$OUT" || true
    docker exec "$TID" sh -lc 'ls -la /var/log/traefik 2>/dev/null || true; for f in /var/log/traefik/*; do [ -f "$f" ] || continue; echo "\n----- $f -----"; tail -n 2000 "$f" || true; done' >> "$OUT" 2>&1 || true
  fi

  # Nginx: try /var/log/nginx/*
  NID=$(docker compose -f local.docker.yml ps -q nginx 2>/dev/null || true)
  if [ -n "$NID" ]; then
    OUT="/root/logs/services/nginx.log"
    echo "" >> "$OUT" || true
    echo "--- /var/log/nginx (file-based logs) ---" >> "$OUT" || true
    docker exec "$NID" sh -lc 'ls -la /var/log/nginx 2>/dev/null || true; for f in /var/log/nginx/*; do [ -f "$f" ] || continue; echo "\n----- $f -----"; tail -n 2000 "$f" || true; done' >> "$OUT" 2>&1 || true
  fi

  # Nginx-static: try /var/log/nginx/* (image-based static nginx may log to files)
  NSID=$(docker compose -f local.docker.yml ps -q nginx-static 2>/dev/null || true)
  if [ -n "$NSID" ]; then
    OUT="/root/logs/services/nginx-static.log"
    echo "" >> "$OUT" || true
    echo "--- /var/log/nginx (file-based logs) ---" >> "$OUT" || true
    docker exec "$NSID" sh -lc 'ls -la /var/log/nginx 2>/dev/null || true; for f in /var/log/nginx/*; do [ -f "$f" ] || continue; echo "\n----- $f -----"; tail -n 2000 "$f" || true; done' >> "$OUT" 2>&1 || true
  fi
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
    docker exec "$CID" sh -lc 'ls -la /etc/traefik/acme 2>/dev/null || true; for f in /etc/traefik/acme/*.json; do [ -f "$f" ] || continue; stat -c "%a %n" "$f" 2>/dev/null || true; done' > /root/logs/traefik-acme-perms.txt || true
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
    echo "MISSING_CID" | tee /root/logs/traefik-env.txt /root/logs/traefik-static.yml /root/logs/traefik-dynamic.yml /root/logs/traefik-ls.txt /root/logs/traefik-acme-perms.txt /root/logs/traefik-logs.txt /root/logs/api-logs.txt >/dev/null
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

    # Request-id log propagation probe:
    # - Send a request with an explicit X-Request-Id
    # - Confirm that ID appears in FastAPI/Django logs (and Traefik access log if available)
    # IMPORTANT: Keep this probe non-fatal; missing log hits should not abort remote verification.
    set +e
    RID=$(cat /proc/sys/kernel/random/uuid 2>/dev/null || true)
    if [ -z "$RID" ]; then
      RID=$(python3 -c 'import uuid; print(str(uuid.uuid4()))' 2>/dev/null || true)
    fi
    export RID
    mkdir -p /root/logs/meta /root/logs/services || true
    : > /root/logs/request-id-health.headers || true
    : > /root/logs/request-id-health.body || true
    curl -sk "${RESOLVE_DOMAIN[@]}" -H "X-Request-Id: $RID" -D /root/logs/request-id-health.headers -o /root/logs/request-id-health.body "https://$DOMAIN/api/health" || true

    TID=$(docker compose -f local.docker.yml ps -q traefik 2>/dev/null || true)
    AID=$(docker compose -f local.docker.yml ps -q api 2>/dev/null || true)
    DJID=$(docker compose -f local.docker.yml ps -q django 2>/dev/null || true)
    CWID=$(docker compose -f local.docker.yml ps -q celery-worker 2>/dev/null || true)

    # Capture grep outputs (best-effort; keep artifacts even on failure)
    : > /root/logs/services/request-id-traefik.txt || true
    : > /root/logs/services/request-id-api.txt || true
    : > /root/logs/services/request-id-django.txt || true
    : > /root/logs/services/request-id-celery-worker.txt || true

    if [ -n "$TID" ]; then
      docker exec "$TID" sh -lc "(grep -F \"$RID\" /var/log/traefik/access.log 2>/dev/null || true) | tail -n 50" > /root/logs/services/request-id-traefik.txt 2>&1 || true
    fi
    if [ -n "$AID" ]; then
      docker logs --timestamps --since=10m "$AID" 2>/dev/null | grep -F "$RID" | tail -n 50 > /root/logs/services/request-id-api.txt || true
    fi
    if [ -n "$DJID" ]; then
      docker logs --timestamps --since=10m "$DJID" 2>/dev/null | grep -F "$RID" | tail -n 50 > /root/logs/services/request-id-django.txt || true
    fi
    if [ -n "$CWID" ]; then
      docker logs --timestamps --since=10m "$CWID" 2>/dev/null | grep -F "$RID" | tail -n 50 > /root/logs/services/request-id-celery-worker.txt || true
    fi

    python3 -c "import json, os; from pathlib import Path;\
def rt(p):\
  try:\
    return Path(p).read_text(encoding='utf-8', errors='replace').strip()\
  except Exception:\
    return ''\
rid=os.environ.get('RID','');\
found={\
  'traefik': bool(rt('/root/logs/services/request-id-traefik.txt')),\
  'api': bool(rt('/root/logs/services/request-id-api.txt')),\
  'django': bool(rt('/root/logs/services/request-id-django.txt')),\
  'celery_worker': bool(rt('/root/logs/services/request-id-celery-worker.txt')),\
};\
payload={'request_id': rid, 'ok': bool(rid) and found['api'] and found['django'], 'found': found};\
print(json.dumps(payload))" > /root/logs/meta/request-id-log-propagation.json 2> /root/logs/meta/request-id-log-propagation.err || true
    set -e

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
      : > /root/logs/celery-ping.json || true
      : > /root/logs/celery-result.json || true
      curl -sk "${RESOLVE_DOMAIN[@]}" -X POST "https://$DOMAIN/api/celery/ping" -H 'Content-Type: application/json' -d '{}' -o /root/logs/celery-ping.json || true
      TASK_ID=$(python3 -c "import json;\
import sys;\
try:\
  print(json.load(open('/root/logs/celery-ping.json'))['task_id']);\
except Exception:\
  print('')" 2>/dev/null || true)
      if [ -n "$TASK_ID" ]; then
        for i in $(seq 1 30); do
          curl -sk "${RESOLVE_DOMAIN[@]}" "https://$DOMAIN/api/celery/result/$TASK_ID" -o /root/logs/celery-result.json || true
          if grep -q '"successful": *true' /root/logs/celery-result.json 2>/dev/null; then
            break
          fi
          sleep 2
        done
      fi
    fi
  fi
  # mark completion
  # Run service test suites inside containers and capture outputs
  mkdir -p /root/logs || true
  # FastAPI (api) pytest
  # Ensure we run from /app so `import main` / local imports resolve as expected.
  docker compose -f local.docker.yml exec -T api sh -lc 'cd /app && pytest -q' > /root/logs/api-pytest.txt 2>&1 || true
  # Django pytest
  docker compose -f local.docker.yml exec -T django sh -lc 'pytest -q' > /root/logs/django-pytest.txt 2>&1 || true
  date -u +"%Y-%m-%dT%H:%M:%SZ" > /root/logs/remote_verify.done || true
fi
'@
  # Ensure Unix LF endings and no BOM for remote bash
  $unixScript = $scriptContent -replace "`r`n","`n"
  Set-Content -Path $tmpScript -Value $unixScript -Encoding Ascii -NoNewline
  # Upload and execute the script
  try {
    & $scpExe -i $keyPath @($sshCommon) $tmpScript "root@${ip}:/root/remote_verify.sh" *> $null
    if ($LASTEXITCODE -ne 0) { throw "scp upload failed (exit $LASTEXITCODE)" }
  } finally {
    $LASTEXITCODE = 0
  }
  # Clear previous completion flag to avoid copying stale logs immediately
  try { & $sshExe @sshArgs "rm -f /root/logs/remote_verify.done" *> $null } catch { }
  if ($AsyncVerify) {
    if ($RunCeleryCheck) {
      & $sshExe @sshArgs "RUN_CELERY_CHECK=1 nohup bash /root/remote_verify.sh > /root/remote_verify.out 2>&1 & echo \$! > /root/remote_verify.pid" *> $null
    } else {
      & $sshExe @sshArgs "nohup bash /root/remote_verify.sh > /root/remote_verify.out 2>&1 & echo \$! > /root/remote_verify.pid" *> $null
    }
  } else {
    $timeoutCmd = "if command -v timeout >/dev/null 2>&1; then timeout -k 15s $VerifyTimeoutSec bash /root/remote_verify.sh; else bash /root/remote_verify.sh; fi"
    if ($RunCeleryCheck) {
      & $sshExe @sshArgs "RUN_CELERY_CHECK=1 sh -lc '$timeoutCmd'" *> $null
    } else {
      & $sshExe @sshArgs "sh -lc '$timeoutCmd'" *> $null
    }
  }

  if ($LASTEXITCODE -ne 0) {
    $code = $LASTEXITCODE
    $LASTEXITCODE = 0
    throw "Remote verification SSH failed (exit $code)"
  }

  # If we ran synchronously, require a completion marker; otherwise we risk proceeding with
  # partial /root/logs and then failing confusingly on missing artifacts.
  if (-not $AsyncVerify) {
    try {
      $flag = & $sshExe @sshArgs "test -f /root/logs/remote_verify.done && echo DONE || echo NOT_DONE" 2>&1
      if (-not ($flag -match 'DONE')) {
        throw "Remote verification did not complete (missing /root/logs/remote_verify.done). Try a larger -VerifyTimeoutSec (current=$VerifyTimeoutSec) or use -AsyncVerify."
      }
    } catch {
      throw $_
    }
  }

  Write-Section "Copying verification artifacts"
  $dest = Ensure-ArtifactDir

  # Robust copy with polling when async: wait for /root/logs/remote_verify.done, then scp
  $attempts = 3
  if ($AsyncVerify) { $attempts = [Math]::Max($attempts, [int]$LogsPollMaxAttempts) }
  $interval = [Math]::Max(2, [int]$LogsPollIntervalSec)
  $copied = $false
  $lastCopyErr = $null
  for ($i = 1; $i -le $attempts; $i++) {
    try {
      if ($AsyncVerify) {
        $flag = & $sshExe @sshArgs "test -f /root/logs/remote_verify.done && echo DONE || echo WAIT" 2>&1
        if (-not ($flag -match 'DONE')) {
          Start-Sleep -Seconds $interval
          continue
        }
      }
      # Copy entire remote logs directory (build + services + snapshots)
      & $scpExe -i $keyPath @($sshCommon) -r "root@${ip}:/root/logs" $dest *> $null
      if ($LASTEXITCODE -ne 0) { throw "scp logs failed (exit $LASTEXITCODE)" }
      $copied = $true
      break
    } catch {
      $lastCopyErr = $_
      Start-Sleep -Seconds ([Math]::Min(30, $interval * $i))
    }
  }

  # Fallback: try copying a single tarball if directory copy was flaky.
  if (-not $copied) {
    try {
      & $sshExe @sshArgs "tar -czf /root/logs.tgz -C /root logs" *> $null
      if ($LASTEXITCODE -ne 0) { throw "remote tar failed (exit $LASTEXITCODE)" }
      $tgzPath = Join-Path $dest 'logs.tgz'
      & $scpExe -i $keyPath @($sshCommon) "root@${ip}:/root/logs.tgz" $tgzPath *> $null
      if ($LASTEXITCODE -ne 0) { throw "scp logs.tgz failed (exit $LASTEXITCODE)" }
      if (Test-Path $tgzPath) {
        & tar -xzf $tgzPath -C $dest *> $null
        Remove-Item -Force $tgzPath -ErrorAction SilentlyContinue
        $copied = $true
      }
    } catch {
      $lastCopyErr = $_
    }
  }

  if (-not $copied) {
    $msg = "Remote logs could not be copied after $attempts attempts"
    if ($lastCopyErr) { $msg += ": $($lastCopyErr.Exception.Message)" }
    Write-Warning "$msg; continuing. You can re-run copy later."
  } else {
    # Best-effort copy of individual files to the root of $dest for convenience
    $files = @(
      'compose-ps.txt','traefik-env.txt','traefik-static.yml','traefik-dynamic.yml','traefik-ls.txt','traefik-logs.txt','api-logs.txt',
      'traefik-acme-perms.txt',
      'django-migrate.txt',
      'django-check-deploy.txt',
      'django-internal-health.json',
      'django-internal-health.status',
      'schema-compat-check.json','schema-compat-check.err','schema-compat-check.status',
      'published-ports.txt',
      'curl-root.txt','curl-api.txt','curl-api-health.txt','curl-api-health-slash.txt',
      'curl-admin-head.txt',
      'api-health.json','api-health.status','api-health-slash.json','api-health-slash.status',
      'traefik-dynamic.template.yml','traefik-static.template.yml','remote_verify.done'
    )
    foreach ($f in $files) {
      try { & $scpExe -i $keyPath @($sshCommon) "root@${ip}:/root/logs/$f" $dest *> $null } catch { }
    }

    # Ensure expected artifacts are present at the run-folder root even if per-file scp fails.
    # scp -r copies into $dest\logs\..., so we promote key files from there.
    try {
      $logsRoot = Join-Path $dest 'logs'
      foreach ($f in $files) {
        $src = Join-Path $logsRoot $f
        $dst = Join-Path $dest $f
        if ((-not (Test-Path $dst)) -and (Test-Path $src)) {
          Copy-Item -Path $src -Destination $dst -Force
        }
      }
      # Also promote env-dollar-check artifacts if present.
      foreach ($f in @('env-dollar-check.txt','env-dollar-check.status')) {
        $src = Join-Path (Join-Path $logsRoot 'build') $f
        $dst = Join-Path $dest $f
        if ((-not (Test-Path $dst)) -and (Test-Path $src)) {
          Copy-Item -Path $src -Destination $dst -Force
        }
      }
    } catch {}
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

  # Avoid leaking a non-zero $LASTEXITCODE to callers (native tools may set it).
  try { $LASTEXITCODE = 0 } catch {}

  # Droplet info JSON omitted (optional enhancement; non-critical for verification)

  }
  finally {
    $ErrorActionPreference = $prevEap
  }

}


Write-Section "Base2 Deploy"
try {
  $null = Ensure-ArtifactDir
  # Provide the orchestrator a per-run artifact directory. It will write DO_userdata.json
  # into this folder during the same run (even before the droplet IP is known).
  try { $env:BASE2_ARTIFACT_DIR = (Ensure-ArtifactDir) } catch {}

  # Start capturing console output early.
  Start-DeployTranscript

  # If a stale root DO_userdata.json exists, move it into the run folder to avoid pollution.
  try {
    $rootUd = Join-Path $PSScriptRoot "..\DO_userdata.json"
    if (Test-Path $rootUd) {
      $dest = Ensure-ArtifactDir
      $movedName = 'DO_userdata.root.moved.json'
      $movedPath = Join-Path $dest $movedName
      Move-Item -Path $rootUd -Destination $movedPath -Force
    }
  } catch {}

  Ensure-Venv
  Activate-Venv
  Load-DotEnv -path $EnvPath
  Assert-EnvNotTracked
  Update-Allowlist
  if ($Preflight) {
    Invoke-Preflight
    Write-Section "Preflight only"
    Write-Output "Preflight passed. No cloud actions executed."
    $script:ExitCode = 0
    throw $script:EarlyExitSentinel
  }
  Validate-DoCreds
  
  # Default AllTests to UpdateOnly when an environment exists and -Full was not requested.
  $autoSelectedUpdateOnly = $false
  $detectedExistingIp = ''
  if ($AllTests -and -not $Full -and -not $UpdateOnly) {
    try {
      $ipCheck = Get-DropletIp
      if ($ipCheck) {
        $detectedExistingIp = [string]$ipCheck
        $autoSelectedUpdateOnly = $true
        Write-Section "AllTests: existing environment detected ($ipCheck); defaulting to -UpdateOnly"
        $UpdateOnly = $true
      } else {
        Write-Section "AllTests: no existing environment detected; proceeding without -UpdateOnly"
      }
    } catch {
      Write-Verbose ("AllTests UpdateOnly default check failed: {0}" -f $_.Exception.Message)
    }
  }

  # Record requested vs effective mode into artifacts (T078).
  try {
    $dest = Ensure-ArtifactDir
    $branch = $env:DO_APP_BRANCH
    if (-not $branch) { $branch = '' }
    $effectiveMode = 'auto'
    if ($Full) { $effectiveMode = 'full' }
    elseif ($UpdateOnly) { $effectiveMode = 'update-only' }

    $modePayload = [ordered]@{
      timestampUtc = (Get-UtcTimestamp)
      allTests = [bool]$AllTests
      requested = [ordered]@{
        full = [bool]$Full
        updateOnly = [bool]$UpdateOnly
      }
      effectiveMode = $effectiveMode
      autoSelectedUpdateOnly = [bool]$autoSelectedUpdateOnly
      detectedExistingIp = $detectedExistingIp
      doAppBranch = $branch
    }
    $modeJson = ($modePayload | ConvertTo-Json -Depth 6)
    Set-Content -Path (Join-Path $dest 'deploy-mode.json') -Value $modeJson -Encoding UTF8
  } catch {}

  # Reminder banner for UpdateOnly runs: ensure commit/push to origin/<DO_APP_BRANCH>
  if ($UpdateOnly -and -not $Full) {
    try {
      $branch = $env:DO_APP_BRANCH
      if (-not $branch) { $branch = '(unset)' }
      Write-Section "UpdateOnly: using remote branch origin/$branch"
      Write-Host "Reminder: UpdateOnly hard-resets the droplet repo to origin/$branch. Commit and push any runtime-impacting changes (api/, django/, react-app/, Dockerfiles, compose, traefik) before running UpdateOnly." -ForegroundColor Yellow
    } catch {}
  }
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
    $support += "Run: ./digital_ocean/scripts/powershell/deploy.ps1 -Preflight -RunTests -TestsJson"
    Set-Content -Path (Join-Path $dest 'support.txt') -Value ($support -join [Environment]::NewLine) -Encoding UTF8
    $script:ExitCode = 0
    throw $script:EarlyExitSentinel
  }

  $script:ResolvedIp = $resolvedIp
  Switch-TranscriptToResolvedArtifactDir -ip $resolvedIp
  $null = Ensure-ArtifactDir -ip $resolvedIp

  # Expand -AllTests before remote verification so droplet verification produces required artifacts.
  if ($AllTests) {
    $RunTests = $true
    $TestsJson = $true
    $RunRateLimitTest = $true
    $RunCeleryCheck = $true
  }

  Remote-Verify -ip $resolvedIp -keyPath $SshKey

  # Group downloaded artifacts by service for easier debugging.
  Organize-ArtifactsByService

  # Bundle droplet-side artifacts/logs into a single local file for later review.
  Write-RemoteArtifactsBundle

  if ($RunTests) {
    Write-Section "Running post-deploy tests"
    if ($TestsJson) {
      $testArgs = @{ EnvPath = $EnvPath; LogsDir = $LogsDir; UseLatestTimestamp = $true; Json = $true; CheckDjangoAdmin = $true; ResolveIp = $script:ResolvedIp; ExpectedIpv4 = $script:ResolvedIp }
      if ($RunRateLimitTest) { $testArgs.CheckRateLimit = $true; $testArgs.RateLimitBurst = $RateLimitBurst }
      if ($RunCeleryCheck) { $testArgs.CheckCelery = $true }
      if ($AllTests) { $testArgs.All = $true }
      $jsonOut = & .\digital_ocean\scripts\powershell\test.ps1 @testArgs
      $exitCode = $LASTEXITCODE
      $artifactDir = Ensure-ArtifactDir
      $metaDir = Join-Path $artifactDir 'meta'
      if (-not (Test-Path $metaDir)) { New-Item -ItemType Directory -Path $metaDir -Force | Out-Null }
      $reportPath = Join-Path $metaDir $ReportName
      try {
        Set-Content -Path $reportPath -Value $jsonOut -Encoding UTF8
        Write-Host "Saved JSON report: $reportPath" -ForegroundColor Yellow
      } catch {
        Write-Warning "Failed to write JSON report: $($_.Exception.Message)"
      }

      # Re-organize after writing report so it lands in meta/ on older runs too.
      Organize-ArtifactsByService

      if ($exitCode -ne 0) {
        Write-Warning "Post-deploy tests failed"
        $script:ExitCode = 1
        throw $script:EarlyExitSentinel
      }
    } else {
      $testArgs2 = @{ EnvPath = $EnvPath; LogsDir = $LogsDir; UseLatestTimestamp = $true; CheckDjangoAdmin = $true; ResolveIp = $script:ResolvedIp; ExpectedIpv4 = $script:ResolvedIp }
      if ($RunRateLimitTest) { $testArgs2.CheckRateLimit = $true; $testArgs2.RateLimitBurst = $RateLimitBurst }
      if ($RunCeleryCheck) { $testArgs2.CheckCelery = $true }
      if ($AllTests) { $testArgs2.All = $true }
      & .\digital_ocean\scripts\powershell\test.ps1 @testArgs2
      if ($LASTEXITCODE -ne 0) {
        Write-Warning "Post-deploy tests failed"
        $script:ExitCode = 1
        throw $script:EarlyExitSentinel
      }
    }

    # T024: Run React Jest tests locally and capture output
    try {
      Write-Section "Running React Jest (local)"
      $artifactDir = Ensure-ArtifactDir
      $reactOutDir = Join-Path $artifactDir 'react-app'
      if (-not (Test-Path $reactOutDir)) { New-Item -ItemType Directory -Path $reactOutDir -Force | Out-Null }
      $jestOutPath = Join-Path $reactOutDir 'jest.txt'
      Push-Location (Join-Path $script:RepoRoot 'react-app')
      $log = @()
      $log += ("UTC: {0}" -f (Get-UtcTimestamp))
      try { $log += (& node --version 2>&1 | Out-String).TrimEnd() } catch {}
      try { $log += (& npm --version 2>&1 | Out-String).TrimEnd() } catch {}
      $log += ''

      $log += '== npm ci =='
      $ciOut = ''
      $ciExit = 0
      $prevEAP = $ErrorActionPreference
      try {
        # npm emits warnings to stderr; with $ErrorActionPreference='Stop' that can become terminating.
        $ErrorActionPreference = 'Continue'
        $ciOut = (& cmd /c "npm ci --no-audit --no-fund" 2>&1 | Out-String)
        $ciExit = $LASTEXITCODE
      } finally {
        $ErrorActionPreference = $prevEAP
      }
      $log += $ciOut.TrimEnd()
      $log += ("npm ci exitCode={0}" -f $ciExit)
      $log += ''

      if ($ciExit -ne 0) {
        $log += 'Skipping Jest because npm ci failed.'
        $log | Set-Content -Path $jestOutPath -Encoding UTF8
      } else {
        $log += '== Jest (CRA) =='
        $prevCI = $env:CI
        try {
          $env:CI = 'true'
          $testOut = ''
          $testExit = 0
          $prevEAP = $ErrorActionPreference
          try {
            $ErrorActionPreference = 'Continue'
            # Avoid cross-env (often the source of Windows PATH issues) and rely on PowerShell env.
            $testOut = (& cmd /c "npm test -- --coverage" 2>&1 | Out-String)
            $testExit = $LASTEXITCODE
          } finally {
            $ErrorActionPreference = $prevEAP
          }
          $log += $testOut.TrimEnd()
          $log += ("npm test exitCode={0}" -f $testExit)
        } finally {
          $env:CI = $prevCI
        }
        $log | Set-Content -Path $jestOutPath -Encoding UTF8
      }
    } catch {
      Write-Warning ("React Jest execution error: {0}" -f $_.Exception.Message)
    } finally { try { Pop-Location } catch {} }
  }

  Write-Section "Done"
  $artDir = Ensure-ArtifactDir
  Write-Output ("Artifacts saved to: " + $artDir)
  $script:ExitCode = 0
} catch {
  $msg = $_.Exception.Message
  if ($msg -ne $script:EarlyExitSentinel) {
    Write-Warning "Deploy failed: $msg"
    Write-FailureArtifacts -context 'exception' -message $msg
    $script:ExitCode = 1
  }
} finally {
  Stop-DeployTranscript
  Finalize-ArtifactDirRename
  Append-RemoteArtifactsToConsoleLog

  # If a manual test runner wrote its JSON output at repo root, sweep it into this run's meta/.
  try {
    $manualOut = Join-Path $script:RepoRoot 'manual-test-out.json'
    if (Test-Path $manualOut) {
      $dest = Ensure-ArtifactDir
      $metaDir = Join-Path $dest 'meta'
      if (-not (Test-Path $metaDir)) { New-Item -ItemType Directory -Path $metaDir -Force | Out-Null }
      Copy-Item -LiteralPath $manualOut -Destination (Join-Path $metaDir 'manual-test-out.json') -Force
    }
  } catch {}

  try { Pop-Location } catch {}
}

exit $script:ExitCode
