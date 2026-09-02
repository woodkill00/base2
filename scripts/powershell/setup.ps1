[CmdletBinding()]
param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$Args,
  [Alias('h')]
  [switch]$Help,
  [switch]$NonInteractive,
  [switch]$SkipSetupJs,
  [string]$EnvPath,
  [switch]$DoSyncDryRun
)

$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path (Join-Path $PSScriptRoot '..') '..')

if ($Help) {
  Write-Host 'Usage: ./scripts/powershell/setup.ps1 [options] [-- <setup.js args>]' -ForegroundColor Cyan
  Write-Host ''
  Write-Host 'Options:'
  Write-Host '  -NonInteractive   Run setup.js without prompts (fails if required values are missing)'
  Write-Host '  -SkipSetupJs      Skip setup.js and only run secret generation + DO SSH sync'
  Write-Host '  -EnvPath <path>   Target a different .env file (default: repo root .env.build)'
  Write-Host '  -DoSyncDryRun     Dry-run the DigitalOcean SSH key sync step'
  Write-Host '  -Help, -h         Show this help'
  Write-Host ''
  Write-Host 'Extra args after -- are forwarded to scripts/setup.js.'
  return
}

if (-not $env:VIRTUAL_ENV) {
  Write-Warning 'Virtual environment not active. For first-time setup, run ./scripts/powershell/first-start.ps1.'
}

$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) {
  Write-Error 'node is required. Install Node.js 24.20.0+ and re-run.'
  exit 127
}

$setupJs = Join-Path $repoRoot 'scripts\setup.js'

if (-not $SkipSetupJs) {
  Write-Host '==> Running setup.js' -ForegroundColor Cyan

  if ($NonInteractive) {
    $output = & $node.Path $setupJs @Args 2>&1
    $exitCode = $LASTEXITCODE
    if ($output) {
      $output | ForEach-Object { Write-Host $_ }
    }
    if ($exitCode -ne 0) {
      throw "setup.js failed with exit code $exitCode"
    }
  } else {
    & $node.Path $setupJs @Args
    if ($LASTEXITCODE -ne 0) {
      throw "setup.js failed with exit code $LASTEXITCODE"
    }
  }

  Write-Host 'OK: setup.js completed' -ForegroundColor Green
}

$envPath = if ($EnvPath) { Resolve-Path $EnvPath } else { Join-Path $repoRoot '.env.build' }
if (-not (Test-Path $envPath)) {
  Write-Warning 'Missing .env.build; skipping secret generation.'
  exit 0
}

