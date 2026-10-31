# Supported in PowerShell 7 on Linux/WSL: the shared no-follow lock uses fcntl.
$ErrorActionPreference = 'Stop'
if (-not $IsLinux) { throw 'Isolated E2E requires PowerShell 7 on Linux/WSL (fcntl lock).' }
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$lockArgs = @((Join-Path $repoRoot 'scripts/python/secure_file_lock.py'), '--lock', (Join-Path $repoRoot '.artifacts/e2e-isolated.lock'), '--root', $repoRoot, '--busy-exit', '3')
if ($env:E2E_READY_FD) {
    if ($env:E2E_READY_FD -notmatch '^\d+$') { throw 'Invalid E2E_READY_FD' }
    $lockArgs += @('--ready-fd', $env:E2E_READY_FD)
}
& python3 @lockArgs -- pwsh -NoProfile -File (Join-Path $PSScriptRoot 'e2e-isolated-body.ps1') @args
$code = $LASTEXITCODE
if ($code -eq 3) { [Console]::Error.WriteLine('ERROR: the fixed isolated E2E project is already in use') }
exit $code
