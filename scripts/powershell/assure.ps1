[CmdletBinding()]
param(
    [ValidateSet("plan", "run", "status", "explain")]
    [string]$Action = "run",
    [ValidateSet("auto", "focused", "standard", "full", "release")]
    [string]$Tier = "auto",
    [ValidatePattern("^[0-9a-f]{40}$")]
    [string]$Base,
    [switch]$Json
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$Arguments = @((Join-Path $Root "scripts/python/assurance_orchestrator.py"), $Action, "--tier", $Tier)
if ($Base) { $Arguments += @("--base", $Base) }
if ($Json) { $Arguments += "--json" }
& python @Arguments
exit $LASTEXITCODE
