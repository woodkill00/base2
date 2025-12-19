param(
  [string]$EnvPath = ".\.env",
  [string]$Domain = "localhost",
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

function Curl-Head([string]$url) {
  $args = @('-skI', '--max-time', $TimeoutSec, $url)
  $out = & curl.exe @args 2>&1
  if ($Verbose) { $out | Write-Host }
  return $out -split "`r?`n"
}

function Curl-Get([string]$url) {
  $args = @('-sk', '--max-time', $TimeoutSec, $url)
  $out = & curl.exe @args 2>&1
  if ($Verbose) { $out | Write-Host }
  return $out
}

# Init
Write-Section "Smoke Tests"
Load-DotEnv -path $EnvPath
if ($env:WEBSITE_DOMAIN) { $Domain = $env:WEBSITE_DOMAIN }

$failures = @()

# 1) HTTP root should redirect to HTTPS
Write-Section "HTTP → HTTPS redirect"
$hdr = Curl-Head "http://$Domain/"
$code = Get-StatusCodeFromHeaders $hdr
if ($code -lt 300 -or $code -ge 400) { $failures += "Root HTTP expected 3xx, got $code" }
if (-not ($hdr | Where-Object { $_ -match '^Location:\s*https://'})) { $failures += "Missing Location:https:// header on HTTP root" }

# 2) HTTPS root should return 200 and security headers
Write-Section "HTTPS root and security headers"
$hdr2 = Curl-Head "https://$Domain/"
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
$hdr3 = Curl-Head "https://$Domain/api/health"
$code3 = Get-StatusCodeFromHeaders $hdr3
if ($code3 -ne 200) { $failures += "API health expected 200, got $code3" }

# Summary
if ($failures.Count -gt 0) {
  Write-Host "Failures:" -ForegroundColor Red
  $failures | ForEach-Object { Write-Host " - $_" -ForegroundColor Red }
  exit 1
}

Write-Host "All smoke tests passed." -ForegroundColor Green
exit 0
