$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$action = if ($args.Count -gt 0) { [string]$args[0] } else { '' }
$rest = if ($args.Count -gt 1) { $args[1..($args.Count - 1)] } else { @() }
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = 'python' }

switch ($action) {
  'setup' { & (Join-Path $PSScriptRoot 'setup.ps1') @rest; exit $LASTEXITCODE }
  'generate' { & (Join-Path $root 'scripts\create-base2-site.ps1') @rest; exit $LASTEXITCODE }
  'migrate' { & (Join-Path $PSScriptRoot 'migrate.ps1') @rest; exit $LASTEXITCODE }
  'test' { & (Join-Path $PSScriptRoot 'complete-gate.ps1') @rest; exit $LASTEXITCODE }
  'preview' { & (Join-Path $PSScriptRoot 'start.ps1') @rest; exit $LASTEXITCODE }
  'release' { & $python '-m' 'scripts.python.production_release_cli' 'promote' @rest; exit $LASTEXITCODE }
  'recover' { & (Join-Path $PSScriptRoot 'content-workspace-recovery.ps1') @rest; exit $LASTEXITCODE }
  'rollback' { & $python '-m' 'scripts.python.production_release_cli' 'rollback' @rest; exit $LASTEXITCODE }
  default { Write-Error 'usage: production-ready.ps1 setup|generate|migrate|test|preview|release|recover|rollback [arguments]'; exit 64 }
}
