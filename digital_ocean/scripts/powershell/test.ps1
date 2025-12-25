param(
  [string]$EnvPath = ".\.env",
  [string]$LogsDir = ".\local_run_logs",
  [switch]$UseLatestTimestamp = $true,
  [string]$Domain = "",
  [string]$ResolveIp = "",
  [string]$ExpectedIpv4 = "",
  [string]$ExpectedIpv6 = "",
  [int]$TimeoutSec = 8,
  [switch]$Verbose,
  [switch]$Json,
  [switch]$All,
  [switch]$CheckTls,
  [switch]$CheckOpenApi,
  [switch]$CheckRateLimit,
  [switch]$CheckDjangoProxy,
  [switch]$CheckDjangoAdmin,
  [switch]$CheckPgAdmin,
  [switch]$CheckTraefikDashboard,
  [switch]$CheckDns,
  [switch]$CheckCelery,
  [string]$AdminUser = "",
  [string]$AdminPass = "",
  [int]$RateLimitBurst = 20
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Ensure relative paths work regardless of where the script is invoked from.
$script:RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
Push-Location $script:RepoRoot

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
    if ($line -match '(?i)HTTP/[^ ]+\s+(\d{3})') { return [int]$Matches[1] }
  }
  return 0
}

function Get-CertDnsNames([System.Security.Cryptography.X509Certificates.X509Certificate2]$cert) {
  $names = @()
  if (-not $cert) { return $names }
  try {
    foreach ($ext in $cert.Extensions) {
      if ($ext.Oid -and $ext.Oid.Value -eq '2.5.29.17') {
        $formatted = $ext.Format($true)
        foreach ($line in ($formatted -split "`r?`n")) {
          $t = ($line + '').Trim()
          if ($t -match '(?i)DNS\s*Name\s*=\s*(.+)$') {
            $n = ($Matches[1] + '').Trim()
            if ($n) { $names += $n }
          }
        }
      }
    }
  } catch {}
  return @($names | Where-Object { $_ } | Select-Object -Unique)
}

function Check-TlsCert([string]$artifactDir, [string]$domain) {
  $fail = @()
  $payload = [ordered]@{
    domain = $domain
    resolveIp = $ResolveIp
    notBefore = ''
    notAfter = ''
    daysRemaining = $null
    subject = ''
    issuer = ''
    dnsNames = @()
    ok = $false
    error = ''
  }

  $client = $null
  $stream = $null
  $ssl = $null
  try {
    $ipToConnect = $domain
    if ($ResolveIp) { $ipToConnect = $ResolveIp }

    $client = New-Object System.Net.Sockets.TcpClient
    $client.ReceiveTimeout = $TimeoutSec * 1000
    $client.SendTimeout = $TimeoutSec * 1000
    $client.Connect($ipToConnect, 443)
    $stream = $client.GetStream()

    $sslCallback = {
      param($sender, $certificate, $chain, $sslPolicyErrors)
      return $true
    }
    $ssl = New-Object System.Net.Security.SslStream($stream, $false, $sslCallback)
    $ssl.AuthenticateAsClient($domain)

    $remoteCert = $ssl.RemoteCertificate
    if (-not $remoteCert) { throw 'No remote certificate presented' }
    $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($remoteCert)

    $payload.subject = $cert.Subject
    $payload.issuer = $cert.Issuer
    $payload.notBefore = $cert.NotBefore.ToString('o')
    $payload.notAfter = $cert.NotAfter.ToString('o')
    $payload.daysRemaining = [math]::Floor(($cert.NotAfter.ToUniversalTime() - (Get-Date).ToUniversalTime()).TotalDays)
    $payload.dnsNames = @(Get-CertDnsNames -cert $cert)

    if ($cert.NotAfter.ToUniversalTime() -le (Get-Date).ToUniversalTime()) {
      $fail += "TLS cert is expired (notAfter=$($payload.notAfter))"
    }
    if ($cert.NotBefore.ToUniversalTime() -gt (Get-Date).ToUniversalTime().AddMinutes(5)) {
      $fail += "TLS cert not yet valid (notBefore=$($payload.notBefore))"
    }

    # Require that the cert covers the apex domain explicitly.
    if (-not ($payload.dnsNames -contains $domain)) {
      $fail += "TLS cert SAN does not include ${domain} (dnsNames=$($payload.dnsNames -join ','))"
    }

    $payload.ok = ($fail.Count -eq 0)
  } catch {
    $payload.ok = $false
    $payload.error = [string]$_.Exception.Message
    $fail += "TLS check failed: $($_.Exception.Message)"
  } finally {
    try { if ($ssl) { $ssl.Dispose() } } catch {}
    try { if ($stream) { $stream.Dispose() } } catch {}
    try { if ($client) { $client.Close() } } catch {}
  }

  Write-ServiceArtifact -artifactDir $artifactDir -serviceName 'traefik' -fileName 'tls-cert.json' -content $payload
  return $fail
}

function Check-OpenApi([string]$artifactDir, [string]$domain) {
  $fail = @()
  $u = "https://$domain/api/openapi.json"
  $payload = [ordered]@{ url = $u; status = 0; ok = $false; openapi = ''; title = ''; pathsCount = 0; sessionCookieName = '' }

  try {
    $resp = Curl-Get $u
    $payload.status = [int]$resp.status
    if ($resp.status -ne 200) {
      $fail += "OpenAPI expected 200, got $($resp.status) ($u)"
    }

    $raw = ($resp.body -join "")
    Write-ServiceArtifact -artifactDir $artifactDir -serviceName 'api' -fileName 'openapi.json' -content $raw

    $doc = $raw | ConvertFrom-Json
    if (-not $doc) { throw 'OpenAPI JSON parsed to null' }
    if (-not $doc.openapi) { $fail += 'OpenAPI doc missing openapi field' }
    if (-not $doc.info -or -not $doc.info.title) { $fail += 'OpenAPI doc missing info.title' }
    if (-not $doc.paths) { $fail += 'OpenAPI doc missing paths' }

    $payload.openapi = [string]$doc.openapi
    $payload.title = [string]$doc.info.title
    try {
      $pc = 0
      foreach ($p in $doc.paths.PSObject.Properties) { $pc++ }
      $payload.pathsCount = $pc
      if ($pc -le 0) { $fail += 'OpenAPI doc has zero paths' }
    } catch {}

    # Validate session cookie governance aligns with contract
    try {
      $cookieName = ''
      if ($doc.components -and $doc.components.securitySchemes -and $doc.components.securitySchemes.SessionCookie) {
        $cookieName = '' + $doc.components.securitySchemes.SessionCookie.name
      }
      $payload.sessionCookieName = $cookieName
      if (-not $cookieName) {
        $fail += 'OpenAPI missing components.securitySchemes.SessionCookie.name'
      } elseif ($cookieName -ne 'base2_session') {
        $fail += "OpenAPI session cookie name mismatch: expected base2_session, got $cookieName"
      }
    } catch { $fail += 'Failed to validate OpenAPI session cookie name' }

    $payload.ok = ($fail.Count -eq 0)
  } catch {
    $payload.ok = $false
    $fail += "OpenAPI check failed: $($_.Exception.Message)"
  }

  Write-ServiceArtifact -artifactDir $artifactDir -serviceName 'api' -fileName 'openapi-validation.json' -content $payload
  return $fail
}

