$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location $repoRoot
python scripts/python/run_email_container_checks.py @args
exit $LASTEXITCODE
