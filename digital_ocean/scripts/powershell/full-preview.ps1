$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$wslRepo = (wsl wslpath -a $repo).Trim()
if (-not $wslRepo) { throw 'Unable to resolve Base2 repository in WSL.' }
$quoted = ($args | ForEach-Object { "'" + ($_ -replace "'", "'\\''") + "'" }) -join ' '
wsl bash -lc "cd '$wslRepo' && exec python3 -m digital_ocean.scripts.python.full_preview_cli $quoted"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
