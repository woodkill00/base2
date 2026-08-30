[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path (Join-Path $PSScriptRoot '..') '..')).Path

if (-not $env:VIRTUAL_ENV) {
    throw 'Virtual environment not active. Run ./scripts/powershell/first-start.ps1 to activate `.venv` before installing Node dependencies.'
}

Write-Host '==> Node dependency installation starting' -ForegroundColor Cyan

$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeCmd) {
    throw 'node executable not found in PATH. Install Node.js 24.20.0+ and retry.'
}

$npmCmd = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npmCmd) {
    throw 'npm executable not found in PATH. Install npm 11.10.0+ and retry.'
}

function Get-NumericVersion([string]$version) {
    if (-not $version) { return @() }
    $trimmed = $version.TrimStart('v').Trim()
    if (-not $trimmed) { return @() }
    $numbers = @()
    foreach ($segment in ($trimmed -split '\.')) {
        if ($segment -match '^[0-9]+$') {
            $numbers += [int]$segment
        }
    }
    return $numbers
}

function Get-PaddedVersion([int[]]$parts, [int]$size) {
    $result = @()
    for ($i = 0; $i -lt $size; $i++) {
        if ($i -lt $parts.Count) {
            $result += $parts[$i]
        } else {
            $result += 0
        }
    }
    return $result
}

function Test-VersionAtLeast([int[]]$actual, [int[]]$required) {
    $actualParts = Get-PaddedVersion -parts $actual -size 3
    $requiredParts = Get-PaddedVersion -parts $required -size 3
    for ($i = 0; $i -lt 3; $i++) {
        if ($actualParts[$i] -gt $requiredParts[$i]) { return $true }
        if ($actualParts[$i] -lt $requiredParts[$i]) { return $false }
    }
    return $true
}

$nodeVersionParts = @(Get-NumericVersion (& $nodeCmd.Path --version))
if ($nodeVersionParts.Count -lt 1) {
    throw 'Unable to parse node --version output.'
}
$requiredNode = @(24, 13, 1)
if (-not (Test-VersionAtLeast -actual $nodeVersionParts -required $requiredNode)) {
    $nodeReported = (& $nodeCmd.Path --version).Trim()
    throw "Node.js version 24.20.0+ is required but found $nodeReported."
}

$npmVersionParts = @(Get-NumericVersion (& $npmCmd.Path --version))
if ($npmVersionParts.Count -lt 1) {
    throw 'Unable to parse npm --version output.'
}
$requiredNpm = @(11, 10, 0)
if (-not (Test-VersionAtLeast -actual $npmVersionParts -required $requiredNpm)) {
    $npmReported = (& $npmCmd.Path --version).Trim()
    throw "npm version 11.10.0+ required but found $npmReported."
}

Write-Host ("Node version: {0}; npm version: {1}" -f (& $nodeCmd.Path --version).Trim(), (& $npmCmd.Path --version).Trim()) -ForegroundColor DarkGray

function Invoke-NpmInstall([string]$workingDir, [string]$label, [switch]$AllowLegacyPeerDeps) {
    Push-Location $workingDir
    try {
        & $npmCmd.Path install --no-fund
        if ($LASTEXITCODE -ne 0) {
            if ($AllowLegacyPeerDeps) {
                Write-Warning "npm install ($label) failed; retrying with --legacy-peer-deps."
                & $npmCmd.Path install --no-fund --legacy-peer-deps
            }
            if ($LASTEXITCODE -ne 0) {
                throw "npm install ($label) failed with exit code $LASTEXITCODE"
            }
        }
    } finally {
        Pop-Location
    }
}

Write-Host "Installing npm dependencies in $repoRoot..." -ForegroundColor Cyan
Invoke-NpmInstall -workingDir $repoRoot -label 'repo root'

$subdirs = @('react-app','e2e')
foreach ($sub in $subdirs) {
    $pkgJson = Join-Path $repoRoot "$sub/package.json"
    if (Test-Path $pkgJson) {
        Write-Host "Installing npm dependencies in $sub..." -ForegroundColor Cyan
        $allowLegacy = $sub -eq 'react-app'
        Invoke-NpmInstall -workingDir (Join-Path $repoRoot $sub) -label $sub -AllowLegacyPeerDeps:$allowLegacy
    }
}

Write-Host 'Node dependencies installed successfully.' -ForegroundColor Green
