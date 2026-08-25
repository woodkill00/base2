$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
& (Join-Path $root '.venv/Scripts/python.exe') (Join-Path $root 'scripts/python/create_base2_site.py') @args
exit $LASTEXITCODE