function Get-OpenApiContractPaths([string]$contractPath) {
  if (-not $contractPath -or -not (Test-Path $contractPath)) { return @() }
  $lines = @(Get-Content -Path $contractPath | ForEach-Object { [string]$_ })
  $inPaths = $false
  $pathsIndent = $null
  $keys = @()

  foreach ($rawLine in $lines) {
    $line = ($rawLine + '')
    $trim = $line.Trim()
    if (-not $trim) { continue }
    if ($trim.StartsWith('#')) { continue }

    if (-not $inPaths) {
      if ($line -match '^\s*paths\s*:\s*$') {
        $inPaths = $true
        $pathsIndent = ($line.Length - $line.TrimStart().Length)
      }
      continue
    }

    $indent = ($line.Length - $line.TrimStart().Length)
    if ($pathsIndent -ne $null -and $indent -le $pathsIndent -and ($line -notmatch '^\s*#')) {
      break
    }

    if ($line -match '^\s{2,}([\x27\"]?)(/[^\x27"\s:]+)\1\s*:\s*$') {
      $k = ($Matches[2] + '').Trim()
      if ($k) { $keys += $k }
    }
  }

  return @($keys | Select-Object -Unique)
}

function Check-OpenApiContract([string]$artifactDir, [string]$contractPath) {
  $fail = @()
  $payload = [ordered]@{
    contractPath = $contractPath
    ok = $false
    contractPathsCount = 0
    runtimePathsCount = 0
    missingPaths = @()
    error = ''
  }

  try {
    $contractPaths = @(Get-OpenApiContractPaths -contractPath $contractPath)
    $payload.contractPathsCount = $contractPaths.Count
    if ($contractPaths.Count -le 0) { $fail += 'OpenAPI contract has zero parsed paths' }

    $runtimePath = Resolve-ArtifactPath -artifactDir $artifactDir -fileName 'openapi.json'
    if (-not $runtimePath) { throw 'Runtime openapi.json artifact not found' }
    $raw = Get-Content -Path $runtimePath -Raw
    $doc = $raw | ConvertFrom-Json
    if (-not $doc -or -not $doc.paths) { throw 'Runtime OpenAPI missing paths' }

    $runtimePaths = @()
    foreach ($p in $doc.paths.PSObject.Properties) { $runtimePaths += [string]$p.Name }
    $payload.runtimePathsCount = $runtimePaths.Count
    if ($runtimePaths.Count -le 0) { $fail += 'Runtime OpenAPI has zero paths' }

    $missing = @()
    foreach ($cp in $contractPaths) {
      $rp = $cp
      if ($rp -like '/api/*') { $rp = $rp.Substring(4) }
      if ($runtimePaths -notcontains $rp) { $missing += $cp }
    }
    $payload.missingPaths = @($missing)
    if ($missing.Count -gt 0) {
      $fail += "OpenAPI contract paths missing from runtime: $($missing -join ', ')"
    }

    $payload.ok = ($fail.Count -eq 0)
  } catch {
    $payload.ok = $false
    $payload.error = [string]$_.Exception.Message
    $fail += "OpenAPI contract check failed: $($_.Exception.Message)"
  }

  Write-ServiceArtifact -artifactDir $artifactDir -serviceName 'api' -fileName 'openapi-contract-check.json' -content $payload
  return [pscustomobject]@{ payload = $payload; failures = @($fail) }
}

function Check-GuardedEndpoints([string]$artifactDir, [string]$domain) {
  $fail = @()
  $endpoints = @(
    [ordered]@{ name = 'usersMe'; method = 'GET'; url = "https://$domain/api/users/me"; status = 0; ok = $false },
    [ordered]@{ name = 'usersLogout'; method = 'POST'; url = "https://$domain/api/users/logout"; status = 0; ok = $false }
  )

  foreach ($ep in $endpoints) {
    try {
      $status = 0
      if ($ep.method -eq 'POST') {
        $resp = Curl-PostJson $ep.url '{}'
        $status = [int]$resp.status
      } else {
        $status = [int](Curl-GetStatusOnly $ep.url)
      }
      $ep.status = $status
      $ep.ok = (Get-ExpectedGuardedNoAuthOk $status)
      if (-not $ep.ok) {
        $fail += "Guarded endpoint expected 401/403 without auth, got $status ($($ep.method) $($ep.url))"
      }
    } catch {
      $ep.status = 0
      $ep.ok = $false
      $fail += "Guarded endpoint probe failed: $($_.Exception.Message) ($($ep.method) $($ep.url))"
    }
  }

  $payload = [ordered]@{ ok = ($fail.Count -eq 0); endpoints = @($endpoints) }
  Write-ServiceArtifact -artifactDir $artifactDir -serviceName 'meta' -fileName 'guarded-endpoints.json' -content $payload
  return [pscustomobject]@{ payload = $payload; failures = @($fail) }
}

function Check-ArtifactCompleteness([string]$artifactDir, [string[]]$expectedFiles) {
  $fail = @()
  $found = [ordered]@{}
  $missing = @()
  foreach ($f in $expectedFiles) {
    $p = Resolve-ArtifactPath -artifactDir $artifactDir -fileName $f
    $exists = ($p -and (Test-Path $p))
    $found[$f] = [ordered]@{ exists = [bool]$exists; path = [string]$p }
    if (-not $exists) { $missing += $f }
  }

  if ($missing.Count -gt 0) {
    $fail += "Missing required artifacts: $($missing -join ', ')"
  }

  $payload = [ordered]@{ ok = ($missing.Count -eq 0); expected = @($expectedFiles); found = $found; missing = @($missing) }
  Write-ServiceArtifact -artifactDir $artifactDir -serviceName 'meta' -fileName 'artifact-completeness.json' -content $payload
  return [pscustomobject]@{ payload = $payload; failures = @($fail) }
}

