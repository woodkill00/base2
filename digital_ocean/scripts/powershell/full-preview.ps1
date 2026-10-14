$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
Set-Location $repo
& python3 -m digital_ocean.scripts.python.full_preview_cli @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
