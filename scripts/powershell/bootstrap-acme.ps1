param(
  [Parameter(Mandatory = $true)][string]$Directory,
  [int]$Uid = 1000,
  [int]$Gid = 1000,
  [string]$Output = ''
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Arguments = @(
  (Join-Path $RepoRoot 'digital_ocean\scripts\python\bootstrap_acme.py'),
  '--directory', $Directory,
  '--uid', [string]$Uid,
  '--gid', [string]$Gid
)
if (-not [string]::IsNullOrWhiteSpace($Output)) {
  $Arguments += @('--output', $Output)
}

& python @Arguments
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
