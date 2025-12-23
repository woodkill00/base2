param(
  [string]$EnvPath = ".\.env",
  [string]$LogsDir = ".\local_run_logs",
  [switch]$UseLatestTimestamp = $true,
  [string]$Domain = "",
  [string]$ResolveIp = "",
  [int]$TimeoutSec = 8,
  [switch]$Verbose,
  [switch]$Json,
  [switch]$CheckRateLimit,
  [switch]$CheckDjangoProxy,
  [switch]$CheckDjangoAdmin,
  [switch]$CheckCelery,
  [string]$AdminUser = "",
  [string]$AdminPass = "",
  [int]$RateLimitBurst = 20
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Section($msg) {
  if (-not $Json) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
}

function Load-DotEnv([string]$path) {
  if (-not (Test-Path $path)) { return }
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
      [System.Environment]::SetEnvironmentVariable($k, $v, 'Process')
    }
  }
}
function Get-StatusCodeFromHeaders([string[]]$headers) {
  foreach ($line in $headers) {
    if ($line -match '^HTTP/[^ ]+\s+(\d{3})') { return [int]$Matches[1] }
  }
  return 0
}

function Read-HeadersFile([string]$path) {
  if (-not (Test-Path $path)) { return @() }
  return @(Get-Content $path | ForEach-Object { [string]$_ })
}

# Helper to read small file content safely
function Read-FileSafe([string]$path, [int]$tail = 0) {
  if (-not (Test-Path $path)) { return @() }
  try {
    if ($tail -gt 0) { return @(Get-Content -Path $path -Tail $tail | ForEach-Object { [string]$_ }) }
    return @(Get-Content -Path $path | ForEach-Object { [string]$_ })
  } catch { return @('ERROR: unable to read ' + $path) }
}

function Verify-Headers([string[]]$headers, [string]$context) {
  $fail = @()
  if (-not $headers -or $headers.Count -eq 0) { return @("${context}: empty headers") }
  $code = Get-StatusCodeFromHeaders $headers
  if ($context -eq 'root-https' -and $code -ne 200) { $fail += "HTTPS root expected 200, got $code" }
  $expected = @('strict-transport-security:', 'x-content-type-options:', 'x-frame-options:', 'referrer-policy:')
  foreach ($h in $expected) {
    if (-not ($headers | Where-Object { $_ -imatch $h })) { $fail += "Missing security header: $h ($context)" }
  }
  return $fail
}

function Read-StatusFile([string]$path) {
  if (-not (Test-Path $path)) { return 0 }
  try { return [int](Get-Content -Path $path -Raw).Trim() } catch { return 0 }
}

function Get-ArtifactServiceSubdir([string]$fileName) {
  switch -Regex ($fileName) {
    '^DO_userdata\.json$' { return 'digital_ocean' }

    '^compose-ps\.txt$' { return 'docker' }
    '^published-ports\.txt$' { return 'docker' }

    '^traefik-.*\.yml$' { return 'traefik' }
    '^traefik-.*\.template\.yml$' { return 'traefik' }
    '^traefik-.*\.txt$' { return 'traefik' }

    '^django-.*\.txt$' { return 'django' }

    '^api-logs\.txt$' { return 'api' }
    '^api-health(\-slash)?\.(json|status)$' { return 'api' }

    '^curl-.*\.txt$' { return 'smoke' }

    '^schema-compat-check\.(json|err|status)$' { return 'database' }

    '^env-dollar-check\.(txt|status)$' { return 'meta' }
    default { return '' }
  }
}

function Resolve-ArtifactPath([string]$artifactDir, [string]$fileName) {
  $candidates = @()
  $candidates += (Join-Path $artifactDir $fileName)
  $sub = Get-ArtifactServiceSubdir -fileName $fileName
  if ($sub) { $candidates += (Join-Path (Join-Path $artifactDir $sub) $fileName) }

  # Current layout (renamed from logs/)
  $candidates += (Join-Path (Join-Path $artifactDir 'container_logs') $fileName)
  $candidates += (Join-Path (Join-Path (Join-Path $artifactDir 'container_logs') 'build') $fileName)

  # Legacy layout
  $candidates += (Join-Path (Join-Path $artifactDir 'logs') $fileName)
  $candidates += (Join-Path (Join-Path (Join-Path $artifactDir 'logs') 'build') $fileName)

  foreach ($p in $candidates) {
    if (Test-Path $p) { return $p }
  }
  return ''
}

