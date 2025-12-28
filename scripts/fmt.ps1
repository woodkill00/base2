$ErrorActionPreference = 'Stop'

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

Push-Location $projectRoot
try {
    Push-Location (Join-Path $projectRoot 'react-app')
    try {
        npm run format
    } finally {
        Pop-Location
    }

    python -m ruff format .
} finally {
    Pop-Location
}
