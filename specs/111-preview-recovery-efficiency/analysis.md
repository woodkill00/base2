# Analysis cycle

## Cycle 1 — discovery before implementation

Known gaps added as tasks before code:

- Lease is saved only after successful deployment: add T003–T007.
- Preparing a lease alone is insufficient: a lost provider response can leave an
  unbound resource; current teardown would mark it destroyed. Add T006,T009.
- DNS mutation and lease persistence are separate: interruption can orphan records
  or lose prior-record rollback. Add T008; do not claim compute fix closes DNS.
- Existing lease locks protect single writes, not launch vs expiry transactions.
  Add T010; durable schedule integration must not race an ongoing launch.
- Last preview used a one-off saved timer; future launcher still uses transient
  scheduling. Add T011,T012; WSL-off limitation must remain explicit.
- Revised fixture helper exists outside product repo: add T013 and consumer audit.
- Prior full gate spent time before detecting stale evidence: add T015, but keep
  source-bound assurance semantics and release gates unchanged.

No known missing task for these identified failures. This is planning coverage,
not proof of implementation correctness or absence of unknown defects. Batch 1
may proceed; live release remains blocked on remaining tasks and review.

## Cycle 2 — lifecycle exclusion review

Implement a nonblocking operation lock shared by launch and teardown, separate
from per-write locks. Competing operations must report busy without provider reads
or mutations; crashes release the kernel lock. Reject linked/nonprivate lock files.
Directory fsync is required after atomic lease replacement for restart durability.
The lock scopes one lease root: distinct roots targeting the same DNS zone still
need cross-run admission (added T019). DNS recovery remains T008/T009, not closed
by operation locking. Budget: one red concurrency run and one combined corrected
run, with extra runs only after a relevant correction.

Review added T020: failure cleanup used the most recent untrusted provider response
as its delete target. It now uses the saved identity and revalidates the live
identity before deletion. Invalid or drifted responses retain a blocked lease.

DNS receipt binding now precedes public probing. An in-progress DNS marker makes
expiry stop explicitly on an interrupted migration, rather than silently deleting
compute and claiming cleanup complete with unknown DNS records. This is containment,
NOT journal recovery: T008/T009 remain open and release-blocking. The marker may
also require reconciliation after a rolled-back DNS error; no automatic waiver.

## Cycle 3 — integrated review

DNS journaling and bounded read-only reconciliation are implemented. Unknown write
outcomes explicitly require owner reconciliation; they are never retried blindly.
Journaled deletion rechecks observed identity. A persistent schedule is rendered,
saved and verified before create by the production launch entrypoint. Domain-level
admission excludes same-account launches across per-run directories.

New release-blocking tasks from review:

- T021: remote bootstrap permits 2,700 seconds, whereas preview policy permits
  a 15-minute TTL. Operation locking plus five cleanup retries could exhaust the
  retry budget before launch returns. Need deadline/cleanup convergence coverage.
- T022: existing provider adapters can interpret missing/paginated inventory as
  absent; malformed/partial inventory must not authorize a new launch or terminal cleanup.
- T013: active WSL helpers are absent in Windows notebook. Its mandated sync uses
  rsync --delete. Do not run it or modify the WSL-only helpers without a scoped
  exception. Owner question sent; safe repository work proceeded independently.

PowerShell is not installed in this WSL environment. Native wrapper execution
cannot yet be claimed, though both wrappers now target the same module directly.
The unit files pass actual systemd-analyze validation without being installed.
No final gap-free analysis or release acceptance is claimed while these remain open.

T021/T022 implementation review: persistent calendar plus inactive-service retry
keeps cleanup eligible after busy launch windows; terminal replay disables only its
derived timer and reads no provider credential. Launch checks expiry before create,
after deploy, before DNS and after probe. Missing/paginated list responses now
reject rather than prove absence. Current provider-free regressions pass.
Workstation consumer migration is still blocked on the requested scoped exception.

## Final integration review

Owner granted the exact three-helper WSL exception. Launcher now delegates to the
guarded CLI without duplicate transient scheduling or diagnostic bypass. Browser
and media-principal helpers consume the tracked validator; static checks and shell
syntax pass without live execution. No Windows sync or other helper edit occurred.

The remaining dashboard route/heading race has a shared helper and real Chromium
regressions included in the complete gate. Two checks pass. Native PowerShell is
not installed; its direct Python wrapper is reviewed, not claimed runtime-tested.
Linux/WSL is the supported launch platform. No visual baseline or design change.

No known missing implementation task remains in this bounded feature. Release gate
and final coverage/closeout remain T017/T018. Unknown defects, provider ambiguity,
workstation-off cleanup delay and independent-operator races remain explicit risks,
not promises of universal autonomous recovery.
