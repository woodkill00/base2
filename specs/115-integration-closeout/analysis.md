# Analysis and issue ledger

## Cycle 1: discovery

| ID      | Category              | Evidence / reproduction                                                                                  | Action / regression                                                                                  | Status                                |
| ------- | --------------------- | -------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | ------------------------------------- |
| C115-01 | Evidence drift        | Feature114 T074-T076 unchecked despite accepted candidate, human Google confirmation, teardown and merge | Reconcile exact receipts; no fabricated feature-wide pass                                            | Open                                  |
| C115-02 | Coverage              | enabled-modules.spec.ts fulfills API requests with fixtures                                              | Add isolated PostgreSQL lifecycle coverage with restricted roles                                     | Open                                  |
| C115-03 | Coverage              | email container runner covers first/restart/corrupt only                                                 | Test ownership, expiry/exhaustion, lease initialization, cleanup failures and gate wiring            | Open                                  |
| C115-04 | External prerequisite | Live verification/reset/contact outcomes need disposable identity and delivery proof                     | Request owner identity approval, retain synthetic versus real distinction                            | Awaiting owner; local tests unblocked |
| C115-05 | Security scope        | Existing unused code flow shares GOOGLE_OAUTH_ENABLED; selected preview has no secret/state config       | Characterize missing/full config without enabling provider flow; review state replay/PKCE separately | Audit pending                         |
| C115-06 | Reliability           | F114-17 runtime intermittency and F114-34 execution-speed variation                                      | Preserve first failures and measured bounded checks, never promise elimination                       | Audit pending                         |

No design or provider changes in this planning batch. Read-only prerequisites
confirmed Docker 29.1.3 and local images. Existing synthetic container mounts and
pytest fixtures must be reviewed before use. Additional tasks will be recorded
after endpoint and backend inspection, before implementation.

## Cycle 2: bounded email and booking batch

- C115-03: eight network-disabled container phases now pass through the actual
  adapter factory; five initial runner tests passed after reproducing the missing
  cleanup boundary. Required gate wiring adds a sixth contract test. Initialization
  non-reset and broader ownership cases remain open; do not claim full R03 closure.
- C115-07 (test defect): reset journey asserted no sessions without establishing
  one first. Require a real successful login and nonempty sessions before reset.
  Added expired verification and unchanged-user checks. Disposable PostgreSQL
  acceptance passed on 2026-10-18, including five integration tests; local log
  `/tmp/base2-f115-postgres.log`. No external email sent.
- C115-08 (product defect): API scheduling reservation reads `ends_at` but ignores
  it, unlike Django's closed-event rule. Add expired/closed event regressions.
- C115-09 (product defect): Django checks capacity before looking up an existing
  booking, rejecting an identical replay once full. Add full-capacity replay and
  conflicting replay regressions; preserve capacity locking for new reservations.

Batch analysis: keep canonical Django and API behavior aligned, preserve tenant
isolation and transactional locks; test new reservations, identical/conflicting
replays, closed/expired events and capacity rejection. Real restricted-role
PostgreSQL validation remains required before marking the module work complete.

## Cycle 3: actual restricted-role failure

- C115-08/C115-09 reproduced before repair (API expired-event test failed;
  Django full-capacity replay test failed). Repairs pass four API and two Django
  tests. This is focused evidence only, not deployment acceptance.
- C115-10 (release blocker, runtime authorization): new actual PostgreSQL
  scheduling lifecycle fails `InsufficientPrivilege` for `scheduling_event`.
  Evidence: `/tmp/base2-f115-booking-postgres.log`; the supported runner exits 1.
  Do not grant blanket table access or remove the new regression. A narrowly
  scoped reservation capability, tenant isolation, denied direct mutation tests,
  migration reversal and role separation are required. The original repository
  uses SELECT FOR UPDATE, so read-only grants alone cannot repair reservations.
- Current tests: 51 runner/gate/guard tests passed; eight synthetic mail container
  phases passed using both existing isolated and production-like API images.
  The earlier full disposable database acceptance passed strengthened email
  scenarios plus five integration tests. That receipt predates C115-10's new
  check and does not supersede its failure.
- No full release gate, provider action, real mail send, new merge or deployment
  has been performed for Feature115. Human live/mailbox approvals remain pending.

Next repair batch must resolve C115-10 and validate booking plus adjacent content
permissions before expanding the browser evidence. Remaining OAuth, visual,
notifications and full-release tasks stay open, not inferred complete.

## Cycle 4: scoped booking repair evidence

