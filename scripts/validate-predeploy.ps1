param(
  [string]$EnvPath = ".\.env",
  [string]$ComposePath = ".\local.docker.yml",
  [switch]$Strict,
  [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

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
  $start = ($lines | Select-String -Pattern "^\s{$(2)}$name:\s*$" -SimpleMatch).LineNumber
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

$checks = @()
function Add-Check([string]$name, [bool]$ok, [string]$details) {
  $checks += [pscustomobject]@{ name = $name; ok = $ok; details = $details }
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
  'TRAEFIK_LOG_LEVEL','TRAEFIK_PORT','TRAEFIK_API_PORT','TRAEFIK_API_ENTRYPOINT','TRAEFIK_DOCKER_NETWORK','TRAEFIK_EXPOSED_BY_DEFAULT','TRAEFIK_HOST_PORT'
)

$envVars = Parse-DotEnv -path $EnvPath
$missing = @()
foreach ($k in $requiredEnv) { if (-not ($envVars.ContainsKey($k) -and ($envVars[$k] -ne ''))) { $missing += $k } }
Add-Check "Env keys present" ($missing.Count -eq 0) (if ($missing.Count -eq 0) { "All required keys present" } else { "Missing: " + ($missing -join ', ') })

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

# Traefik ports only
$traefikHas443 = ($traefikBlock | Where-Object { $_ -match "'443:443'" }).Count -gt 0
$traefikHasHost = ($traefikBlock | Where-Object { $_ -match "\$\{TRAEFIK_HOST_PORT\}:\$\{TRAEFIK_PORT\}" }).Count -gt 0
Add-Check "Traefik exposes only 80/443" ($traefikHas443 -and $traefikHasHost) "443:443=$traefikHas443, HOST_PORT mapping=$traefikHasHost"

function Has-Ports([string[]]$block) { ($block | Where-Object { $_ -match '^\s{6}ports:\s*$' }).Count -gt 0 }
Add-Check "No host ports on api" (-not (Has-Ports $apiBlock)) "ports section present: $([bool](Has-Ports $apiBlock))"
Add-Check "No host ports on django" (-not (Has-Ports $djangoBlock)) "ports section present: $([bool](Has-Ports $djangoBlock))"
Add-Check "No host ports on postgres" (-not (Has-Ports $postgresBlock)) "ports section present: $([bool](Has-Ports $postgresBlock))"

# Labels checks
$reactHasPortLabel = ($reactBlock | Where-Object { $_ -match 'traefik.http.services.frontend-react.loadbalancer.server.port=8080' }).Count -gt 0
$apiHasRule = ($apiBlock | Where-Object { $_ -match 'traefik.http.routers.api.rule=Host\(\`\$\{WEBSITE_DOMAIN\}\`\) && PathPrefix\(\`/api\`\)' }).Count -gt 0
$apiHasPortLabel = ($apiBlock | Where-Object { $_ -match 'traefik.http.services.api.loadbalancer.server.port=\$\{FASTAPI_PORT\}' }).Count -gt 0
Add-Check "React Traefik port label" $reactHasPortLabel "frontend-react port label present: $reactHasPortLabel"
Add-Check "API Traefik rule label" $apiHasRule "api rule label present: $apiHasRule"
Add-Check "API Traefik port label" $apiHasPortLabel "api port label present: $apiHasPortLabel"

# 3) Required files
$requiredFiles = @(
  '.\scripts\deploy.ps1',
  '.\api\.Dockerfile', '.\api\requirements.txt', '.\api\main.py',
  '.\django\.Dockerfile', '.\django\requirements.txt', '.\django\manage.py',
  '.\django\project\settings\base.py', '.\django\project\settings\production.py', '.\django\project\urls.py', '.\django\project\wsgi.py'
)
$missingFiles = @()
foreach ($f in $requiredFiles) { if (-not (Test-Path $f)) { $missingFiles += $f } }
Add-Check "Required files exist" ($missingFiles.Count -eq 0) (if ($missingFiles.Count -eq 0) { "All present" } else { "Missing: " + ($missingFiles -join ', ') })

# Output
if ($Json) {
  $checks | ConvertTo-Json -Depth 4 | Write-Output
} else {
  Write-Section "Results"
  foreach ($c in $checks) {
    $status = if ($c.ok) { "OK" } else { "FAIL" }
    Write-Host ("- {0}: {1} ({2})" -f $c.name, $status, $c.details) -ForegroundColor (if ($c.ok) { 'Green' } else { 'Red' })
  }
}

if ($Strict -and ($checks | Where-Object { -not $_.ok }).Count -gt 0) { exit 1 } else { exit 0 }
