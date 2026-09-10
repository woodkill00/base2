# Data Model: Efficient Assurance Orchestrator

## AssuranceGraph

- `schemaVersion`, `graphVersion`
- closed `tiers` and escalation order
- ordered `pathRules` with glob, surface, and minimum tier
- `surfaces` with dependent surface IDs
- `checks` with fixed argv, dependencies, timeout, resource class, cache policy, relevant inputs, and mandatory tiers
- `outputPolicy`, `evidencePolicy`, `resourcePolicy`

## ChangeSet

- `baseCommit`, `headCommit`, `diffDigest`
- sorted entries: status, old path when renamed, path
- `dirty` and `selectionSource`

## ExecutionPlan

- `planDigest`, graph identity, change-set identity
- requested and resolved tier
- selected checks with reason chains
- avoided checks with honest residual scope
- execution order and resource admission

## CheckReceipt

- check ID and input digest
- status: passed, failed, blocked, unavailable, interrupted
- exact argv digest, relevant-input digest, toolchain digest
- started/finished times and duration
- attempts and retry class
- bounded summary and private log hash/size
- expiry and integrity digest

## RunReceipt

- source, plan, and graph digests
- status and selected/reused/executed/avoided IDs
- wall/process time, output bytes, token estimate
- check receipt references
- integrity digest

## Invariants

- Only a complete `passed` check receipt can be reused.
- Release checks are fresh unless the graph explicitly permits exact replay.
- All names and paths are closed; commands cannot originate from CLI input.
- Aggregate pass requires every selected mandatory check to pass.
- Evidence is private and integrity-checked before use.
