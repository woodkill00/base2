param(
  [string]$EnvPath = ".\.env",
  [string]$ComposePath = ".\local.docker.yml",
  [switch]$Strict,
  [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Ensure relative paths work regardless of where the script is invoked from.
$script:RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
Push-Location $script:RepoRoot

$script:ExitCode = 0

try {

function Write-Section($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Read-TextFile([string]$path) {
  if (-not (Test-Path $path)) { throw "File not found: $path" }
  Get-Content $path -Raw
}

function Parse-DotEnv([string]$path) {
  $vars = @{}
  if (-not (Test-Path $path)) { return $vars }
  Get-Content $path | ForEach-Object {
    $line = $_.Trim()
    if (-not $line) { return }
    if ($line.StartsWith('#')) { return }
    if ($line -match '^[A-Za-z_][A-Za-z0-9_]*=') {
      $kv = $line -split '=', 2
      $k = $kv[0]
      $v = $kv[1]
      $hashIndex = $v.IndexOf('#')
      if ($hashIndex -ge 0) { $v = $v.Substring(0, $hashIndex).TrimEnd() }
      if ($v.StartsWith('"') -and $v.EndsWith('"')) { $v = $v.Substring(1, $v.Length-2) }
      if ($v.StartsWith("'") -and $v.EndsWith("'")) { $v = $v.Substring(1, $v.Length-2) }
      $vars[$k] = $v
    }
  }
  return $vars
}

function Get-ServiceBlock([string]$name, [string[]]$lines) {
  $escaped = [regex]::Escape($name)
  $pattern = '^\s{2}' + $escaped + ':\s*$'
  $start = ($lines | Select-String -Pattern $pattern).LineNumber
  if (-not $start) { return @() }
  $result = @()
  for ($i = $start; $i -le $lines.Count; $i++) {
    $line = $lines[$i-1]
    $result += $line
    # Next service starts with two spaces then word then colon at same indent
    if ($i -gt $start -and $line -match '^\s{2}[A-Za-z0-9_-]+:\s*$') { break }
  }
  return $result
}

$script:checks = @()
function Add-Check([string]$name, [bool]$ok, [string]$details) {
  $script:checks += [pscustomobject]@{ name = $name; ok = $ok; details = $details }
}

Write-Section "Preflight Validation"

# 1) Env keys lint
$requiredEnv = @(
  'FASTAPI_PYTHON_VERSION','FASTAPI_PORT',
  'DJANGO_PYTHON_VERSION','DJANGO_PORT','DJANGO_SECRET_KEY','DJANGO_DEBUG','DJANGO_ALLOWED_HOSTS',
  'REACT_APP_API_URL',
  'POSTGRES_USER','POSTGRES_PASSWORD','POSTGRES_DB','POSTGRES_PORT',
  'JWT_SECRET','JWT_EXPIRE','RATE_LIMIT_WINDOW_MS','RATE_LIMIT_MAX_REQUESTS',
  'WEBSITE_DOMAIN',
  'TRAEFIK_LOG_LEVEL','TRAEFIK_PORT','TRAEFIK_API_PORT','TRAEFIK_CERT_EMAIL'
)

$envVars = Parse-DotEnv -path $EnvPath
$missing = @()
foreach ($k in $requiredEnv) { if (-not ($envVars.ContainsKey($k) -and ($envVars[$k] -ne ''))) { $missing += $k } }
$envDetails = if ($missing.Count -eq 0) { "All required keys present" } else { "Missing: " + ($missing -join ', ') }
Add-Check "Env keys present" ($missing.Count -eq 0) $envDetails

# 2) Compose file sanity: services and ports
$composeText = Read-TextFile -path $ComposePath
$lines = $composeText -split "`r?`n"

$reactBlock = Get-ServiceBlock -name 'react-app' -lines $lines
$apiBlock   = Get-ServiceBlock -name 'api' -lines $lines
$djangoBlock= Get-ServiceBlock -name 'django' -lines $lines
$traefikBlock= Get-ServiceBlock -name 'traefik' -lines $lines
$postgresBlock= Get-ServiceBlock -name 'postgres' -lines $lines

Add-Check "Service 'api' present" ($apiBlock.Count -gt 0) "api service block found: $([bool]($apiBlock.Count))"
Add-Check "Service 'django' present" ($djangoBlock.Count -gt 0) "django service block found: $([bool]($djangoBlock.Count))"

# Traefik ports only (accept quoted/unquoted YAML scalars)
$traefikPortMappings = @(
  $traefikBlock |
    Where-Object { $_ -match '^\s{6}-\s+[''\"]?\d+:\d+[''\"]?\s*$' } |
    ForEach-Object {
      if ($_ -match '[''\"]?(\d+):(\d+)[''\"]?') { "$($Matches[1]):$($Matches[2])" }
    }
)
$expectedMappings = @('80:80','443:443')
$traefikPortsOk = ($traefikPortMappings.Count -gt 0) -and (@($traefikPortMappings | Sort-Object -Unique) -join ',') -eq (@($expectedMappings | Sort-Object -Unique) -join ',')
Add-Check "Traefik exposes only 80/443" $traefikPortsOk ("ports=" + ($traefikPortMappings -join ', '))

function Has-Ports([string[]]$block) { ((($block | Where-Object { $_ -match '^\s{6}ports:\s*$' }) | Measure-Object).Count -gt 0) }
Add-Check "No host ports on api" (-not (Has-Ports $apiBlock)) "ports section present: $([bool](Has-Ports $apiBlock))"
Add-Check "No host ports on django" (-not (Has-Ports $djangoBlock)) "ports section present: $([bool](Has-Ports $djangoBlock))"
Add-Check "No host ports on postgres" (-not (Has-Ports $postgresBlock)) "ports section present: $([bool](Has-Ports $postgresBlock))"

# Ensure we are not using Docker provider labels (file-provider only)
function Has-TraefikLabels([string[]]$block) {
  ((($block | Where-Object { $_ -match 'traefik\.http\.' }) | Measure-Object).Count -gt 0)
}
Add-Check "No Traefik labels on react-app" (-not (Has-TraefikLabels $reactBlock)) "labels present: $([bool](Has-TraefikLabels $reactBlock))"
Add-Check "No Traefik labels on api" (-not (Has-TraefikLabels $apiBlock)) "labels present: $([bool](Has-TraefikLabels $apiBlock))"
Add-Check "No Traefik labels on django" (-not (Has-TraefikLabels $djangoBlock)) "labels present: $([bool](Has-TraefikLabels $djangoBlock))"

# Validate key routing primitives exist in traefik/dynamic.yml
$dynamicPath = '.\traefik\dynamic.yml'
$dynamicText = if (Test-Path $dynamicPath) { Read-TextFile -path $dynamicPath } else { '' }
Add-Check "Traefik dynamic.yml present" (Test-Path $dynamicPath) $dynamicPath
Add-Check "Dynamic: no strip /api middleware" (-not ($dynamicText -match 'strip-api-prefix')) "strip-api-prefix present: $([bool]($dynamicText -match 'strip-api-prefix'))"
Add-Check "Dynamic: no public /health router" (-not ($dynamicText -match 'PathPrefix\(/health\)')) "PathPrefix(/health) present: $([bool]($dynamicText -match 'PathPrefix\(/health\)'))"
Add-Check 'Dynamic: API service points to api:${FASTAPI_PORT}' ($dynamicText -match 'url:\s*http://api:\$\{FASTAPI_PORT\}') "api service url ok: $([bool]($dynamicText -match 'url:\s*http://api:\$\{FASTAPI_PORT\}'))"
Add-Check "Dynamic: React service points to react-app:8080" ($dynamicText -match 'url:\s*http://react-app:8080') "react service url ok: $([bool]($dynamicText -match 'url:\s*http://react-app:8080'))"

# 3) Required files
$requiredFiles = @(
  '.\digital_ocean\scripts\powershell\deploy.ps1',
  '.\digital_ocean\scripts\powershell\test.ps1',
  '.\digital_ocean\scripts\powershell\smoke-tests.ps1',
  '.\digital_ocean\scripts\python\orchestrate_deploy.py',
  '.\digital_ocean\scripts\python\validate_dns.py',
  '.\api\.Dockerfile', '.\api\requirements.txt', '.\api\main.py',
  '.\django\.Dockerfile', '.\django\requirements.txt', '.\django\manage.py',
  '.\django\project\settings\base.py', '.\django\project\settings\production.py', '.\django\project\urls.py', '.\django\project\wsgi.py'
)
$missingFiles = @()
foreach ($f in $requiredFiles) { if (-not (Test-Path $f)) { $missingFiles += $f } }
$fileDetails = if ($missingFiles.Count -eq 0) { "All present" } else { "Missing: " + ($missingFiles -join ', ') }
Add-Check "Required files exist" ($missingFiles.Count -eq 0) $fileDetails

# Output
if ($Json) {
  $script:checks | ConvertTo-Json -Depth 4 | Write-Output
} else {
  Write-Section "Results"
  foreach ($c in $script:checks) {
    $status = if ($c.ok) { "OK" } else { "FAIL" }
    $color = if ($c.ok) { 'Green' } else { 'Red' }
    Write-Host ("- {0}: {1} ({2})" -f $c.name, $status, $c.details) -ForegroundColor $color
  }
}

$failedCount = ((($script:checks | Where-Object { -not $_.ok }) | Measure-Object).Count)
if ($Strict -and $failedCount -gt 0) { $script:ExitCode = 1 } else { $script:ExitCode = 0 }
} finally {
  try { Pop-Location } catch {}
}

exit $script:ExitCode