C115-10 repaired through migration 0035: the API receives tenant-scoped event
SELECT and execute access to a fixed reservation function. It receives no booking
table reads, direct inserts/deletes or event updates. The function pins search_path,
fully qualifies relations, validates inputs and tenant context, serializes on the
event row, and checks expiry, replay and capacity. PUBLIC execute is revoked.

The first migration attempt exposed C115-11: Django interpreted PL/pgSQL `%ROWTYPE`
as a parameter placeholder. `params=None` fixes the static SQL execution; a
migration regression asserts this call. The original failure is retained.

Actual disposable PostgreSQL acceptance then passed, including the new booking
check and five final integration tests. Evidence is copied under
`.artifacts/feature-115/`:

- `base2-f115-postgres.log`: strengthened email/session/verification checks pass.
- `base2-f115-booking-postgres.log`: original missing runtime privilege failure.
- `base2-f115-booking-repaired.log`: migration placeholder failure.
- `base2-f115-booking-migration-fixed.log`: corrected database run passes.

Eight API repository tests and seven Django model/permission tests passed.
These database receipts precede final formatting and are repair evidence, not
exact-final-source release receipts. Concurrency capability tests, explicit
capability reversal checks, final coverage and complete release gate remain open.
No full gate or live deployment has been attempted in Feature115.

## Approved disposable identity

Owner approved the exact disposable alias and one bounded trial on 2026-10-18.
The mail-trial configuration previously rejected that alias. A failing regression
reproduced the prerequisite gap; the allowlist now includes exactly the approved
alias, not arbitrary plus-addresses. Each handoff still activates only its one
recipient. Tests reject other aliases, lookalike domains, multiple recipients,
newline injection and non-string recipient data. Existing expiry, five-attempt
maximum, private-file validation and non-reset budget rules remain unchanged.

## Cycle 5: actual visual review and concurrency

The 102-case three-browser journey run passed before adding a newly discovered
visual regression. Captures were inspected for mobile expired reset, Arabic RTL
long content and Firefox enlarged-text keyboard contact. The latter exposed
C115-12: the narrow-layout right edge tab uses a fixed/clamped top position and
overlaps the enlarged header's Sign Up action. Preserve its colors/shape and
normal spacing; measure header layout height and add only the necessary minimum
clearance. Add an actual geometry assertion to the named enlarged-text state,
then inspect the repaired capture before any baseline consideration.

The actual restricted-role booking race passed with one confirmed request and
one capacity rejection, exactly one stored seat. Evidence:
`.artifacts/feature-115/booking-concurrency.log`. Alert destination clarification
was requested; no destination or successful external delivery is assumed.

## Cycle 6: focused repair acceptance and remaining decisions

- C115-12 reproduced in Firefox by checking header/tab rectangles, repaired via
  observed layout-pixel header height and a minimum narrow-screen clearance.
  Three-browser enlarged-text checks passed and the repaired Firefox capture was
  inspected. All 73 Volcano reference/route checks passed without updating any
  reference images (`volcano.log`). Six component tests passed, including observer
  cleanup; an absent-ResizeObserver fallback was added after unit-environment failure.
- C115-13: private budget schema accepted boolean/float versions by numeric
  equality. Both new cases failed before repair and now reject malformed versions.
  81 focused mail/budget/health/configuration tests pass. Actual configurator-created
  private files survive container restart; attempted reinitialization leaves key,
  ledger and environment bytes unchanged. Ten isolated container phases pass
  (`mail-container-final.log`), with zero external requests.
- `database-final-focused.log` passes real optional blog/portfolio/doc publication
  transitions, booking race/denial/replay/recovery and explicit reverse checks
  proving the function, policy and read grant are removed. Five final integration
  tests pass. Hosted CI now invokes the same real module checks under a separate
  restricted role; hosted evidence is still pending.
- 22 OAuth boundary tests pass. GIS remains the selected flow. The unused
  authorization-code flow is not enabled by this feature, and has no PKCE
  acceptance claim. Missing configuration and provider rejection establish no
  identity/session and do not expose provider error contents.
- Harness errors retained: initial focused Vitest invocation used repository root
  rather than react-app config; a second invocation supplied conflicting coverage
  flags. Correct working directory and a single coverage option fixed invocation;
  these are not product regressions or accepted test receipts.

Two owner clarifications are pending before final scope/release: the existing
Discord webhook item/channel for real alert-delivery evidence; and whether the
contact form's existing persisted receipt is the intended outcome or new contact
email notifications must be implemented. Current code explicitly queues a
disabled form-delivery adapter, not a functioning contact-email sender. No new
destination, contact email behavior or successful delivery is assumed.

