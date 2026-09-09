param(
    [string]$ComposeFile = 'development.docker.yml',
    [string]$EnvFile = '.env'
)

$ErrorActionPreference = 'Stop'

$projectRoot = (Resolve-Path (Join-Path (Join-Path $PSScriptRoot '..') '..')).Path

function Resolve-ComposeFilePath {
    param(
        [string]$Path,
        [string]$Root
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return (Join-Path $Root 'development.docker.yml')
    }
    if ([System.IO.Path]::IsPathRooted($Path)) {
        return $Path
    }
    return (Join-Path $Root $Path)
}

function Resolve-EnvFilePath {
    param(
        [string]$Path,
        [string]$Root
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return (Join-Path $Root '.env')
    }
    if ([System.IO.Path]::IsPathRooted($Path)) {
        return $Path
    }
    return (Join-Path $Root $Path)
}

$composeFile = Resolve-ComposeFilePath -Path $ComposeFile -Root $projectRoot
$envFile = Resolve-EnvFilePath -Path $EnvFile -Root $projectRoot

Push-Location $projectRoot
try {
    docker compose --env-file $envFile -f $composeFile run --rm --no-deps api python -m api.scripts.migrate
    if ($LASTEXITCODE -ne 0) { throw "API migration failed with exit code $LASTEXITCODE" }
    docker compose --env-file $envFile -f $composeFile run --rm --no-deps django python manage.py migrate --noinput
    if ($LASTEXITCODE -ne 0) { throw "Django migration failed with exit code $LASTEXITCODE" }
} finally {
    Pop-Location
}
