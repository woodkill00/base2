param([Parameter(ValueFromRemainingArguments = $true)][string[]]$RemainingArgs)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
python (Join-Path $root 'scripts/python/frontend_ci_scope.py') --root $root @RemainingArgs
exit $LASTEXITCODE
