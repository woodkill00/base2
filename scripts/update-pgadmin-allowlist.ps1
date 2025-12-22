param(
    [string] $EnvPath,
    [string] $Ip,
    [switch] $DryRun
)

# update-pgadmin-allowlist.ps1
# - Detects your public IPv4 (or uses -Ip) and updates PGADMIN_ALLOWLIST in .env to <ip>/32
# - Safe for PowerShell 5.1; preserves other .env content
#
# Usage examples:
#   ./scripts/update-pgadmin-allowlist.ps1
#   ./scripts/update-pgadmin-allowlist.ps1 -Ip 203.0.113.42
#   ./scripts/update-pgadmin-allowlist.ps1 -EnvPath ./.env -DryRun

$ErrorActionPreference = 'Stop'

function Write-Info($m) { Write-Host "[INFO] $m" -ForegroundColor Green }
function Write-Warn($m) { Write-Host "[WARN] $m" -ForegroundColor Yellow }
function Write-Err($m) { Write-Host "[ERROR] $m" -ForegroundColor Red }

# Resolve default .env path (repo root assumed as parent of scripts folder)
if (-not $EnvPath -or [string]::IsNullOrWhiteSpace($EnvPath)) {
    $repoRoot = Split-Path -Parent $PSScriptRoot
    $EnvPath = Join-Path $repoRoot '.env'
}

if (-not (Test-Path -LiteralPath $EnvPath)) {
    Write-Err "Could not find .env at: $EnvPath"
    exit 1
}

function Get-PublicIPv4 {
    try {
        $r = Invoke-RestMethod -Uri 'https://api.ipify.org?format=json' -TimeoutSec 5 -UseBasicParsing
        if ($r -and $r.ip) { return $r.ip }
    } catch { }
    try {
        $ip = Invoke-RestMethod -Uri 'https://ifconfig.me/ip' -TimeoutSec 5 -UseBasicParsing
        if ($ip) { return ($ip.Trim()) }
    } catch { }
    return $null
}

function Is-IPv4([string] $candidate) {
    try {
        $out = $null
        if ([System.Net.IPAddress]::TryParse($candidate, [ref]$out)) {
            return ($out.AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork)
        }
        return $false
    } catch { return $false }
}

# Determine IP
$useIp = $Ip
if (-not $useIp) {
    Write-Info "Detecting public IPv4..."
    $detected = Get-PublicIPv4
    if (-not $detected) {
        Write-Err "Failed to detect public IPv4. Provide -Ip <addr>."
        exit 1
    }
    $useIp = $detected
}

if (-not (Is-IPv4 $useIp)) {
    Write-Err "Provided IP is not a valid IPv4 address: $useIp"
    exit 1
}

$cidr = "$useIp/32"
Write-Info "Using allowlist CIDR: $cidr"

# Read .env as text to preserve formatting
$text = Get-Content -LiteralPath $EnvPath -Raw -Encoding UTF8
# Remove ALL existing PGADMIN_ALLOWLIST lines to avoid duplicates, then append a single line
$newText = [System.Text.RegularExpressions.Regex]::Replace($text, '(?m)^\s*PGADMIN_ALLOWLIST\s*=.*\r?\n?', '')
if ($newText.Length -gt 0 -and -not $newText.EndsWith("`r`n")) { $newText += "`r`n" }
$newText += "PGADMIN_ALLOWLIST=$cidr`r`n"

if ($DryRun) {
    Write-Warn "[DryRun] Would write updated .env with PGADMIN_ALLOWLIST=$cidr"
    $preview = $newText -split "`r`n" | Where-Object { $_ -match '^PGADMIN_ALLOWLIST=' }
    Write-Host ($preview -join "`n")
    exit 0
}

# Write back
$newText | Set-Content -LiteralPath $EnvPath -Encoding UTF8

# Confirm
$confirm = Select-String -Path $EnvPath -Pattern '^PGADMIN_ALLOWLIST=.*$' -Encoding UTF8
if ($confirm) {
    # Print a single confirmation line and the number of occurrences to ensure uniqueness
    $lines = @($confirm | ForEach-Object { $_.Line })
    Write-Info ("Updated: " + $lines[0])
    if ($lines.Count -gt 1) { Write-Warn ("Found ${lines.Count} PGADMIN_ALLOWLIST lines; expected 1. File was cleaned to ensure single entry.") }
    Write-Info "Done. Restart Traefik to apply: docker compose up -d --force-recreate traefik"
} else {
    Write-Err "Failed to confirm PGADMIN_ALLOWLIST write."
    exit 1
}
