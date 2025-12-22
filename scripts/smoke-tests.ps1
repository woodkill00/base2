param(
  [string]$EnvPath = ".\.env",
  [string]$Domain = "localhost",
  [string]$ResolveIp = "",
  [int]$TimeoutSec = 5,
  [switch]$Verbose
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

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
    if ($line -match '^HTTP/[^ ]+\s+(\d{3})') { return [int]$Matches[1] }
  }
  return 0
}

function Curl-Head([string]$url, [string[]]$extraArgs = @()) {
  $args = @('-skI', '--max-time', $TimeoutSec) + $extraArgs + @($url)
  $out = & curl.exe @args 2>&1
  if ($Verbose) { $out | Write-Host }
  return $out -split "`r?`n"
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
  $statusRaw = & curl.exe @args 2>&1
  if ($Verbose) { $statusRaw | Write-Host }
  Remove-Item -Force -ErrorAction SilentlyContinue $tmp
  try { return [int]$statusRaw } catch { return 0 }
}

# Init
Write-Section "Smoke Tests"
Load-DotEnv -path $EnvPath
if ($env:WEBSITE_DOMAIN) { $Domain = $env:WEBSITE_DOMAIN }

$failures = @()

# 1) HTTP root should redirect to HTTPS
Write-Section "HTTP → HTTPS redirect"
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

# Summary
if ($failures.Count -gt 0) {
  Write-Host "Failures:" -ForegroundColor Red
  $failures | ForEach-Object { Write-Host " - $_" -ForegroundColor Red }
  exit 1
}

Write-Host "All smoke tests passed." -ForegroundColor Green
exit 0
