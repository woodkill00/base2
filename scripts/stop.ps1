$ErrorActionPreference = 'Stop'

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$composeFile = Join-Path $projectRoot 'local.docker.yml'

Push-Location $projectRoot
try {
    docker compose -f $composeFile down
} finally {
    Pop-Location
}
