$ErrorActionPreference = 'Stop'

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$composeFile = Join-Path $projectRoot 'local.docker.yml'

Push-Location $projectRoot
try {
    docker compose -f $composeFile exec -T api pytest
    docker compose -f $composeFile exec -T django pytest

    Push-Location (Join-Path $projectRoot 'react-app')
    try {
        npm run test:ci
    } finally {
        Pop-Location
    }
} finally {
    Pop-Location
}