function Ensure-Dir([string]$path) {
  if (-not $path) { return }
  if (-not (Test-Path $path)) { New-Item -ItemType Directory -Path $path -Force | Out-Null }
}

function Get-ServiceOutDir([string]$artifactDir, [string]$serviceName) {
  if (-not $artifactDir) { return '' }
  if (-not $serviceName) { $serviceName = 'meta' }
  $d = Join-Path $artifactDir $serviceName
  Ensure-Dir $d
  return $d
}

function Write-ServiceArtifact([string]$artifactDir, [string]$serviceName, [string]$fileName, [object]$content) {
  if (-not $artifactDir -or -not $fileName) { return }
  $outDir = Get-ServiceOutDir -artifactDir $artifactDir -serviceName $serviceName
  $path = Join-Path $outDir $fileName
  try {
    if ($content -is [string]) {
      Set-Content -Path $path -Value $content -Encoding UTF8
    } else {
      $json = $content | ConvertTo-Json -Depth 8
      Set-Content -Path $path -Value $json -Encoding UTF8
    }
  } catch {}
}

function Read-HeadersFile([string]$path) {
  if (-not $path) { return @() }
  if (-not (Test-Path $path)) { return @() }
  return @(Get-Content $path | ForEach-Object { [string]$_ })
}

