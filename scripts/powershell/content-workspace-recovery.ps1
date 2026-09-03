param(
  [Parameter(Mandatory=$true)][ValidateSet('backup','restore')][string]$Mode,
  [Parameter(Mandatory=$true)][string]$Source,
  [Parameter(Mandatory=$true)][string]$Target
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
& (Join-Path $root '.venv-api/Scripts/python.exe') (Join-Path $root 'scripts/python/content_workspace_recovery.py') $Mode $Source $Target
exit $LASTEXITCODE
