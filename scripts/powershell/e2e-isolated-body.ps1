# Local HTTP service proof only, not TLS or seeded-asset scanning acceptance.
# Controlled-clock service proof is separate from the unchanged real beat schedule.
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$lockFile = Join-Path $repoRoot '.artifacts/e2e-isolated.lock'
if ($env:BASE2_SECURE_LOCK_FD -notmatch '^\d+$') { throw 'Secure E2E lock capability is missing' }
& python3 (Join-Path $repoRoot 'scripts/python/secure_file_lock.py') --lock $lockFile --root $repoRoot --verify-fd $env:BASE2_SECURE_LOCK_FD
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Remove-Item Env:BASE2_SECURE_LOCK_FD
$defaults = @{ E2E_API_PORT = '15001'; E2E_TEST_SUPPORT_PORT = '15002'; E2E_WEB_PORT = '18080' }
$ports = @()
foreach ($name in $defaults.Keys) {
    $value = [Environment]::GetEnvironmentVariable($name)
    if (-not $value) { $value = $defaults[$name] }
    if ($value -notmatch '^\d{4,5}$' -or [int]$value -lt 1024 -or [int]$value -gt 65535) { throw "Invalid unprivileged TCP port: $name" }
    [Environment]::SetEnvironmentVariable($name, $value)
    $ports += $value
}
if (($ports | Select-Object -Unique).Count -ne 3) { throw 'Isolated E2E ports must be distinct' }
$env:E2E_WEB_ORIGIN = "http://127.0.0.1:$env:E2E_WEB_PORT"
$env:E2E_BASE_URL = $env:E2E_WEB_ORIGIN
$env:E2E_API_URL = "http://127.0.0.1:$env:E2E_API_PORT"
$env:E2E_TEST_SUPPORT_URL = "http://127.0.0.1:$env:E2E_TEST_SUPPORT_PORT"
$env:E2E_TEST_KEY = 'local-e2e-key'
$artifacts = Join-Path $repoRoot 'e2e/artifacts'
if ((Test-Path $artifacts) -and (Get-Item $artifacts -Force).LinkType) { throw 'Unsafe E2E artifact directory' }
New-Item -ItemType Directory -Force -Path $artifacts | Out-Null
& chmod 700 $artifacts
if ($LASTEXITCODE -ne 0) { throw 'Cannot protect E2E evidence' }
foreach ($name in @('source-commit.txt', 'playwright.json', 'compose-ps.txt', 'compose.log', 'cleanup.log', 'exit-code.txt')) {
    $member = Join-Path $artifacts $name
    if (Test-Path $member) {
        $item = Get-Item $member -Force
        if ($item.LinkType -or $item.PSIsContainer) { throw 'Unsafe E2E artifact member' }
        Remove-Item -LiteralPath $member
    }
}
& git -C $repoRoot rev-parse HEAD | Set-Content (Join-Path $artifacts 'source-commit.txt')
if ($LASTEXITCODE -ne 0) { throw 'Cannot bind source commit' }
$env:PLAYWRIGHT_JSON_OUTPUT_NAME = Join-Path $artifacts 'playwright.json'
$composeArgs = @('compose', '-p', 'base2-e2e-isolated', '-f', (Join-Path $repoRoot 'e2e/docker-compose.e2e.yml'))
$code = 1
try {
    & docker @composeArgs down -v --remove-orphans
    if ($LASTEXITCODE -ne 0) { throw 'Initial E2E cleanup failed' }
    & docker @composeArgs up -d --build --wait --wait-timeout 240
    if ($LASTEXITCODE -ne 0) { throw 'E2E stack did not become healthy' }
    Push-Location (Join-Path $repoRoot 'e2e')
    try {
        & npm run test:ci -- --reporter=line,json --workers=1
        $code = $LASTEXITCODE
    } finally { Pop-Location }
} catch {
    [Console]::Error.WriteLine($_)
    $code = 1
} finally {
    & docker @composeArgs ps -a *> (Join-Path $artifacts 'compose-ps.txt')
    & docker @composeArgs logs --no-color *> (Join-Path $artifacts 'compose.log')
    & docker @composeArgs down -v --remove-orphans *> (Join-Path $artifacts 'cleanup.log')
    if ($LASTEXITCODE -ne 0 -and $code -eq 0) { $code = 1 }
    $code | Set-Content (Join-Path $artifacts 'exit-code.txt')
}
exit $code
