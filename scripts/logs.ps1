param(
    [string[]]$Services,
    [int]$Tail = 200
)

$ErrorActionPreference = 'Stop'

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$composeFile = Join-Path $projectRoot 'local.docker.yml'

Push-Location $projectRoot
try {
    if ($Services -and $Services.Count -gt 0) {
        docker compose -f $composeFile logs -f --tail=$Tail @Services
    } else {
        docker compose -f $composeFile logs -f --tail=$Tail
    }
} finally {
    Pop-Location
}