function Verify-StagingCert([string]$staticPath, [string]$dynamicPath) {
  $fail = @()
  $hasStaging = $false
  foreach ($p in @($staticPath, $dynamicPath)) {
    if ($p -and (Test-Path $p)) {
      $content = Get-Content $p -Raw
      if ($content -match 'le-staging') { $hasStaging = $true }
    }
  }
  if (-not $hasStaging) { $fail += "Traefik config does not reference staging cert resolver (le-staging)" }
  return $fail
}

function Verify-TraefikRoutingConfig([string]$dynamicPath) {
  $fail = @()
  if (-not $dynamicPath -or -not (Test-Path $dynamicPath)) {
    return @('Missing traefik dynamic config for routing verification')
  }
  $content = Get-Content -Path $dynamicPath -Raw

  # /static routing present
  if ($content -notmatch "(?m)^\s*static-files:\s*$") { $fail += 'Missing router: static-files' }
  if ($content -notmatch "(?m)^\s*service:\s*django-static\s*$") { $fail += 'Missing service reference: django-static' }

  # Admin routing should be guarded (config-level check; runtime may vary by allowlist)
  if ($content -match "(?m)^\s*django-admin-path:\s*$") {
    if ($content -notmatch 'traefik-basic-auth') { $fail += 'Admin router missing basic auth middleware (traefik-basic-auth)' }
    if ($content -notmatch 'django-admin-allow-ip') { $fail += 'Admin router missing allowlist middleware (django-admin-allow-ip)' }
  } else {
    $fail += 'Missing router: django-admin-path'
  }

  return $fail
}

function Verify-HostPortExposure([string]$composePsPath) {
  $fail = @()
  if (-not $composePsPath -or -not (Test-Path $composePsPath)) {
    return @('Missing compose-ps.txt for host port exposure verification')
  }

  $lines = Get-Content -Path $composePsPath
  foreach ($line in $lines) {
    if ($line -match '0\.0\.0\.0:' -or $line -match '\[::\]:' ) {
      # Allow Traefik only
      if ($line -notmatch 'traefik') {
        $fail += "Non-Traefik service appears to publish host ports: $line"
      }
    }
  }
  return $fail
}

function Curl-Head([string]$url) {
  $args = @('-skI', '--max-time', $TimeoutSec, $url)
  $out = & curl.exe @args 2>&1
  if ($Verbose) { $out | Write-Host }
  return $out -split "`r?`n"
}

function Curl-HeadAuth([string]$url, [string]$user, [string]$pass) {
  $args = @('-skI', '--max-time', $TimeoutSec, '-u', ("{0}:{1}" -f $user, $pass), $url)
  $out = & curl.exe @args 2>&1
  if ($Verbose) { $out | Write-Host }
  return $out -split "`r?`n"
}

# Simple GET utility to capture body and status
function Curl-Get([string]$url) {
  $tmp = [System.IO.Path]::GetTempFileName()
  $args = @('-sk', '--max-time', $TimeoutSec, '-o', $tmp, '-w', '%{http_code}', $url)
  $status = & curl.exe @args 2>&1
  $body = @()
  try { $body = Get-Content -Path $tmp -TotalCount 80 } catch {}
  Remove-Item -Force -ErrorAction SilentlyContinue $tmp
  return [ordered]@{ status = ([int]$status); body = $body }
}

function Try-RateLimit([string]$domain, [int]$burst) {
  $codes = @()
  for ($i = 0; $i -lt $burst; $i++) {
    $hdr = Curl-Head "https://$domain/api/health"
    $codes += (Get-StatusCodeFromHeaders $hdr)
    Start-Sleep -Milliseconds 150
  }
  $saw429 = (@($codes | Where-Object { $_ -eq 429 })).Count -gt 0
  return [ordered]@{ burst = $burst; saw429 = $saw429; codes = $codes }
}

