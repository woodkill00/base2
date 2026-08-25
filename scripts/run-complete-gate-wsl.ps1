[CmdletBinding()]
param(
    [string]$Distro = 'Ubuntu-24.04',
    [string]$RepoPath = '/home/woodkill/code/base2'
)

$ErrorActionPreference = 'Stop'
$gateCommand = "cd '$RepoPath' && python3 scripts/python/run_complete_gate.py"
$commitCommand = "cd '$RepoPath' && git rev-parse HEAD && git diff --quiet && git diff --cached --quiet"
$classifyCommand = "cd '$RepoPath' && python3 scripts/python/classify_gate_runtime_failure.py"

function Invoke-WslCommand([string]$Command) {
    & wsl.exe -d $Distro -- bash -lc $Command | ForEach-Object { Write-Host $_ }
    $code = $LASTEXITCODE
    return $code
}

$initialCommit = (& wsl.exe -d $Distro -- bash -lc "cd '$RepoPath' && git rev-parse HEAD").Trim()
if ($LASTEXITCODE -ne 0 -or $initialCommit -notmatch '^[0-9a-f]{40}$') {
    throw 'Unable to bind the gate to an exact WSL commit.'
}
if ((Invoke-WslCommand $commitCommand) -ne 0) {
    throw 'Tracked or staged changes must be committed before the exact gate.'
}

for ($attempt = 1; $attempt -le 2; $attempt++) {
    $exitCode = Invoke-WslCommand $gateCommand
    if ($exitCode -eq 0) {
        exit 0
    }

    & wsl.exe -d $Distro -- bash -lc $classifyCommand
    $classificationExit = $LASTEXITCODE
    if ($classificationExit -ne 75) {
        Write-Error 'Complete gate failed for a product/test reason; WSL recovery is forbidden.'
        exit $exitCode
    }
    if ($attempt -eq 2) {
        Write-Error 'Native corruption recurred after the single bounded WSL recovery.'
        exit $exitCode
    }

    Write-Warning 'Native WSL runtime corruption detected. Performing one bounded WSL restart.'
    & wsl.exe --shutdown
    if ($LASTEXITCODE -ne 0) {
        throw 'WSL shutdown failed.'
    }
    $currentCommit = (& wsl.exe -d $Distro -- bash -lc "cd '$RepoPath' && git rev-parse HEAD").Trim()
    if ($LASTEXITCODE -ne 0 -or $currentCommit -ne $initialCommit) {
        throw 'Exact source commit changed across WSL recovery.'
    }
}
