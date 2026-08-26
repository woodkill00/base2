# Data Model

## ControlReceipt

- `schemaVersion`
- `ok`
- `command`
- `code`
- `runId` (optional)
- `requestDigest`
- `summary`
- `details`
- `cleanupState`
- `recommendedAction`
- `secretValuesEmitted` = `0`

## RuntimeReceipt

- repository path and filesystem class
- WSL/Linux detection
- architecture
- tool name, resolved path, binary class, and version
- violations
- credential reads = `0`

## PreviewInventory

- canonical state root
- valid lease summaries
- invalid lease findings
- live/expired/destroyed/pending counts
- conflicts
- provider reconciliation status when separately authorized

## DnsConvergenceReceipt

- domain and exact expected address
- required hostnames
- provider observations
- public-recursive observations by resolver
- system-recursive observations
- unexpected A/AAAA answers
- stale/split/converged classification
- safe remediation

## ExpiryPlan

- run ID
- lease path digest
- exact expiry timestamp
- fixed executable/module
- credential-file path digest, never value
- timer identity
- persistent/catch-up flags
- armed and verified state

## VisualArtifact

- logical identity: route + area + viewport + state + browser
- relative path
- media type
- byte size
- SHA-256
- dimensions
- commit/profile/run bindings
- review state: pending/approved/rejected

## VisualEvidenceBundle

- schema version
- source commit and profile digest
- run ID and leased address
- artifact list
- required coverage matrix
- missing/duplicate/rejected findings
- HTML index path and bundle digest
