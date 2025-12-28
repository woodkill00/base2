param(
    [int]$Confirm = 0
)

$ErrorActionPreference = 'Stop'

if ($Confirm -ne 1) {
    throw 'Refusing to reset without -Confirm 1'
}

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$composeFile = Join-Path $projectRoot 'local.docker.yml'

Push-Location $projectRoot
try {
    docker compose -f $composeFile down -v
} finally {
    Pop-Location
}