# Init
Write-Section "Post-Deploy Verification"
Load-DotEnv -path $EnvPath
if (-not $Domain) { $Domain = $env:WEBSITE_DOMAIN }
if (-not $Domain) { $Domain = 'localhost' }

# Locate artifact folder
$artifactDir = $LogsDir
if ($UseLatestTimestamp) {
  if (Test-Path $LogsDir) {
    $cands = @(
      Get-ChildItem -Path $LogsDir -Directory |
        Where-Object {
          # New format: <ip>-yyyyMMdd_HHmmss
          $_.Name -match '^(?:\d{1,3}\.){3}\d{1,3}-\d{8}_\d{6}$' -or
          # Legacy format: yyyyMMdd_HHmmss
          $_.Name -match '^\d{8}_\d{6}$'
        }
    )
    if ($cands.Count -gt 0) {
      $latest = $cands |
        Sort-Object -Property @{ Expression = {
            if ($_.Name -match '(\d{8}_\d{6})$') { $Matches[1] } else { $_.Name }
          }
        }
      $artifactDir = $latest[-1].FullName
    }
  }
}
if (-not $Json) { Write-Host "Using artifacts at: $artifactDir" -ForegroundColor Yellow }

$failures = @()

# Check presence of expected artifacts
$expectedFiles = @(
  'compose-ps.txt',
  'published-ports.txt',
  'traefik-env.txt',
  'traefik-static.yml',
  'traefik-dynamic.yml',
  'traefik-ls.txt',
  'traefik-logs.txt',
  'api-logs.txt',
  'django-migrate.txt',
  'django-check-deploy.txt',
  'schema-compat-check.json',
  'schema-compat-check.status',
  'curl-root.txt',
  'curl-api.txt',
  'curl-api-health.txt',
  'curl-api-health-slash.txt',
  'api-health.json',
  'api-health.status',
  'api-health-slash.json',
  'api-health-slash.status',
  'traefik-dynamic.template.yml',
  'traefik-static.template.yml'
)
foreach ($f in $expectedFiles) {
  $p = Resolve-ArtifactPath -artifactDir $artifactDir -fileName $f
  if (-not $p) { $failures += "Missing artifact: $f" }
}

# Verify headers from remote artifacts
$rootHdr = Read-HeadersFile (Resolve-ArtifactPath -artifactDir $artifactDir -fileName 'curl-root.txt')
$apiHdr  = Read-HeadersFile (Resolve-ArtifactPath -artifactDir $artifactDir -fileName 'curl-api.txt')
$apiHdrHealth = Read-HeadersFile (Resolve-ArtifactPath -artifactDir $artifactDir -fileName 'curl-api-health.txt')
$apiHdrHealthSlash = Read-HeadersFile (Resolve-ArtifactPath -artifactDir $artifactDir -fileName 'curl-api-health-slash.txt')
$failures += Verify-Headers $rootHdr 'root-https'
$failures += Verify-Headers $apiHdr 'api-https'

# Also verify explicit health endpoints headers for clarity
$failures += Verify-Headers $apiHdrHealth 'api-https-health'
$failures += Verify-Headers $apiHdrHealthSlash 'api-https-health-slash'

# Verify staging cert resolver
$staticYml = Resolve-ArtifactPath -artifactDir $artifactDir -fileName 'traefik-static.yml'
$dynamicYml = Resolve-ArtifactPath -artifactDir $artifactDir -fileName 'traefik-dynamic.yml'
$failures += Verify-StagingCert $staticYml $dynamicYml

# Verify required routing and exposure invariants from artifacts
$failures += Verify-TraefikRoutingConfig $dynamicYml
$failures += Verify-HostPortExposure (Resolve-ArtifactPath -artifactDir $artifactDir -fileName 'compose-ps.txt')

