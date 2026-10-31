$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$pythonRelative = if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT) { '.venv/Scripts/python.exe' } else { '.venv/bin/python' }
$python = Join-Path $repoRoot $pythonRelative
$previousShell = $env:BASE2_GATE_SHELL
$hadShell = Test-Path Env:BASE2_GATE_SHELL
$code = 1
try {
    $env:BASE2_GATE_SHELL = 'pwsh'
    & $python (Join-Path $repoRoot 'scripts/python/run_complete_gate.py')
    $code = $LASTEXITCODE
} finally {
    if ($hadShell) { $env:BASE2_GATE_SHELL = $previousShell }
    else { Remove-Item Env:BASE2_GATE_SHELL -ErrorAction SilentlyContinue }
}
exit $code