# Helper to read small file content safely
function Read-FileSafe([string]$path, [int]$tail = 0) {
  if (-not $path) { return @() }
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
  if (-not $path) { return 0 }
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

    '^openapi\.json$' { return 'api' }
    '^openapi-validation\.json$' { return 'api' }
    '^openapi-contract-check\.json$' { return 'api' }

    '^curl-.*\.txt$' { return 'smoke' }

    '^schema-compat-check\.(json|err|status)$' { return 'database' }

    '^celery-(ping|result)\.json$' { return 'celery' }

    '^env-dollar-check\.(txt|status)$' { return 'meta' }
    '^post-deploy-report\.json$' { return 'meta' }
    '^admin-host-path-guard\.json$' { return 'meta' }
    '^guarded-endpoints\.json$' { return 'meta' }
    '^artifact-completeness\.json$' { return 'meta' }
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

function Verify-ComposePsHealth([string]$composePsPath) {
  $fail = @()
  if (-not $composePsPath -or -not (Test-Path $composePsPath)) {
    return @('Missing compose-ps.txt for container health verification')
  }

  $expectedServices = @(
    'traefik','nginx','nginx-static','react-app',
    'django','api','postgres','redis','pgadmin',
    'celery-worker','celery-beat','flower'
  )

  $text = (Get-Content -Path $composePsPath -Raw)
  foreach ($svc in $expectedServices) {
    if ($text -notmatch "(?im)^.*\s${svc}\s+.*$") {
      $fail += "compose-ps.txt missing service row: $svc"
    }
  }

  # Health expectations: most should be healthy; allow pgadmin to be 'health: starting' briefly.
  $mustBeHealthy = @('traefik','nginx','django','api','postgres','redis','react-app','celery-worker','celery-beat','flower')
  foreach ($svc in $mustBeHealthy) {
    if ($text -notmatch "(?im)\b${svc}\b.*\(healthy\)") {
      $fail += "Service not healthy in compose-ps.txt: $svc"
    }
  }
  return $fail
}

function Get-ExpectedGuardedNoAuthOk([int]$status) {
  return (@(401,403) -contains $status)
}

function Invoke-ValidateDnsJson([string]$domain, [string]$recordType, [string]$name) {
  $args = @('.\\digital_ocean\\validate_dns.py','--domain',$domain,'--json')
  if ($recordType) { $args += @('--record-type',$recordType) }
  if ($name) { $args += @('--name',$name) }

  # Prefer the repo venv Python (deploy creates .\.venv\Scripts\python.exe with required deps).
  $repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
  $venvPy = Join-Path $repoRoot '.venv\Scripts\python.exe'
  $pythonExe = 'python'
  if (Test-Path $venvPy) { $pythonExe = $venvPy }

  Push-Location $repoRoot
  try {
    $rawLines = & $pythonExe @args 2>&1
    $raw = ($rawLines -join "`n").Trim()
  } finally {
    Pop-Location
  }
  if (-not $raw) { throw "validate_dns.py returned empty output" }
  try { return ($raw | ConvertFrom-Json) } catch { throw "validate_dns.py returned non-JSON: $raw" }
}

function Check-DoDns([string]$artifactDir, [string]$domain, [string]$expectedIpv4, [string]$expectedIpv6) {
  $fail = @()
  $traefikLabel = $env:TRAEFIK_DNS_LABEL
  if (-not $traefikLabel) { $traefikLabel = 'traefik' }
  $pgadminLabel = $env:PGADMIN_DNS_LABEL
  if (-not $pgadminLabel) { $pgadminLabel = 'pgadmin' }
  $adminLabel = $env:DJANGO_ADMIN_DNS_LABEL
  if (-not $adminLabel) { $adminLabel = 'admin' }
  $flowerLabel = $env:FLOWER_DNS_LABEL
  if (-not $flowerLabel) { $flowerLabel = 'flower' }

  $labels = [ordered]@{
    at = '@'
    www = 'www'
    traefik = $traefikLabel
    pgadmin = $pgadminLabel
    admin = $adminLabel
    flower = $flowerLabel
  }

  $payload = [ordered]@{ domain = $domain; expectedIpv4 = $expectedIpv4; expectedIpv6 = $expectedIpv6; names = @{}; } 
  try {
    foreach ($k in $labels.Keys) {
      $name = $labels[$k]
      $a = Invoke-ValidateDnsJson -domain $domain -recordType 'A' -name $name
      $aaaa = Invoke-ValidateDnsJson -domain $domain -recordType 'AAAA' -name $name
      $aVals = @($a.records | ForEach-Object { $_.data } | Where-Object { $_ })
      $aaaaVals = @($aaaa.records | ForEach-Object { $_.data } | Where-Object { $_ })
      $payload.names[$name] = [ordered]@{ A = $aVals; AAAA = $aaaaVals }

      if (-not $aVals -or $aVals.Count -eq 0) {
        $fail += "DO DNS missing A record for $name"
      } elseif ($expectedIpv4 -and ($aVals -notcontains $expectedIpv4)) {
        $fail += "DO DNS A mismatch for ${name}: expected $expectedIpv4, got $($aVals -join ',')"
      }

      # AAAA is optional for www in current setup; enforce for others if expectedIpv6 provided.
      $needsAAAA = ($name -ne 'www')
      if ($expectedIpv6 -and $needsAAAA) {
        if (-not $aaaaVals -or $aaaaVals.Count -eq 0) {
          $fail += "DO DNS missing AAAA record for $name"
        } elseif ($aaaaVals -notcontains $expectedIpv6) {
          $fail += "DO DNS AAAA mismatch for ${name}: expected $expectedIpv6, got $($aaaaVals -join ',')"
        }
      }
    }
  } catch {
    $fail += "DO DNS check failed: $($_.Exception.Message)"
  }
  Write-ServiceArtifact -artifactDir $artifactDir -serviceName 'digital_ocean' -fileName 'dns-records.json' -content $payload
  return $fail
}

function Check-ClientDns([string]$artifactDir, [string]$domain, [string]$expectedIpv4) {
  # This checks what *this machine's resolver* returns (i.e., what the user/browser will likely hit),
  # which is exactly where stale caches/split-horizon issues show up.
  $fail = @()

  $traefikLabel = $env:TRAEFIK_DNS_LABEL
  if (-not $traefikLabel) { $traefikLabel = 'traefik' }
  $pgadminLabel = $env:PGADMIN_DNS_LABEL
  if (-not $pgadminLabel) { $pgadminLabel = 'pgadmin' }
  $adminLabel = $env:DJANGO_ADMIN_DNS_LABEL
  if (-not $adminLabel) { $adminLabel = 'admin' }
  $flowerLabel = $env:FLOWER_DNS_LABEL
  if (-not $flowerLabel) { $flowerLabel = 'flower' }

  $labels = [ordered]@{
    at = '@'
    www = 'www'
    traefik = $traefikLabel
    pgadmin = $pgadminLabel
    admin = $adminLabel
    flower = $flowerLabel
  }

  $dnsServers = @()
  try {
    $dnsServers = @(
      Get-DnsClientServerAddress -AddressFamily IPv4 -ErrorAction Stop |
        ForEach-Object { $_.ServerAddresses } |
        Where-Object { $_ }
    )
  } catch {}

  $payload = [ordered]@{
    domain = $domain
    expectedIpv4 = $expectedIpv4
    dnsServers = @($dnsServers)
    names = @{}
  }

  foreach ($k in $labels.Keys) {
    $name = $labels[$k]
    $fqdn = ''
    if ($name -eq '@') {
      $fqdn = $domain
    } else {
      $fqdn = "{0}.{1}" -f $name, $domain
    }

    $vals = @()
    $err = ''
    try {
      $res = Resolve-DnsName -Name $fqdn -Type A -ErrorAction Stop
      $vals = @($res | ForEach-Object { $_.IPAddress } | Where-Object { $_ } | Select-Object -Unique)
    } catch {
      $err = [string]$_.Exception.Message
    }

    $payload.names[$fqdn] = [ordered]@{ A = $vals; error = $err }

    if ($err) {
      $fail += "Client DNS lookup failed for ${fqdn}: $err"
      continue
    }
    if (-not $vals -or $vals.Count -eq 0) {
      $fail += "Client DNS missing A record for ${fqdn}"
      continue
    }
    if ($expectedIpv4 -and ($vals -notcontains $expectedIpv4)) {
      $fail += "Client DNS A mismatch for ${fqdn}: expected $expectedIpv4, got $($vals -join ',')"
    }
  }

  Write-ServiceArtifact -artifactDir $artifactDir -serviceName 'digital_ocean' -fileName 'client-dns.json' -content $payload
  return $fail
}

function Get-CurlResolveArgs([string]$url) {
  $ip = $ResolveIp
  if (-not $ip) { $ip = $ExpectedIpv4 }
  if (-not $ip) { return @() }

  try { $ip = $ip.Trim() } catch {}
  if (-not $ip) { return @() }

  # Avoid [System.Uri] parsing here; it can behave inconsistently in Windows PowerShell 5.1
  # with certain inputs and leads to missing --resolve args (false timeouts).
  $m = [regex]::Match($url, '^(?<scheme>https?)://(?<host>[^/:]+)(?::(?<port>\d+))?')
  if (-not $m.Success) { return @() }

  $scheme = $m.Groups['scheme'].Value
  $urlHost = $m.Groups['host'].Value
  $portText = $m.Groups['port'].Value

  try { $scheme = $scheme.Trim().ToLowerInvariant() } catch {}
  try { $urlHost = $urlHost.Trim() } catch {}
  if (-not $urlHost) { return @() }

  $port = 0
  if ($portText) {
    try { $port = [int]$portText } catch { $port = 0 }
  }
  if (-not $port -or $port -le 0) {
    if ($scheme -eq 'https') { $port = 443 } elseif ($scheme -eq 'http') { $port = 80 } else { return @() }
  }

  # curl --resolve supports IPv6 literals, but they can be ambiguous due to ':' separators.
  # Wrap IPv6 in brackets to be safe.
  $ipLiteral = $ip
  if ($ipLiteral -match ':') { $ipLiteral = "[$ipLiteral]" }

  return @('--resolve', ("{0}:{1}:{2}" -f $urlHost, $port, $ipLiteral))
}

function Invoke-CurlSafe([string[]]$curlArgs) {
  $oldEap = $ErrorActionPreference
  try {
    $ErrorActionPreference = 'Continue'
    $raw = & curl.exe @curlArgs 2>&1
    return $raw
  } catch {
    return @([string]$_.Exception.Message)
  } finally {
    try { $global:LASTEXITCODE = 0 } catch {}
    $ErrorActionPreference = $oldEap
  }
}

function Curl-Head([string]$url) {
  $args = @('-4', '-sS', '-k', '-I', '--max-time', $TimeoutSec)
  $args += (Get-CurlResolveArgs $url)
  $args += @($url)
  $raw = Invoke-CurlSafe $args
  if ($Verbose) { $raw | Write-Host }
  $text = ($raw | Out-String)
  return $text -split "`r?`n"
}

function Curl-HeadAuth([string]$url, [string]$user, [string]$pass) {
  $args = @('-4', '-sS', '-k', '-I', '--max-time', $TimeoutSec, '-u', ("{0}:{1}" -f $user, $pass))
  $args += (Get-CurlResolveArgs $url)
  $args += @($url)
  $raw = Invoke-CurlSafe $args
  if ($Verbose) { $raw | Write-Host }
  $text = ($raw | Out-String)
  return $text -split "`r?`n"
}

# Simple GET utility to capture body and status
function Curl-Get([string]$url) {
  $tmp = [System.IO.Path]::GetTempFileName()
  $args = @('-4', '-sS', '-k', '--max-time', $TimeoutSec)
  $args += (Get-CurlResolveArgs $url)
  $args += @('-o', $tmp, '-w', '%{http_code}', $url)
  $statusText = ((Invoke-CurlSafe $args) | Out-String).Trim()
  $status = 0
  if ($statusText -match '(\d{3})\s*$') { $status = [int]$Matches[1] }
  $body = @()
  try { $body = Get-Content -Path $tmp -TotalCount 80 } catch {}
  Remove-Item -Force -ErrorAction SilentlyContinue $tmp
  return [pscustomobject]@{ status = $status; body = $body }
}

function Curl-GetStatusOnly([string]$url) {
  $args = @('-4', '-sS', '-k', '--max-time', $TimeoutSec, '-o', 'NUL', '-D', '-')
  $args += (Get-CurlResolveArgs $url)
  $args += @($url)
  $raw = Invoke-CurlSafe $args
  if ($Verbose) { $raw | Write-Host }
  $text = ($raw | Out-String)
  $lines = $text -split "`r?`n"
  return Get-StatusCodeFromHeaders $lines
}

# Simple POST utility to capture body and status
function Curl-PostJson([string]$url, [string]$jsonBody = '{}') {
  $tmp = [System.IO.Path]::GetTempFileName()
  $args = @('-4', '-sS', '-k', '--max-time', $TimeoutSec, '-X', 'POST', '-H', 'Content-Type: application/json', '-d', $jsonBody)
  $args += (Get-CurlResolveArgs $url)
  $args += @('-o', $tmp, '-w', '%{http_code}', $url)
  $statusText = ((Invoke-CurlSafe $args) | Out-String).Trim()
  $status = 0
  if ($statusText -match '(\d{3})\s*$') { $status = [int]$Matches[1] }
  $body = @()
  try { $body = Get-Content -Path $tmp -TotalCount 80 } catch {}
  Remove-Item -Force -ErrorAction SilentlyContinue $tmp
  return [pscustomobject]@{ status = $status; body = $body }
}

# Compute percentile (e.g., 0.95 => p95) from an array of millisecond durations
function Get-Percentile([double[]]$values, [double]$p) {
  if (-not $values -or $values.Count -eq 0) { return $null }
  $sorted = @($values | Sort-Object)
  $n = $sorted.Count
  if ($n -eq 1) { return [double]$sorted[0] }
  if ($p -lt 0) { $p = 0 }
  if ($p -gt 1) { $p = 1 }
  $rank = [Math]::Ceiling($p * $n) - 1
  if ($rank -lt 0) { $rank = 0 }
  if ($rank -ge $n) { $rank = $n - 1 }
  return [double]$sorted[$rank]
}

# Measure latency for an endpoint using HEAD-based status to minimize payload
function Measure-EndpointLatency([string]$url, [int]$samples = 20, [int]$sleepMs = 100) {
  $durations = New-Object System.Collections.Generic.List[double]
  $codes = New-Object System.Collections.Generic.List[int]
  for ($i = 0; $i -lt $samples; $i++) {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $code = 0
    try { $code = [int](Curl-GetStatusOnly $url) } catch { $code = 0 }
    $sw.Stop()
    $codes.Add($code) | Out-Null
    $durations.Add([double]$sw.Elapsed.TotalMilliseconds) | Out-Null
    if ($sleepMs -gt 0 -and $i -lt ($samples - 1)) { Start-Sleep -Milliseconds $sleepMs }
  }
  $okDurations = @()
  for ($j=0; $j -lt $durations.Count; $j++) { if ($codes[$j] -eq 200) { $okDurations += $durations[$j] } }
  $p50 = Get-Percentile $okDurations 0.5
  $p95 = Get-Percentile $okDurations 0.95
  return [ordered]@{
    url = $url
    samplesRequested = $samples
    samplesTaken = $durations.Count
    successCount = $okDurations.Count
    durationsMs = @($durations)
    statusCodes = @($codes)
    p50Ms = $p50
    p95Ms = $p95
  }
}

function Try-RateLimit([string]$domain, [int]$burst) {
  $codes = @()
  for ($i = 0; $i -lt $burst; $i++) {
    $u = "https://$domain/api/health"
    $c = [int](Curl-GetStatusOnly $u)
    if ($c -eq 0) {
      Start-Sleep -Milliseconds 200
      $c = [int](Curl-GetStatusOnly $u)
    }
    $codes += $c
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

# Prefer explicit per-run artifact directory if provided by deploy.ps1.
try {
  if ($env:BASE2_ARTIFACT_DIR) {
    $cand = [string]$env:BASE2_ARTIFACT_DIR
    if ($cand -and (Test-Path $cand)) { $artifactDir = $cand }
  }
} catch {}

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

# If invoked as a suite, expand to all checks.
if ($All) {
  $CheckDjangoAdmin = $true
  $CheckCelery = $true
  $CheckDns = $true
  $CheckPgAdmin = $true
  $CheckTraefikDashboard = $true
  $CheckRateLimit = $true
  $CheckTls = $true
  $CheckOpenApi = $true
}

$failures = @()

$doDnsFails = @()
$clientDnsFails = @()

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
  'celery-ping.json',
  'celery-result.json',
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
$failures += Verify-ComposePsHealth (Resolve-ArtifactPath -artifactDir $artifactDir -fileName 'compose-ps.txt')

# Schema compatibility check (post-migration)
$schemaStatusPath = Resolve-ArtifactPath -artifactDir $artifactDir -fileName 'schema-compat-check.status'
if ($schemaStatusPath -and (Test-Path $schemaStatusPath)) {
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

# When API health is reachable, validate response shape and measure latency
try {
  $healthJsonPath = Resolve-ArtifactPath -artifactDir $artifactDir -fileName 'api-health.json'
  if ($healthJsonPath -and (Test-Path $healthJsonPath)) {
    $healthRaw = Get-Content -Path $healthJsonPath -Raw
    $healthObj = $null
    try { $healthObj = ($healthRaw | ConvertFrom-Json) } catch {}
    $shapeOk = $false
    $missing = @()
    $types = [ordered]@{ okType = ''; serviceType = ''; db_okType = '' }
    if ($healthObj) {
      try { $types.okType = (if ($healthObj.ok -is [bool]) { 'boolean' } elseif ($null -eq $healthObj.ok) { 'null' } else { $healthObj.ok.GetType().Name }) } catch {}
      try { $types.serviceType = (if ($healthObj.service -is [string]) { 'string' } elseif ($null -eq $healthObj.service) { 'null' } else { $healthObj.service.GetType().Name }) } catch {}
      try { $types.db_okType = (if ($healthObj.db_ok -is [bool]) { 'boolean' } elseif ($null -eq $healthObj.db_ok) { 'null' } else { $healthObj.db_ok.GetType().Name }) } catch {}
      if (-not $healthObj.PSObject.Properties.Name.Contains('ok')) { $missing += 'ok' }
      if (-not $healthObj.PSObject.Properties.Name.Contains('service')) { $missing += 'service' }
      if (-not $healthObj.PSObject.Properties.Name.Contains('db_ok')) { $missing += 'db_ok' }
      # Consider shape OK if required keys exist; types are recorded but not enforced to avoid false negatives.
      $shapeOk = ($missing.Count -eq 0)
    }
    $shapePayload = [ordered]@{ ok = [bool]$shapeOk; missing = @($missing); observedTypes = $types }
    Write-ServiceArtifact -artifactDir $artifactDir -serviceName 'api' -fileName 'api-health-shape.json' -content $shapePayload
    if (-not $shapeOk) { $failures += 'API health response shape mismatch (expect keys: ok, service, db_ok)' }
  }
} catch {}

try {
  # Only measure latency if at least one health GET returned 200
  if (($apiGetStatus -eq 200) -or ($apiGetStatusSlash -eq 200)) {
    $healthUrl = "https://$Domain/api/health"
    $metrics = Measure-EndpointLatency -url $healthUrl -samples 20 -sleepMs 100
    Write-ServiceArtifact -artifactDir $artifactDir -serviceName 'api' -fileName 'api-health-latency.json' -content $metrics
    if ($metrics.p95Ms -and ([double]$metrics.p95Ms) -gt 5000) {
      $failures += "API health p95 latency too high: $([int]$metrics.p95Ms)ms (> 5000ms)"
    }
  }
} catch {}

# Local smoke tests
Write-Section "Local Smoke Tests"
try {
  $smokeArgs = @{ EnvPath = $EnvPath; Domain = $Domain; TimeoutSec = 5 }
  $smokeResolve = $ResolveIp
  if (-not $smokeResolve) { $smokeResolve = $ExpectedIpv4 }
  if ($smokeResolve) { $smokeArgs.ResolveIp = $smokeResolve }
  & .\digital_ocean\scripts\powershell\smoke-tests.ps1 @smokeArgs | Out-Null
} catch {
  $failures += "Local smoke tests failed: $($_.Exception.Message)"
}

# Optional: DNS checks against DO authoritative zone
if ($CheckDns) {
  # Derive expected IPs when not explicitly provided.
  if (-not $ExpectedIpv4) { $ExpectedIpv4 = $ResolveIp }
  if (-not $ExpectedIpv4) {
    try {
      $udPath = Resolve-ArtifactPath -artifactDir $artifactDir -fileName 'DO_userdata.json'
      if ($udPath) {
        $ud = Get-Content -Path $udPath -Raw | ConvertFrom-Json
        if ($ud.ip_address) { $ExpectedIpv4 = [string]$ud.ip_address }
      }
    } catch {}
  }

  # If expected IPv6 isn't provided, pull it from DO DNS @ AAAA (best effort).
  if (-not $ExpectedIpv6) {
    try {
      $aaaaAt = Invoke-ValidateDnsJson -domain $Domain -recordType 'AAAA' -name '@'
      $vals = @($aaaaAt.records | ForEach-Object { $_.data } | Where-Object { $_ })
      if ($vals.Count -gt 0) { $ExpectedIpv6 = [string]$vals[0] }
    } catch {}
  }

  $doDnsFails = @(Check-DoDns -artifactDir $artifactDir -domain $Domain -expectedIpv4 $ExpectedIpv4 -expectedIpv6 $ExpectedIpv6)
  $clientDnsFails = @(Check-ClientDns -artifactDir $artifactDir -domain $Domain -expectedIpv4 $ExpectedIpv4)
  $failures += $doDnsFails
}

# Final result
$result = [ordered]@{
  domain = $Domain
  logsDir = $LogsDir
  artifactDir = $artifactDir
  timestamp = ''
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
  tlsCheck = [ordered]@{ enabled = $false; ok = $false; notAfter = ''; daysRemaining = $null; dnsNames = @() }
  openApiCheck = [ordered]@{ enabled = $false; ok = $false; status = 0; openapi = ''; title = ''; pathsCount = 0 }
  openApiContractCheck = [ordered]@{ enabled = $false; ok = $false; contractPath = ''; contractPathsCount = 0; runtimePathsCount = 0; missingPaths = @(); error = '' }
  guardedEndpointsCheck = [ordered]@{ enabled = $false; ok = $false; endpoints = @() }
  artifactCompletenessCheck = [ordered]@{ enabled = $false; ok = $false; expected = @(); found = @{}; missing = @() }
  rateLimitCheck = [ordered]@{ enabled = $false; burst = 0; saw429 = $false }
  djangoProxy = [ordered]@{ enabled = $false; status = 0; bodySnippet = @() }
  adminCheck = [ordered]@{ enabled = $false; host = ''; statusNoAuth = 0; statusWithAuth = 0 }
  celeryCheck = [ordered]@{ enabled = $false; host = ''; statusNoAuth = 0; statusWithAuth = 0 }
  doDnsCheck = [ordered]@{ enabled = $false; ok = $false; expectedIpv4 = ''; expectedIpv6 = '' }
  clientDnsCheck = [ordered]@{ enabled = $false; ok = $false; expectedIpv4 = ''; failures = @() }
  failures = @()
}

# Emit explicit artifact for staging-only TLS resolver verification
try {
  Write-ServiceArtifact -artifactDir $artifactDir -serviceName 'traefik' -fileName 'tls-staging.json' -content ([ordered]@{ ok = [bool]$result.stagingResolverOK })
} catch {}

if ($CheckDns) {
  $result.doDnsCheck = [ordered]@{ enabled = $true; ok = ($doDnsFails.Count -eq 0); expectedIpv4 = $ExpectedIpv4; expectedIpv6 = $ExpectedIpv6 }
  $result.clientDnsCheck = [ordered]@{ enabled = $true; ok = ($clientDnsFails.Count -eq 0); expectedIpv4 = $ExpectedIpv4; failures = @($clientDnsFails) }
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

# Optional: TLS certificate validity (expiry + SAN)
if ($CheckTls) {
  $tlsFails = Check-TlsCert -artifactDir $artifactDir -domain $Domain
  $result.tlsCheck.enabled = $true
  try {
    $tlsArtifactPath = Join-Path (Get-ServiceOutDir -artifactDir $artifactDir -serviceName 'traefik') 'tls-cert.json'
    if (Test-Path $tlsArtifactPath) {
      $tlsObj = Get-Content -Path $tlsArtifactPath -Raw | ConvertFrom-Json
      $result.tlsCheck.ok = [bool]$tlsObj.ok
      $result.tlsCheck.notAfter = [string]$tlsObj.notAfter
      $result.tlsCheck.daysRemaining = $tlsObj.daysRemaining
      $result.tlsCheck.dnsNames = @($tlsObj.dnsNames)
    }
  } catch {}
  $failures += $tlsFails
}

# Optional: OpenAPI document availability and basic validity
if ($CheckOpenApi) {
  $openApiFails = Check-OpenApi -artifactDir $artifactDir -domain $Domain
  $result.openApiCheck.enabled = $true
  try {
    $openApiArtifactPath = Join-Path (Get-ServiceOutDir -artifactDir $artifactDir -serviceName 'api') 'openapi-validation.json'
    if (Test-Path $openApiArtifactPath) {
      $oa = Get-Content -Path $openApiArtifactPath -Raw | ConvertFrom-Json
      $result.openApiCheck.ok = [bool]$oa.ok
      $result.openApiCheck.status = [int]$oa.status
      $result.openApiCheck.openapi = [string]$oa.openapi
      $result.openApiCheck.title = [string]$oa.title
      $result.openApiCheck.pathsCount = [int]$oa.pathsCount
    }
  } catch {}
  $failures += $openApiFails

  # Contract-vs-runtime OpenAPI path check (contract is YAML under specs/)
  try {
    $contractPath = Join-Path $script:RepoRoot 'specs\001-django-fastapi-react\contracts\openapi.yaml'
    $c = Check-OpenApiContract -artifactDir $artifactDir -contractPath $contractPath
    $result.openApiContractCheck.enabled = $true
    $result.openApiContractCheck.ok = [bool]$c.payload.ok
    $result.openApiContractCheck.contractPath = [string]$c.payload.contractPath
    $result.openApiContractCheck.contractPathsCount = [int]$c.payload.contractPathsCount
    $result.openApiContractCheck.runtimePathsCount = [int]$c.payload.runtimePathsCount
    $result.openApiContractCheck.missingPaths = @($c.payload.missingPaths)
    $result.openApiContractCheck.error = [string]$c.payload.error
    $failures += @($c.failures)
  } catch {
    $result.openApiContractCheck.enabled = $true
    $result.openApiContractCheck.ok = $false
    $result.openApiContractCheck.error = [string]$_.Exception.Message
    $failures += "OpenAPI contract check failed: $($_.Exception.Message)"
  }

  # Guarded endpoint probes (unauthenticated should be 401/403)
  try {
    $g = Check-GuardedEndpoints -artifactDir $artifactDir -domain $Domain
    $result.guardedEndpointsCheck.enabled = $true
    $result.guardedEndpointsCheck.ok = [bool]$g.payload.ok
    $result.guardedEndpointsCheck.endpoints = @($g.payload.endpoints)
    $failures += @($g.failures)
  } catch {
    $result.guardedEndpointsCheck.enabled = $true
    $result.guardedEndpointsCheck.ok = $false
    $failures += "Guarded endpoints check failed: $($_.Exception.Message)"
  }
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
  if (-not (Get-ExpectedGuardedNoAuthOk $noAuthStatus)) { $failures += "Django admin expected 401/403 without auth, got $noAuthStatus ($AdminHost)" }
  if ($AdminUser -and $AdminPass) {
    if (@(200,302) -notcontains $withAuthStatus) { $failures += "Django admin expected 200/302 with auth, got $withAuthStatus ($AdminHost)" }
  }

  # Admin host path guard: non-/admin paths should not be served
  try {
    $rootHdr = Curl-Head ("https://{0}/" -f $AdminHost)
    $rootStatus = Get-StatusCodeFromHeaders $rootHdr
    $fooHdr = Curl-Head ("https://{0}/foo" -f $AdminHost)
    $fooStatus = Get-StatusCodeFromHeaders $fooHdr
    $guardOk = (($rootStatus -ne 200) -and ($fooStatus -ne 200))
    # Prefer explicit allowed statuses
    $allowedNonAdmin = @(401,403,404)
    $guardOk = $guardOk -or (($allowedNonAdmin -contains $rootStatus) -and ($allowedNonAdmin -contains $fooStatus))
    $guardPayload = [ordered]@{ host = $AdminHost; rootStatus = $rootStatus; fooStatus = $fooStatus; ok = $guardOk }
    Write-ServiceArtifact -artifactDir $artifactDir -serviceName 'meta' -fileName 'admin-host-path-guard.json' -content $guardPayload
    if (-not $guardOk) { $failures += "Admin host path guard failed: statuses root=$rootStatus, foo=$fooStatus ($AdminHost)" }
  } catch {}
}

# Optional: Test pgAdmin dashboard via edge
if ($CheckPgAdmin) {
  $sub = $env:PGADMIN_DNS_LABEL
  if (-not $sub) { $sub = 'pgadmin' }
  $PgHost = "$sub.$Domain"
  $noAuthHdr = Curl-Head "https://$PgHost/"
  $noAuthStatus = Get-StatusCodeFromHeaders $noAuthHdr
  $result.pgadminCheck = [ordered]@{ enabled = $true; host = $PgHost; statusNoAuth = $noAuthStatus }
  if (-not (Get-ExpectedGuardedNoAuthOk $noAuthStatus)) { $failures += "pgAdmin expected 401/403 without auth, got $noAuthStatus ($PgHost)" }
  Write-ServiceArtifact -artifactDir $artifactDir -serviceName 'database' -fileName 'pgadmin-head-noauth.txt' -content ($noAuthHdr -join "`n")
}

# Optional: Test Traefik dashboard via edge
if ($CheckTraefikDashboard) {
  $sub = $env:TRAEFIK_DNS_LABEL
  if (-not $sub) { $sub = 'traefik' }
  $TraefikHost = "$sub.$Domain"
  $traefikUrl = "https://$TraefikHost/"
  $noAuthHdr = Curl-Head $traefikUrl
  $noAuthStatus = Get-StatusCodeFromHeaders $noAuthHdr
  $result.traefikDashboardCheck = [ordered]@{ enabled = $true; host = $TraefikHost; statusNoAuth = $noAuthStatus }
  if (-not (Get-ExpectedGuardedNoAuthOk $noAuthStatus)) { $failures += "Traefik dashboard expected 401/403 without auth, got $noAuthStatus ($TraefikHost)" }
  Write-ServiceArtifact -artifactDir $artifactDir -serviceName 'traefik' -fileName 'traefik-dashboard-head-noauth.txt' -content ($noAuthHdr -join "`n")
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
  # Prefer remote verification artifacts (deterministic) if present.
  $taskId = ''
  $taskState = ''
  $taskResult = $null
  $artifactResultPath = Resolve-ArtifactPath -artifactDir $artifactDir -fileName 'celery-result.json'
  $artifactPingPath = Resolve-ArtifactPath -artifactDir $artifactDir -fileName 'celery-ping.json'
  $usedRemoteArtifacts = $false
  try {
    if ($artifactResultPath -and (Test-Path $artifactResultPath)) {
      $jr = Get-Content -Path $artifactResultPath -Raw | ConvertFrom-Json
      $taskId = [string]$jr.task_id
      $taskState = [string]$jr.state
      if ($jr.ready -and $jr.successful -and $jr.result -eq 'pong') { $taskResult = 'pong' }
      $usedRemoteArtifacts = $true
    } elseif ($artifactPingPath -and (Test-Path $artifactPingPath)) {
      $jp = Get-Content -Path $artifactPingPath -Raw | ConvertFrom-Json
      $taskId = [string]$jp.task_id
      $usedRemoteArtifacts = $true
    }
  } catch {}

  # If remote artifacts aren't available, try a live roundtrip task via the edge API.
  if (-not $usedRemoteArtifacts) {
    try {
      $ping = Curl-PostJson "https://$Domain/api/celery/ping" '{}'
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
  }

  $result.celeryCheck = [ordered]@{
    enabled = $true
    host = $FlowerHost
    statusNoAuth = $noAuthStatus
    statusWithAuth = $withAuthStatus
    task = [ordered]@{ id = $taskId; state = $taskState; result = $taskResult }
  }
  if (-not (Get-ExpectedGuardedNoAuthOk $noAuthStatus)) { $failures += "Flower expected 401/403 without auth, got $noAuthStatus ($FlowerHost)" }
  if ($AdminUser -and $AdminPass) {
    if (@(200,302) -notcontains $withAuthStatus) { $failures += "Flower expected 200/302 with auth, got $withAuthStatus ($FlowerHost)" }
  }
  if (-not $taskResult) { $failures += "Celery ping task did not complete successfully" }
}

# Artifact completeness check (key deploy artifacts must exist)
if ($CheckOpenApi) {
  try {
    $acExpected = @('openapi.json','openapi-validation.json','schema-compat-check.json')
    $ac = Check-ArtifactCompleteness -artifactDir $artifactDir -expectedFiles $acExpected
    $result.artifactCompletenessCheck.enabled = $true
    $result.artifactCompletenessCheck.ok = [bool]$ac.payload.ok
    $result.artifactCompletenessCheck.expected = @($ac.payload.expected)
    $result.artifactCompletenessCheck.found = $ac.payload.found
    $result.artifactCompletenessCheck.missing = @($ac.payload.missing)
    $failures += @($ac.failures)
  } catch {
    $result.artifactCompletenessCheck.enabled = $true
    $result.artifactCompletenessCheck.ok = $false
    $failures += "Artifact completeness check failed: $($_.Exception.Message)"
  }
}

if ($Json) {
  $result.timestamp = (Get-Date).ToString('s')

  # Write report early so artifact completeness can assert it exists.
  $result.failures = @($failures)
  $result.success = $false
  try { Write-ServiceArtifact -artifactDir $artifactDir -serviceName 'meta' -fileName 'post-deploy-report.json' -content $result } catch {}

  if ($CheckOpenApi) {
    try {
      $acExpectedFinal = @('openapi.json','openapi-validation.json','schema-compat-check.json','post-deploy-report.json')
      $ac2 = Check-ArtifactCompleteness -artifactDir $artifactDir -expectedFiles $acExpectedFinal
      $result.artifactCompletenessCheck.enabled = $true
      $result.artifactCompletenessCheck.ok = [bool]$ac2.payload.ok
      $result.artifactCompletenessCheck.expected = @($ac2.payload.expected)
      $result.artifactCompletenessCheck.found = $ac2.payload.found
      $result.artifactCompletenessCheck.missing = @($ac2.payload.missing)
      $failures += @($ac2.failures)
    } catch {
      $failures += "Artifact completeness finalization failed: $($_.Exception.Message)"
    }
  }

  $result.failures = @($failures)
  $ok = ($failures.Count -eq 0 -and $result.missingFiles.Count -eq 0 -and $result.stagingResolverOK)
  $result.success = $ok

  # Persist final form.
  try { Write-ServiceArtifact -artifactDir $artifactDir -serviceName 'meta' -fileName 'post-deploy-report.json' -content $result } catch {}

  $jsonStr = $result | ConvertTo-Json -Depth 6
  Write-Output $jsonStr
  try { Pop-Location } catch {}
  if ($ok) { exit 0 } else { exit 1 }
} else {
  if ($failures.Count -gt 0 -or $result.missingFiles.Count -gt 0 -or -not $result.stagingResolverOK) {
    Write-Host "Failures:" -ForegroundColor Red
    $result.missingFiles | ForEach-Object { Write-Host " - Missing artifact: $_" -ForegroundColor Red }
    $failures | ForEach-Object { Write-Host " - $_" -ForegroundColor Red }
    if (-not $result.stagingResolverOK) { Write-Host " - Traefik not using staging resolver (le-staging)" -ForegroundColor Red }
    try { Pop-Location } catch {}
    exit 1
  }
  Write-Host "Post-deploy verification passed." -ForegroundColor Green
  try { Pop-Location } catch {}
  exit 0
}