# Schema compatibility check (post-migration)
$schemaStatusPath = Resolve-ArtifactPath -artifactDir $artifactDir -fileName 'schema-compat-check.status'
if (Test-Path $schemaStatusPath) {
  try {
    $schemaExit = [int](Get-Content -Path $schemaStatusPath -Raw).Trim()
    if ($schemaExit -ne 0) {
      $failures += "Schema compatibility check failed (schema-compat-check.status=$schemaExit)"
    }
  } catch {
    $failures += "Schema compatibility check status unreadable: $($_.Exception.Message)"
  }
} else {
  $failures += 'Missing schema compatibility status (schema-compat-check.status)'
}

# API health must be 200 via GET (HEAD may be 405, and /api may redirect).
$apiGetStatus = Read-StatusFile (Resolve-ArtifactPath -artifactDir $artifactDir -fileName 'api-health.status')
$apiGetStatusSlash = Read-StatusFile (Resolve-ArtifactPath -artifactDir $artifactDir -fileName 'api-health-slash.status')
if (($apiGetStatus -ne 200) -and ($apiGetStatusSlash -ne 200)) {
  $failures += "API health GET expected 200, got $apiGetStatus (no-slash) / $apiGetStatusSlash (slash)"
}

# Local smoke tests
Write-Section "Local Smoke Tests"
try {
  $smokeArgs = @{ EnvPath = $EnvPath; Domain = $Domain; TimeoutSec = 5 }
  if ($ResolveIp) { $smokeArgs.ResolveIp = $ResolveIp }
  & ./scripts/smoke-tests.ps1 @smokeArgs | Out-Null
} catch {
  $failures += "Local smoke tests failed: $($_.Exception.Message)"
}

# Final result
$result = [ordered]@{
  domain = $Domain
  logsDir = $LogsDir
  artifactDir = $artifactDir
  expectedFiles = $expectedFiles
  missingFiles = @()
  headers = [ordered]@{
    root = [ordered]@{
      status = (Get-StatusCodeFromHeaders $rootHdr)
      missingHeaders = (Verify-Headers $rootHdr 'root-https' | Where-Object { $_ -match '^Missing security header' })
    }
    api = [ordered]@{
      status = $apiGetStatus
      missingHeaders = (Verify-Headers $apiHdr 'api-https' | Where-Object { $_ -match '^Missing security header' })
    }
  }
  stagingResolverOK = (@(Verify-StagingCert $staticYml $dynamicYml)).Length -eq 0
  localSmokePassed = $true
  rateLimitCheck = [ordered]@{ enabled = $false; burst = 0; saw429 = $false }
  djangoProxy = [ordered]@{ enabled = $false; status = 0; bodySnippet = @() }
  adminCheck = [ordered]@{ enabled = $false; host = ''; statusNoAuth = 0; statusWithAuth = 0 }
  celeryCheck = [ordered]@{ enabled = $false; host = ''; statusNoAuth = 0; statusWithAuth = 0 }
  failures = @()
}

