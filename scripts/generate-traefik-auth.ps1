<#
Purpose: Generate Traefik Basic-Auth htpasswd entry safely for use in .env
 - Supports apr1 (MD5) and bcrypt (via Node if available)
 - Escapes '$' as '$$' for Docker Compose/.env safety
 - Validates username/password for problematic characters
 - Retries generation until a safe, non-problematic line is produced

Usage examples:
  # Interactive prompts
  powershell -File scripts/generate-traefik-auth.ps1

  # Non-interactive
  powershell -File scripts/generate-traefik-auth.ps1 -Username testuser -Password testuser -Algorithm apr1

Outputs:
  - Safe .env line: TRAEFIK_DASH_BASIC_USERS=username:escaped_hash
  - Raw htpasswd:   username:raw_hash

Note:
  - Apr1 is widely supported; bcrypt is preferred for strength but requires Node or Python bcrypt.
  - Traefik expects single '$' inside the container; we output '$$' for .env, which resolves to '$' at runtime.
#>

param(
  [string]$Username,
  [string]$Password,
  [ValidateSet('apr1','bcrypt')][string]$Algorithm = 'apr1',
  [int]$MaxRetries = 5
)

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err($msg) { Write-Host "[ERROR] $msg" -ForegroundColor Red }

# Prompt if not provided
if (-not $Username) { $Username = Read-Host 'Enter username' }
if (-not $Password) { $Password = Read-Host 'Enter password' }

# Basic validation
if ($Username -match '[\s]' -or $Username -match ':') {
  Write-Err 'Username must not contain spaces or colons. Aborting.'
  exit 1
}
if ([string]::IsNullOrWhiteSpace($Password)) {
  Write-Err 'Password cannot be empty. Aborting.'
  exit 1
}

function Get-HtpasswdApr1($user, $pass) {
  # Prefer docker httpd generator to avoid local dependencies
  $cmd = "docker run --rm httpd:2.4-alpine htpasswd -nbm `"$user`" <password>"
  Write-Info "Generating apr1 hash via: $cmd"
  try {
    $raw = (& docker run --rm httpd:2.4-alpine htpasswd -nbm "$user" "$pass") 2>$null
    if (-not $raw) { throw 'Empty output from htpasswd' }
    $line = @($raw) | ForEach-Object { $_.ToString() } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -First 1
    if (-not $line) { throw 'Empty output from htpasswd' }
    return $line.Trim()
  }
  catch {
    Write-Warn "Docker httpd htpasswd failed: $($_.Exception.Message). Falling back to openssl perl method."
    # Fallback: use perl-style apr1 algorithm via openssl if available (best-effort)
    $salt = -join ((48..57 + 65..90 + 97..122) | Get-Random -Count 8 | ForEach-Object {[char]$_})
    try {
      $digest = (& openssl passwd -apr1 -salt $salt $pass) 2>$null
      if ($digest) { return "${user}:$digest" }
    } catch {}
    throw 'Failed to generate apr1 hash with all methods'
  }
}

function Get-HtpasswdBcrypt($user, $pass) {
  # Use Node bcrypt if available
  $node = Get-Command node -ErrorAction SilentlyContinue
  if ($null -ne $node) {
$script = @"
const bcrypt = require('bcrypt');
const user = process.argv[2];
const pass = process.argv[3];
bcrypt.hash(pass, 10).then(h => {
  console.log(`${user}:${h}`);
}).catch(e => {
  console.error(e);
  process.exit(1);
});
"@
    $tmp = [System.IO.Path]::GetTempFileName()
    [System.IO.File]::WriteAllText($tmp, $script)
    try {
      $raw = (& node $tmp $user $pass)
      Remove-Item $tmp -Force
      if (-not $raw) { throw 'Empty output from bcrypt Node script' }
      return ($raw.ToString().Trim())
    } catch {
      Remove-Item $tmp -Force -ErrorAction SilentlyContinue
      Write-Warn "Node bcrypt failed: $($_.Exception.Message)"
    }
  }
  throw 'bcrypt generation requires Node (or add a Python bcrypt fallback)'
}

function Escape-ForEnv($raw) {
  # Double all '$' to '$$' for .env/Docker Compose safety
  return ($raw.Replace('$', '$$'))
}

function Is-Safe($raw, $escaped) {
  # Raw must contain single-dollar markers (e.g., $apr1$ or $2y$)
  if ($Algorithm -eq 'apr1' -and ($raw -notmatch '\$apr1\$')) { return $false }
  if ($Algorithm -eq 'bcrypt' -and ($raw -notmatch '\$2[aby]\$')) { return $false }

  # Escaped must not contain any unescaped single '$'
  if ($escaped -match '(?<!\$)\$(?!\$)') { return $false }

  # Should not contain whitespace or newline
  if ($raw -match '\s' -or $escaped -match '\s') { return $false }

  # Ensure format `username:hash`
  if ($raw -notmatch '^[^:]+:.+$') { return $false }

  # Hash characters safety: allow only [A-Za-z0-9./$] to avoid shell/env issues
  $parts = $raw.Split(':',2)
  if ($parts.Count -lt 2) { return $false }
  $hash = $parts[1]
  if ($hash -notmatch '^[A-Za-z0-9./$]+$') { return $false }
  return $true
}

$attempt = 0
while ($attempt -lt $MaxRetries) {
  $attempt++
  try {
    $raw = if ($Algorithm -eq 'apr1') { Get-HtpasswdApr1 -user $Username -pass $Password } else { Get-HtpasswdBcrypt -user $Username -pass $Password }
    $escaped = Escape-ForEnv -raw $raw
    if (Is-Safe -raw $raw -escaped $escaped) {
      Write-Host "" -ForegroundColor DarkGray
      Write-Host "Raw htpasswd:" -ForegroundColor Green
      Write-Host "  $raw"
      Write-Host "" -ForegroundColor DarkGray
      Write-Host "Env-safe line for .env:" -ForegroundColor Green
      Write-Host "  TRAEFIK_DASH_BASIC_USERS=$escaped"
      Write-Host "" -ForegroundColor DarkGray
      Write-Info "Copy the env-safe line into your .env and redeploy."
      exit 0
    } else {
      Write-Warn "Generated value failed safety checks. Retrying ($attempt/$MaxRetries)..."
    }
  } catch {
    Write-Warn "Attempt $attempt failed: $($_.Exception.Message)"
  }
}

Write-Err "Unable to generate a safe htpasswd entry after $MaxRetries attempts."
exit 2
