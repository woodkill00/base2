[CmdletBinding()]
param(
    [switch]$SkipPipUpgrade,
    [switch]$Api,
    [switch]$Django,
    [switch]$DigitalOcean
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path (Join-Path $PSScriptRoot '..') '..')).Path
$hostPython = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $hostPython) { $hostPython = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $hostPython) { throw 'Python executable not found in PATH. Install Python 3.12+ and retry.' }

Write-Host '==> Python dependency installation starting' -ForegroundColor Cyan

$requiredVersion = '3.12'
$pythonVersionFile = Join-Path $repoRoot '.python-version'
if (Test-Path $pythonVersionFile) {
    $content = (Get-Content $pythonVersionFile -ErrorAction Stop | Select-Object -First 1).Trim()
    if ($content) { $requiredVersion = $content }
}

function Normalize-Version([string]$version) {
    if (-not $version) { return '' }
    $parts = $version.TrimStart('v').Trim() -split '\.'
    if ($parts.Count -ge 2) {
        return "$($parts[0]).$($parts[1])"
    }
    return $version.Trim()
}

$expectedVersion = Normalize-Version $requiredVersion
if (-not $expectedVersion) {
    throw 'Unable to determine required Python version.'
}

$targets = @()
if ($Api -or $Django -or $DigitalOcean) {
    if ($Api) { $targets += @{ Venv = '.venv-api'; Requirements = 'requirements-dev-api.txt' } }
    if ($Django) { $targets += @{ Venv = '.venv-django'; Requirements = 'requirements-dev-django.txt' } }
    if ($DigitalOcean) { $targets += @{ Venv = '.venv'; Requirements = 'digital_ocean/requirements.txt' } }
} else {
    $targets += @{ Venv = '.venv-api'; Requirements = 'requirements-dev-api.txt' }
    $targets += @{ Venv = '.venv-django'; Requirements = 'requirements-dev-django.txt' }
    $targets += @{ Venv = '.venv'; Requirements = 'digital_ocean/requirements.txt' }
}

foreach ($target in $targets) {
    $reqPath = Join-Path $repoRoot $target.Requirements
    $venvDir = Join-Path $repoRoot $target.Venv
    $venvPython = Join-Path $venvDir 'Scripts\python.exe'
    if (-not (Test-Path $reqPath)) { throw "Requirements file not found: $($target.Requirements)" }
    if (-not (Test-Path $venvPython)) {
        Write-Host "Creating isolated environment $($target.Venv)..." -ForegroundColor Cyan
        & $hostPython.Source -m venv --clear $venvDir
        if ($LASTEXITCODE -ne 0) { throw "Unable to create $($target.Venv)" }
    }
    & $venvPython -m pip --version | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "$($target.Venv) cannot run pip" }
    $actualVersion = (& $venvPython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')").Trim()
    if ($actualVersion -ne $expectedVersion) {
        throw "$($target.Venv) uses Python $actualVersion but $expectedVersion is required."
    }
    if (-not $SkipPipUpgrade) {
        & $venvPython -m pip install --upgrade pip
        if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed in $($target.Venv)" }
    }
    Write-Host "Installing $($target.Requirements) into $($target.Venv)..." -ForegroundColor Cyan
    & $venvPython -m pip install -r $reqPath
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Initial pip install failed for $($target.Venv); retrying once without cache."
        & $venvPython -m pip install --no-cache-dir -r $reqPath
        if ($LASTEXITCODE -ne 0) { throw "pip install failed twice for $($target.Requirements)" }
    }
    & $venvPython -m pip check
    if ($LASTEXITCODE -ne 0) { throw "Dependency validation failed for $($target.Venv)" }
}

Write-Host 'Python dependencies installed successfully.' -ForegroundColor Green
