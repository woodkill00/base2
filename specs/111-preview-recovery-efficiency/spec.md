# Feature 111 — Recoverable previews and efficient verification

## Outcomes

- R1: A preview has a durable, private cleanup record before spending begins and
  binds returned compute identity before waiting or deploying. Interrupted startup
  is visible, never reported as successful cleanup without inventory proof.
- R2: Future workstation cleanup schedules survive restart, retain original expiry,
  retry bounded transient failures and clearly disclose that offline WSL cannot act.
- R3: DNS changes are journaled and recoverable without deleting another owner's
  records. Ambiguous provider outcomes stop for reconciliation, not blind retry.
- R4: Live test identities and rendered-state readiness are consistent across setup
  and browser consumers; fixture errors remain distinct from product failures.
- R5: Supported assurance preflights expose stale prerequisites before expensive
  checks, without weakening exact-source, security, coverage or visual requirements.
- R6: Compact reports preserve first failures, recovery evidence and residual risks.

## Acceptance

Provider-free interruption, identity mismatch, replay, cleanup failure and restart
simulations must pass. Existing lifecycle tests must continue passing. Release uses
the existing assurance selector and mandated complete gate, with changed-line
coverage reviewed first. No fixture simulation counts as live provider validation.

## Boundaries

No paid preview, DNS mutation, credential changes, production certificates, new
agents, publication or merge in this implementation batch. No application design,
screenshots, legal content or access-control changes. Preserve Volcano exactly.
Owner visual acceptance of Feature 110 remains separate from automatic checks.

## Scenarios

1. Operator loses power while a droplet starts: a prepared/bound lease survives;
   later cleanup verifies exact identity or reports an ambiguity.
2. Provider accepts creation but its reply is lost: no automatic second create and
   no false destroyed receipt; bounded inventory reconciliation is required.
3. Tests need a fresh fixture revision: setup and browser use the same identity.
4. Required evidence is stale: report the prerequisite before running a full gate.
