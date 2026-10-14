# Checkpoint — 2026-10-14

## Final safe checkpoint for this turn

**311 tests passed in 12.25 seconds.** Current measured changed Python executable
lines: **370/378 (97.88%)**, above the unchanged 90% floor. Evidence:
`.artifacts/feature111/validated-checkpoint.log`, `coverage.json`, `changed-lines.json`.
TypeScript, new-file lint and actual systemd unit syntax validation passed. No
services were installed or activated by validation. No full release gate ran.

Closed review findings T021/T022: periodic timer retries survive a busy launch
window, destroyed leases retire their timer without reading credentials, expiry
checks reject late launch stages, and incomplete/paginated inventories fail closed.
Failure/reconciliation paths remain intentionally non-destructive on ambiguous
provider outcomes. Tests cover expired setup and deployment, lost responses,
identity drift, real process-kill lock recovery, timer replay and read-only CLI.

Blocked on a user decision for the three WSL helper scripts: permission requested
to update those directly without the notebook's destructive sync. Helpers and
Windows notebook are untouched. Remaining tasks also include final wrapper/browser
acceptance, exact-source release validation and closeout. Nothing is represented
as merged, deployed or fully complete. Changes remain local, uncommitted.

## Latest implementation — awaiting workstation integration direction

Added durable DNS intent/result journaling, exact-identity journaled deletion,
read-only reconciliation, persistent user-unit installation before provider create,
cross-directory domain admission, shared fixture identity module and an assurance
preflight command. The remaining live media-login path now waits for the rendered
Dashboard heading. Launch CLI errors expose exception class, not provider messages.

Integrated preview/assurance tests: 298 passed before the final review additions.
Subsequent recovery review: 246 passed (different focused selection).
First changed-line measurement: 304/321 = 94.70%, above the unchanged 90% floor;
this predates final additions/formatting, so final coverage must be rerun.
TypeScript passed, new-file Ruff checks passed, and actual systemd unit validation
passed without installing/starting any unit. All logs remain in `.artifacts/feature111/`.

Failures retained and corrected: standalone preflight initially lacked its repository
import path; regression now invokes the real script. New-file import ordering,
overbroad exception assertion and loop-binding warnings corrected. Ruff is supplied
by `.venv-api`, not `.venv`. No failed gate was relabeled as passed.

Final analysis found T021/T022; release remains blocked, not done. T013 also needs
owner direction because mandated notebook sync could delete WSL-only helpers/data.
No sync, paid launch, provider mutation, merge, publication or full release gate ran.
Repository changes are staged/unstaged local work, not committed or deployed.

## Latest bounded batch

Added nonblocking lifecycle exclusion shared by launch and teardown, private-lock
checks and parent-directory fsync for durable lease replacement. Separate store
instances contend correctly; a real terminated child process releases its kernel
lock. Failed launch cleanup now revalidates persisted compute identity; malformed
or drifted responses authorize no deletion. DNS identities bind before public
probing; interruption inside DNS mutation explicitly requires reconciliation.

T010 and additional T020 are implemented. T008/T009 (durable DNS journal and
reconciliation), T011/T012 (persistent schedule), and T019 (cross-root admission)
remain required before release. No claim that interrupted DNS recovery is automatic.

Evidence: `.artifacts/feature111/` contains concurrency, identity-cleanup and DNS
boundary red runs and corrected validations. Broad preview regression first
reported 213 passed / 1 fixture failure: the old empty-lease fake prohibited the
new necessary read-only inventory check. Corrected fake permits only that read.
Final broad run `preview-regression-r2.log`: **214 passed in 6.03 seconds**;
`git diff --check` passed. This is focused provider-free validation, not the full
release gate or live cloud acceptance. Full gates: 0; deployments: 0 this feature.
Changes remain local and uncommitted. No design or baseline files changed.

The next work is DNS journaling/reconciliation, cross-root admission and persistent
scheduling; do not deploy this partial lifecycle candidate before those tasks pass.

## Previous batch

Feature branch created from f9440de. Scope is provider-free implementation only.
Feature 110 preview cleanup succeeded: inventory reported zero droplets and zero
managed DNS records. Owner visual acceptance V012 remains separate and unclaimed.

Initial five recovery regressions failed as expected (retained in
`.artifacts/feature111/startup-red.log`). The outer Windows launcher incorrectly
expanded a shell status variable and returned zero despite pytest failures; the
recorded five failures are authoritative, not that wrapper exit status. Subsequent
checks invoke pytest directly and preserve exit status without shell interpolation.

Early prepared and compute-bound leases, serial run-ID reuse prevention, sanitized
failure checkpoints and fail-closed unbound inventory checks are implemented.
Initial focused run: 16 passed. Adjacent lifecycle/DNS/policy/systemd suite: 50 passed.
Additional lost-response/cleanup-error tests included in the final focused round.

Release remains blocked on T008–T018. In particular, DNS journaling and operation
serialization must be implemented before deploying the early-lease lifecycle;
per-record locking alone does not protect launch against expiry. Persistent future
workstation scheduling is not installed by these changes. No design files changed,
no cloud resources created, no publication/merge/full release gate performed.

Next batch: journal DNS mutations and reconcile uncertain provider responses, then
serialize lifecycle operations before connecting restart-persistent scheduling.
