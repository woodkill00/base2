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
- [x] T006 Run final release gate/CI, publish repair and obtain merge approval.
- [x] T007 Obtain a fresh bounded live-trial approval, run automated acceptance,
      inspect screenshots, verify teardown; preserve failures and deferred checks.

No paid resources or new live attempts are authorized by this task ledger.

## Final outcome

PR85 merged to main 5c1ba450149c8221397bb03088254162a138577d.
Exact-source complete gate: 132 passed, zero failed/blocked, at
`.artifacts/complete-gate/20261020T093306Z-2667976/result.json`.
Post-merge hosted checks passed. Approved trial base2-full-20261020-095030
proved antivirus cold startup healthy with fresh signatures and all 17 services
healthy. Browser acceptance was **13 passed, 1 failed**, not a complete pass:
the privacy export exposed a freshness/expiry client bug. Visual inspection
also found a Google frame canvas mismatch. Both are tracked in Feature119.
Runtime export verification consequently failed; no successful export was queued.
Teardown deleted one droplet and six temporary DNS records; subsequent inventory
confirmed zero. No real test emails or interactive Google sign-in were performed.
This trial approval is consumed. Earlier failures remain preserved.

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