Full release gate, changed-line coverage, final source-bound visual review,
publication/CI, live email outcomes, merge and teardown remain open. The single
approved live trial is unused. All evidence paths above are relative to
`.artifacts/feature-115/`; focused passes are not complete-release receipts.

## Cycle 7: owner scope clarification and checkpoint

- Owner confirmed contact acceptance means received and stored submissions;
  contact-email notifications are explicitly a separate feature. Existing
  disabled delivery adapters must not be represented as functioning email.
- Owner believes no Base2 Discord webhook has been created. Real alert delivery
  is unavailable, not passed. Asked whether to configure an existing private
  channel destination or explicitly defer delivery; neither is assumed approved.
- Checkpoint 80d6fb9 preserves the implementation and regressions. The first
  commit hook rejected a stale surface configuration digest after release-gate
  changes. Supported `validate_surface_drift.py --write` refreshed only that
  configuration digest; the subsequent hook passed. No test pass receipt or
  visual baseline was rewritten to resolve this configuration inventory drift.
- Next bounded batch: coverage-policy and source-bound visual review inventory,
  followed by the necessary focused validation before the full release gate.
  No paid trial, external email or new notification destination has been used.
- Contact persistence assertion initially expected the model default `received`;
  the repository and restrictive INSERT policy explicitly use internal `queued`
  with a disabled adapter. This is a test expectation mismatch, not proof of
  email delivery. Corrected the assertion to require exact payload/consent,
  `queued`, no delivered timestamp and a future retention deadline. First failure
  is preserved in `contact-stored-acceptance.log`; corrected run is separate.
- Owner explicitly deferred Discord delivery and requested a later task. D115-01
  records secure destination setup, failure/retry/redaction tests, real delivery
  receipt, owner visibility and rollback. Delivery stays disabled; it is excluded
  by owner decision, not marked tested. No webhook or destination was created.
- Corrected contact acceptance passed (`contact-stored-corrected.log`), including
  restricted-role persistence, scheduling race, migration reversal and recovery.
  Frontend coverage passed 370 tests across 83 files; Operations Center comparison
  passed 22 cases with 20 intentional exclusions and unchanged reference images.
  Supported visual evidence regeneration binds the two changed shared-style sources.
- API, Django and deployment-code coverage runners passed, followed by the root
  runner and coverage policy. Current measured changed-line coverage is 102/111
  (91.89%, floor 90%); critical glass coverage is 100% across reported metrics.
  This policy measures instrumented lines, not every changed file or unknown
  failure scenario. Evidence is in `*-coverage.log` and `coverage-policy.log`.
  Full gate, remaining media source review, CI and live acceptance are still open.

## Cycle 8: exact-source gate prerequisite

- C115-14 (evidence prerequisite, not a product failure): full gate
  `20261018T035021Z-4048538` on `af87aec` failed because current-head Feature106
  repetitions had not been generated. It reported `repetition_evidence_invalid`;
  dependent checks stayed not-run. All other executed checks passed. Preserve
  the original result; no existing receipt is to be edited or relabeled.
- Repair: after committing this batch, run the supported Feature106 repetition
  generator on that exact clean commit, validate its evidence, then rerun the
  complete gate without editing source. This prerequisite must precede future
  full gates, including documentation-only source changes while exact-head
  evidence remains mandatory. No weakened assertion or timeout is needed.
- Current visual review: 102 journey checks passed on the candidate in 2.4m;
  approved Volcano references remain unchanged. Media renewal passed 24 applicable
  checks with 12 intentional exclusions and binds commit `7d7fd13`; its reviewed
  UI sources are unchanged afterward. Operations comparisons passed 22 with 20
  explicit exclusions. Geometry/state coverage and pixel comparison remain distinct.
- Historical F114-17 native/runtime intermittency and F114-34 timing variability
  remain residual environment risks, not defects proven eliminated. Current API,
  Django and deployment-code coverage runs passed without an observed recurrence;
  exact-head stability repetitions are still required before release.
- Contact acceptance is persisted payload/consent/retention with no delivered
  timestamp; its queued disabled adapter is not email delivery. Verification/reset
  use the separate mail outbox, private send budget and one-use token/session
  boundaries tested in disposable PostgreSQL. Discord dispatch-disabled regression
  confirms no tenant/runtime secret reads while disabled; real delivery is D115-01.

Reanalysis: remaining acceptance is the current-head repetition prerequisite,
complete gate, hosted CI, bounded live outcomes with human mailbox confirmation,
independent teardown and merge/post-merge verification. Optional pack browser
fixtures do not replace actual restricted-role database evidence. No new feature,
external destination or additional paid trial is introduced by this repair.