# Diagnostics: if API health is non-200, include API logs snippet
$apiStatus = $apiGetStatus
if (($apiGetStatus -ne 200) -and ($apiGetStatusSlash -ne 200)) {
  $apiLogsPath = Resolve-ArtifactPath -artifactDir $artifactDir -fileName 'api-logs.txt'
  $snippet = @('api-logs.txt not found')
  if ($apiLogsPath -and (Test-Path $apiLogsPath)) { $snippet = Read-FileSafe $apiLogsPath 80 }

  # Include GET health status and body snippets for deeper insight
  $getStatusPath = Resolve-ArtifactPath -artifactDir $artifactDir -fileName 'api-health.status'
  $getBodyPath = Resolve-ArtifactPath -artifactDir $artifactDir -fileName 'api-health.json'
  $getStatusSlashPath = Resolve-ArtifactPath -artifactDir $artifactDir -fileName 'api-health-slash.status'
  $getBodySlashPath = Resolve-ArtifactPath -artifactDir $artifactDir -fileName 'api-health-slash.json'
  $getStatus = $apiGetStatus
  $getStatusSlash = $apiGetStatusSlash
  $bodySnippet = if ($getBodyPath) { Read-FileSafe $getBodyPath 40 } else { @() }
  $bodySnippetSlash = if ($getBodySlashPath) { Read-FileSafe $getBodySlashPath 40 } else { @() }

  # Traefik routing parsing: extract api router service and service URL if possible
  $dynPath = Resolve-ArtifactPath -artifactDir $artifactDir -fileName 'traefik-dynamic.yml'
  $apiRouterService = ''
  $apiServiceURL = ''
  if ($dynPath -and (Test-Path $dynPath)) {
    try {
      $dynLines = Get-Content -Path $dynPath
      # naive parsing: find 'routers:' then 'api:' block and service
      for ($i=0; $i -lt $dynLines.Length; $i++) {
        $line = $dynLines[$i]
        if ($line -match '^\s*api:\s*$') {
          for ($j=$i; $j -lt [Math]::Min($i+20, $dynLines.Length); $j++) {
            $l2 = $dynLines[$j]
            if ($l2 -match '^\s*service:\s*(.+)') { $apiRouterService = ($l2 -replace '^\s*service:\s*','').Trim(); break }
          }
        }
        if ($line -match '^\s*services:\s*$') {
          # find services api url
          for ($k=$i; $k -lt [Math]::Min($i+100, $dynLines.Length); $k++) {
            $l3 = $dynLines[$k]
            if ($l3 -match '^\s*api:\s*$') {
              for ($m=$k; $m -lt [Math]::Min($k+50, $dynLines.Length); $m++) {
                $l4 = $dynLines[$m]
                if ($l4 -match '^\s*url:\s*(.+)') { $apiServiceURL = ($l4 -replace '^\s*url:\s*','').Trim(); break }
              }
            }
          }
        }
      }
    } catch {}
  }

  $result.diagnostics = [ordered]@{
    apiHealthStatus = $apiStatus
    apiLogsSnippet = $snippet
    apiHead = [ordered]@{ health = (Get-StatusCodeFromHeaders $apiHdrHealth); healthSlash = (Get-StatusCodeFromHeaders $apiHdrHealthSlash) }
    apiGet = [ordered]@{ status = $getStatus; statusSlash = $getStatusSlash; bodySnippet = $bodySnippet; bodySnippetSlash = $bodySnippetSlash }
    traefikRouting = [ordered]@{ apiRouterService = $apiRouterService; apiServiceURL = $apiServiceURL }
  }
}

foreach ($f in $expectedFiles) {
  $p = Resolve-ArtifactPath -artifactDir $artifactDir -fileName $f
  if (-not $p) { $result.missingFiles += $f }
}

if ($failures.Count -gt 0) { $result.failures = $failures; $result.localSmokePassed = $false }

if ($CheckRateLimit) {
  $rl = Try-RateLimit $Domain $RateLimitBurst
  $result.rateLimitCheck = [ordered]@{ enabled = $true; burst = $rl.burst; saw429 = $rl.saw429; codes = $rl.codes }
}

# Optional: Test Django proxy endpoint via edge
if ($CheckDjangoProxy) {
  $result.djangoProxy = [ordered]@{
    enabled = $true
    status = 0
    bodySnippet = @('Django proxy endpoint check removed; schema compatibility check will be implemented under N007.')
  }
}

