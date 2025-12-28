param(
    [switch]$Build
)

$ErrorActionPreference = 'Stop'

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$composeFile = Join-Path $projectRoot 'local.docker.yml'
$envFile = Join-Path $projectRoot '.env'
$envExample = Join-Path $projectRoot '.env.example'

if (-not (Test-Path $envFile)) {
    if (Test-Path $envExample) {
        Copy-Item $envExample $envFile
        Write-Host 'Created .env from .env.example (review values before deploying).'
    } else {
        throw 'Missing .env and .env.example'
    }
}

Push-Location $projectRoot
try {
    if ($Build) {
        docker compose -f $composeFile up -d --build
    } else {
        docker compose -f $composeFile up -d
    }
} finally {
    Pop-Location
}
