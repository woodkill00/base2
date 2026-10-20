# Preview antivirus startup repair

## Scope and analysis

Source: main 8504ea0; failed trial base2-full-20261020-062149.
ClamAV signature testing was last observed before warm-up exited 4. Cleanup is
verified; the exact failure subtype was not retained. Do not claim an OOM or
timeout as established fact. Runtime mail and Google interaction remain deferred.

The launcher allows 180 two-second polls, but both Compose profiles start counting
failed checks after ten seconds (five retries at thirty-second intervals). This
permits premature unhealthy classification during legitimate cold initialization.
Align the startup grace with the existing six-minute deadline, without accepting
unhealthy state, extending the lease, changing signature freshness, granting
privileges, or changing CPU/memory limits.

Failure records must retain only a fixed enumerated cause, never raw logs,
exception text, credentials or healthcheck output. Unknown/malformed/conflicting
markers remain unknown. Evidence-write failure must not prevent cleanup.

- [x] T001 Add regressions for startup-budget parity and typed failure evidence.
- [x] T002 Align Compose startup grace with the existing bounded warm-up budget.
- [x] T003 Emit/parse reason-specific warm-up failure markers and persist safely.
- [x] T004 Test hostile markers, metadata mutation, timeout and cleanup behavior.
- [x] T005 Review affected consumers and repeat analysis; run focused checks.
- [ ] T006 Run final release gate/CI, publish repair and obtain merge approval.
- [ ] T007 Obtain a fresh bounded live-trial approval, run automated acceptance,
      inspect screenshots, verify teardown; preserve failures and deferred checks.

No paid resources or new live attempts are authorized by this task ledger.

## Analysis cycles and evidence

Cycle 1 identified startup-grace inconsistency plus loss of failure subtype.
Cycle 2 added duplicate/hostile marker rejection, revalidation of mutable
exception properties and cleanup when evidence persistence fails.
Cycle 3 added execution of the actual warm-up shell for healthy, OOM, exit,
unhealthy and deadline cases, plus remote-adapter tests for normal and byte-stream
timeout failures. No known blocking gap remains for this bounded repair;
real cold-start completion is still unproven until the new live trial.

Initial failing regression: `/tmp/base2-f118-repro.log`.
Final focused suite: 89 passed in `/tmp/base2-f118-focused-final.log`.
Shell syntax, source-surface inventory and diff checks passed. No visual/style
sources changed. Full release gate/CI and live acceptance remain outstanding.