# Optional: Test Django admin router via edge
if ($CheckDjangoAdmin) {
  $sub = $env:DJANGO_ADMIN_DNS_LABEL
  if (-not $sub) { $sub = 'admin' }
  $AdminHost = "$sub.$Domain"
  $noAuthHdr = Curl-Head "https://$AdminHost/admin"
  $noAuthStatus = Get-StatusCodeFromHeaders $noAuthHdr
  $withAuthStatus = 0
  if ($AdminUser -and $AdminPass) {
    $authHdr = Curl-HeadAuth "https://$AdminHost/admin" $AdminUser $AdminPass
    $withAuthStatus = Get-StatusCodeFromHeaders $authHdr
  }
  $result.adminCheck = [ordered]@{ enabled = $true; host = $AdminHost; statusNoAuth = $noAuthStatus; statusWithAuth = $withAuthStatus }
  if ($noAuthStatus -ne 401) { $failures += "Django admin expected 401 without auth, got $noAuthStatus ($AdminHost)" }
  if ($AdminUser -and $AdminPass) {
    if (@(200,302) -notcontains $withAuthStatus) { $failures += "Django admin expected 200/302 with auth, got $withAuthStatus ($AdminHost)" }
  }
}

# Optional: Test Flower (Celery) dashboard via edge (non-production only)
if ($CheckCelery) {
  $sub = $env:FLOWER_DNS_LABEL
  if (-not $sub) { $sub = 'flower' }
  $FlowerHost = "$sub.$Domain"
  $noAuthHdr = Curl-Head "https://$FlowerHost/"
  $noAuthStatus = Get-StatusCodeFromHeaders $noAuthHdr
  $withAuthStatus = 0
  if ($AdminUser -and $AdminPass) {
    $authHdr = Curl-HeadAuth "https://$FlowerHost/" $AdminUser $AdminPass
    $withAuthStatus = Get-StatusCodeFromHeaders $authHdr
  }
  # Try a roundtrip task via API if available
  $taskId = ''
  $taskState = ''
  $taskResult = $null
  try {
    $ping = Curl-Get "https://$Domain/api/celery/ping"
    if ($ping.status -eq 200) {
      $js = ($ping.body -join "") | ConvertFrom-Json
      $taskId = [string]$js.task_id
      # poll up to ~10s
      $attempts = 20
      for ($i=0; $i -lt $attempts; $i++) {
        Start-Sleep -Milliseconds 500
        $res = Curl-Get ("https://{0}/api/celery/result/{1}" -f $Domain, $taskId)
        if ($res.status -eq 200) {
          $rj = ($res.body -join "") | ConvertFrom-Json
          $taskState = [string]$rj.state
          if ($rj.ready -and $rj.successful -and $rj.result -eq 'pong') {
            $taskResult = 'pong'
            break
          }
        }
      }
    }
  } catch {}

  $result.celeryCheck = [ordered]@{
    enabled = $true
    host = $FlowerHost
    statusNoAuth = $noAuthStatus
    statusWithAuth = $withAuthStatus
    task = [ordered]@{ id = $taskId; state = $taskState; result = $taskResult }
  }
  if ($noAuthStatus -ne 401) { $failures += "Flower expected 401 without auth, got $noAuthStatus ($FlowerHost)" }
  if ($AdminUser -and $AdminPass) {
    if (@(200,302) -notcontains $withAuthStatus) { $failures += "Flower expected 200/302 with auth, got $withAuthStatus ($FlowerHost)" }
  }
  if (-not $taskResult) { $failures += "Celery ping task did not complete successfully" }
}

if ($Json) {
  $ok = ($failures.Count -eq 0 -and $result.missingFiles.Count -eq 0 -and $result.stagingResolverOK)
  $result.success = $ok
  $result.timestamp = (Get-Date).ToString('s')
  $jsonStr = $result | ConvertTo-Json -Depth 6
  Write-Output $jsonStr
  if ($ok) { exit 0 } else { exit 1 }
} else {
  if ($failures.Count -gt 0 -or $result.missingFiles.Count -gt 0 -or -not $result.stagingResolverOK) {
    Write-Host "Failures:" -ForegroundColor Red
    $result.missingFiles | ForEach-Object { Write-Host " - Missing artifact: $_" -ForegroundColor Red }
    $failures | ForEach-Object { Write-Host " - $_" -ForegroundColor Red }
    if (-not $result.stagingResolverOK) { Write-Host " - Traefik not using staging resolver (le-staging)" -ForegroundColor Red }
    exit 1
  }
  Write-Host "Post-deploy verification passed." -ForegroundColor Green
  exit 0
}
