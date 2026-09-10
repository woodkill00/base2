# CLI Contract

## Bash

`scripts/bash/assure.sh [plan|run|status|explain] [--tier auto|focused|standard|full|release] [--base COMMIT] [--json]`

## PowerShell

`scripts/powershell/assure.ps1 -Action <plan|run|status|explain> -Tier <auto|focused|standard|full|release> [-Base COMMIT] [-Json]`

## Rules

- Default action is `run`; default tier is `auto`.
- `--base` accepts only an existing full 40-hex commit reachable from HEAD.
- No command, path, environment variable, URL, credential, provider, or exclusion is accepted from the caller.
- `plan` performs no tests and writes no pass evidence.
- `run` acquires the fixed private lease, executes the fixed plan, and returns 0 pass, 1 test failure, 2 validation/integrity failure, 3 busy, or 130 interruption.
- `status` reads only the current exact-source receipt.
- `explain` prints selection reason chains and residual scope, still within configured output bounds.
- `release` always invokes the existing complete gate and requires fresh exact-head repetition evidence under its existing policy.
- A clean `auto`, `focused`, `standard`, or `full` request may be satisfied without execution by a current integrity-valid exact-commit complete-gate receipt whose ordered check inventory exactly matches the current manifest. An explicit `release` request never uses this shortcut.
- Default output is compact readable text. `--json`/`-Json` returns the bounded machine-readable JSON contract.
- A check fails with exit 125 if its exact repository source changes during execution; no cache receipt is published for that check.

## Compact JSON (`--json` / `-Json`)

Required top-level fields: `schemaVersion`, `status`, `sourceCommit`, `requestedTier`, `resolvedTier`, `planDigest`, `selected`, `reused`, `executed`, `failed`, `avoided`, `wallMilliseconds`, `outputBytes`, `estimatedTokens`, `evidencePath`.

Failed summaries additionally include bounded `failureDetails` with check ID, exit code, attempts, and a redacted diagnostic tail.
