$ErrorActionPreference = 'Stop'

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$composeFile = Join-Path $projectRoot 'local.docker.yml'

Push-Location $projectRoot
try {
    docker compose -f $composeFile exec -T api python -m api.scripts.seed
} finally {
    Pop-Location
}
