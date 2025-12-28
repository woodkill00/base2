param(
  [string]$EnvPath = ".\.env",
  [string]$Domain = "localhost",
  [string]$ResolveIp = "",
  [int]$TimeoutSec = 5,
  [switch]$Verbose
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Ensure relative paths work regardless of where the script is invoked from.
$script:RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
Push-Location $script:RepoRoot

function Write-Section($msg) {
  Write-Host "`n=== $msg ===" -ForegroundColor Cyan
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

function Get-RemoteTlsCertificate([string]$domain) {
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
    return New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($remoteCert)
  } finally {
    try { if ($ssl) { $ssl.Dispose() } } catch {}
    try { if ($stream) { $stream.Dispose() } } catch {}
    try { if ($client) { $client.Close() } } catch {}
  }
}

function Curl-Head([string]$url, [string[]]$extraArgs = @()) {
  $args = @('-skI', '--max-time', $TimeoutSec) + $extraArgs + @($url)
  $raw = & curl.exe @args 2>&1
  if ($Verbose) { $raw | Write-Host }
  $text = ($raw | Out-String)
  return $text -split "`r?`n"
}

function Curl-Get([string]$url, [string[]]$extraArgs = @()) {
  $args = @('-sk', '--max-time', $TimeoutSec) + $extraArgs + @($url)
  $out = & curl.exe @args 2>&1
  if ($Verbose) { $out | Write-Host }
  return $out
}

function Curl-GetStatus([string]$url, [string[]]$extraArgs = @()) {
  $tmp = [System.IO.Path]::GetTempFileName()
  $args = @('-sk', '--max-time', $TimeoutSec) + $extraArgs + @('-o', $tmp, '-w', '%{http_code}', $url)
  $statusRaw = (& curl.exe @args 2>&1 | Out-String).Trim()
  if ($Verbose) { $statusRaw | Write-Host }
  Remove-Item -Force -ErrorAction SilentlyContinue $tmp
  if ($statusRaw -match '(\d{3})\s*$') { return [int]$Matches[1] }
  return 0
}

# Init
Write-Section "Smoke Tests"
Load-DotEnv -path $EnvPath
if ($env:WEBSITE_DOMAIN) { $Domain = $env:WEBSITE_DOMAIN }

$failures = @()

# 1) HTTP root should redirect to HTTPS
Write-Section "HTTP -> HTTPS redirect"
$resolveHttp = @()
if ($ResolveIp) { $resolveHttp = @('--resolve', ("{0}:80:{1}" -f $Domain, $ResolveIp)) }
$hdr = Curl-Head "http://$Domain/" $resolveHttp
$code = Get-StatusCodeFromHeaders $hdr
if ($code -lt 300 -or $code -ge 400) { $failures += "Root HTTP expected 3xx, got $code" }
if (-not ($hdr | Where-Object { $_ -match '^Location:\s*https://'})) { $failures += "Missing Location:https:// header on HTTP root" }

# 2) HTTPS root should return 200 and security headers
Write-Section "HTTPS root and security headers"
$resolveHttps = @()
if ($ResolveIp) { $resolveHttps = @('--resolve', ("{0}:443:{1}" -f $Domain, $ResolveIp)) }
$hdr2 = Curl-Head "https://$Domain/" $resolveHttps
$code2 = Get-StatusCodeFromHeaders $hdr2
if ($code2 -ne 200) { $failures += "HTTPS root expected 200, got $code2" }
$expectedHeaders = @(
  '^strict-transport-security:',
  '^x-content-type-options:',
  '^x-frame-options:',
  '^referrer-policy:'
)
foreach ($h in $expectedHeaders) {
  if (-not ($hdr2 | Where-Object { $_ -imatch $h })) { $failures += "Missing security header: $h" }
}

# 3) API health should be OK
Write-Section "API health"
$code3 = Curl-GetStatus "https://$Domain/api/health" $resolveHttps
if ($code3 -ne 200) { $failures += "API health expected 200, got $code3" }

# 4) Unauthenticated /api/auth/me should return 401
Write-Section "API auth/me unauth"
$code4 = Curl-GetStatus "https://$Domain/api/auth/me" $resolveHttps
if ($code4 -ne 401) { $failures += "API auth/me expected 401 (unauth), got $code4" }

# 5) TLS certificate should be valid and cover the domain
Write-Section "TLS certificate validity"
try {
  $cert = Get-RemoteTlsCertificate -domain $Domain
  $dnsNames = @(Get-CertDnsNames -cert $cert)
  if ($cert.NotAfter.ToUniversalTime() -le (Get-Date).ToUniversalTime()) {
    $failures += "TLS cert expired (notAfter=$($cert.NotAfter.ToString('o')))"
  }
  if ($cert.NotBefore.ToUniversalTime() -gt (Get-Date).ToUniversalTime().AddMinutes(5)) {
    $failures += "TLS cert not yet valid (notBefore=$($cert.NotBefore.ToString('o')))"
  }
  if (-not ($dnsNames -contains $Domain)) {
    $failures += "TLS cert SAN does not include ${Domain} (dnsNames=$($dnsNames -join ','))"
  }

  $deployEnv = ((($env:ENV) + '')).Trim().ToLower()
  $isProd = ($deployEnv -eq 'production' -or $deployEnv -eq 'prod')
  if ($isProd) {
    $issuer = (($cert.Issuer) + '')
    if ($issuer -match '(?i)fake\s+le|staging') {
      $failures += "TLS issuer looks like staging in production (issuer=$issuer)"
    }
  }
} catch {
  $failures += "TLS check failed: $($_.Exception.Message)"
}

# Summary
if ($failures.Count -gt 0) {
  Write-Host "Failures:" -ForegroundColor Red
  $failures | ForEach-Object { Write-Host " - $_" -ForegroundColor Red }
  try { Pop-Location } catch {}
  exit 1
}

Write-Host "All smoke tests passed." -ForegroundColor Green
try { Pop-Location } catch {}
exit 0
