$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
& python (Join-Path $repoRoot 'scripts\python\validate_feature_093.py') @args
exit $LASTEXITCODE