function New-RandomHex([int]$bytes = 32) {
  $buffer = New-Object byte[] $bytes
  [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($buffer)
  return ($buffer | ForEach-Object { $_.ToString('x2') }) -join ''
}

function New-RandomBase64Url([int]$bytes = 32) {
  $buffer = New-Object byte[] $bytes
  [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($buffer)
  return [Convert]::ToBase64String($buffer).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}

$targetKeys = @(
  'TP_DJANGO_SECRET_KEY',
  'TP_JWT_SECRET',
  'TP_TOKEN_PEPPER',
  'TP_IDENTITY_ENCRYPTION_KEY',
  'TP_CONTENT_WORKSPACE_STORAGE_KEY',
  'TP_OAUTH_STATE_SECRET',
  'TP_SEED_ADMIN_PASSWORD',
  'TP_SEED_DEMO_PASSWORD',
  'TP_DJANGO_SUPERUSER_PASSWORD',
  'TP_REDIS_PASSWORD',
  'TP_POSTGRES_PASSWORD',
  'TP_PGADMIN_PASSWORD',
  'TP_FLOWER_PASSWORD',
  'TP_TRAEFIK_PASSWORD'
)

$placeholderPattern = '(?i)^(change_me|your_|generated_password_here|your_super_secret|placeholder|todo)'

$lines = Get-Content -Path $envPath
$updated = $false
$newValues = @{}
foreach ($key in $targetKeys) {
  $newValues[$key] = if ($key -eq 'TP_CONTENT_WORKSPACE_STORAGE_KEY') {
    New-RandomBase64Url 32
  } else {
    New-RandomHex 32
  }
}

for ($i = 0; $i -lt $lines.Count; $i++) {
  $line = $lines[$i]
  foreach ($key in $targetKeys) {
    if ($line -match "^${key}=") {
      $currentValue = $line.Substring($key.Length + 1)
      if ([string]::IsNullOrWhiteSpace($currentValue) -or $currentValue -match $placeholderPattern) {
        $lines[$i] = "$key=$($newValues[$key])"
        $updated = $true
      }
      break
    }
  }
}

if ($updated) {
  Set-Content -Path $envPath -Value $lines -Encoding UTF8
  Write-Host 'OK: Generated new secret values in .env' -ForegroundColor Green
} else {
  Write-Host 'OK: Secret values already set; no changes made' -ForegroundColor DarkGreen
}

function Write-Log([string]$level, [string]$msg, [string]$color = 'Gray') {
  $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
  Write-Host "[$ts][$level] $msg" -ForegroundColor $color
}

function Get-EnvValue([string]$key, [string[]]$content) {
  foreach ($line in $content) {
    $trimmed = $line.Trim()
    if (-not $trimmed -or $trimmed.StartsWith('#')) { continue }
    $m = [regex]::Match($trimmed, '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$')
    if (-not $m.Success) { continue }
    if ($m.Groups[1].Value -eq $key) {
      return $m.Groups[2].Value
    }
  }
  return $null
}

function Update-EnvLine([string[]]$content, [string]$key, [string]$value) {
  $updatedLocal = $false
  for ($i = 0; $i -lt $content.Count; $i++) {
    $line = $content[$i]
    $m = [regex]::Match($line, "^${key}=(.*)$")
    if (-not $m.Success) { continue }
    $suffix = ''
    $commentIndex = $line.IndexOf(' #')
    if ($commentIndex -ge 0) {
      $suffix = $line.Substring($commentIndex)
    }
    $content[$i] = "$key=$value$suffix"
    $updatedLocal = $true
    break
  }
  if (-not $updatedLocal) {
    $content += "$key=$value"
    $updatedLocal = $true
  }
  return @{ updated = $updatedLocal; content = $content }
}

function Invoke-DoSshFind([string]$pythonExe, [string]$name) {
  $args = @('-m', 'digital_ocean.scripts.python.DO_ssh_keys', '--find', '--name', $name, '--json')
  $tmpStdout = Join-Path $env:TEMP "do-ssh-find-out-$PID.txt"
  $tmpStderr = Join-Path $env:TEMP "do-ssh-find-err-$PID.txt"
  $argLine = $args -join ' '
  $proc = Start-Process -FilePath $pythonExe -ArgumentList $argLine -NoNewWindow -Wait -PassThru -RedirectStandardOutput $tmpStdout -RedirectStandardError $tmpStderr
  $stdoutLines = @()
  $stderrLines = @()
  if (Test-Path $tmpStdout) { $stdoutLines += Get-Content -Path $tmpStdout -ErrorAction SilentlyContinue }
  if (Test-Path $tmpStderr) { $stderrLines += Get-Content -Path $tmpStderr -ErrorAction SilentlyContinue }
  if ($stdoutLines) { $stdoutLines | ForEach-Object { Write-Log 'DO' $_ } }
  if ($stderrLines) { $stderrLines | ForEach-Object { Write-Log 'DO' $_ } }
  if ($proc.ExitCode -ne 0) {
    throw "DO_ssh_keys find failed with exit code $($proc.ExitCode)"
  }
  $combined = ($stdoutLines + $stderrLines) -join "`n"
  $match = [regex]::Match($combined, '\[[\s\S]*\]')
  if ($match.Success) {
    $payload = $match.Value.Trim()
    if ($payload) {
      return @($payload | ConvertFrom-Json -ErrorAction Stop)
    }
  }
  return @()
}

try {
  Write-Log 'INFO' 'DigitalOcean SSH key sync starting.' 'Cyan'

  $envLines = Get-Content -Path $envPath
  $projectName = Get-EnvValue -key 'PROJECT_NAME' -content $envLines
  $keyName = if ($projectName) { $projectName } else { 'do-ssh' }

  $sshDir = Join-Path $env:USERPROFILE '.ssh'
  $publicKeyPath = Join-Path $sshDir "$keyName.pub"
  $addSshScript = Join-Path $repoRoot 'digital_ocean\scripts\powershell\add-ssh-key.ps1'
  $pythonExe = 'python'

  if (-not (Test-Path $addSshScript)) {
    Write-Log 'WARN' 'add-ssh-key.ps1 not found; skipping DigitalOcean SSH sync.' 'Yellow'
    exit 0
  }

  Write-Log 'INFO' "Ensuring local and remote SSH keys match for '$keyName'." 'Cyan'
  if ($DoSyncDryRun) {
    Write-Log 'INFO' 'DO sync dry-run enabled; no remote changes will be made.' 'Yellow'
    & powershell -File $addSshScript -KeyName $keyName -SshDir $sshDir -PythonExe $pythonExe -DryRun
  } else {
    & powershell -File $addSshScript -KeyName $keyName -SshDir $sshDir -PythonExe $pythonExe
  }
  if ($LASTEXITCODE -ne 0) {
    throw "add-ssh-key.ps1 failed with exit code $LASTEXITCODE"
  }

  if ($DoSyncDryRun) {
    Write-Log 'INFO' 'DO sync dry-run complete; skipping DO key lookup and .env updates.' 'Yellow'
    exit 0
  }

  if (-not (Test-Path $publicKeyPath)) {
    throw "Local public key not found at $publicKeyPath"
  }
  $localPublicKey = (Get-Content -Path $publicKeyPath -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
  if (-not $localPublicKey) {
    throw "Local public key is empty at $publicKeyPath"
  }

  Write-Log 'INFO' 'Querying DigitalOcean SSH key metadata.' 'Cyan'
  $remoteMatches = Invoke-DoSshFind -pythonExe $pythonExe -name $keyName
  if ($null -eq $remoteMatches) { $remoteMatches = @() }
  $remoteMatches = @($remoteMatches)
  if ($remoteMatches.Count -eq 1 -and $remoteMatches[0] -is [System.Array]) { $remoteMatches = $remoteMatches[0] }

  $matched = $null
  foreach ($item in $remoteMatches) {
    $remoteKey = $item.public_key
    if ($remoteKey) { $remoteKey = $remoteKey.Trim() }
    if ($remoteKey -eq $localPublicKey) {
      $matched = $item
      break
    }
  }

  if (-not $matched) {
    Write-Log 'WARN' 'No matching remote key found for the local public key; skipping .env update.' 'Yellow'
    exit 0
  }

  $fingerprint = $matched.fingerprint
  $publicKey = $matched.public_key
  if (-not $fingerprint -or -not $publicKey) {
    Write-Log 'WARN' 'Remote key metadata incomplete; skipping .env update.' 'Yellow'
    exit 0
  }

  Write-Log 'INFO' 'Updating .env with DigitalOcean SSH key values.' 'Cyan'
  $envUpdated = $false
  $result = Update-EnvLine -content $envLines -key 'DO_SSH_KEY_ID' -value $fingerprint
  $envLines = $result.content
  $envUpdated = $envUpdated -or $result.updated

  $result = Update-EnvLine -content $envLines -key 'DO_API_SSH_KEYS' -value $publicKey
  $envLines = $result.content
  $envUpdated = $envUpdated -or $result.updated

  if ($envUpdated) {
    Set-Content -Path $envPath -Value $envLines -Encoding UTF8
    Write-Log 'INFO' 'Updated .env with DigitalOcean SSH key fingerprint and public key.' 'Green'
  } else {
    Write-Log 'INFO' 'No .env changes required for DigitalOcean SSH key values.' 'DarkGreen'
  }
} catch {
  Write-Log 'ERROR' $_.Exception.Message 'Red'
}

exit 0
