# Analysis and issue ledger

## Cycle 1 — scope refinement

Route visit != completed workflow; capture != approved comparison; fixture UI !=
backend acceptance; disabled module != enabled module coverage. Existing Feature
112 live evidence remains valid only for its source and eleven defined cases.

Added T006 before backend journeys: prevent accidental real email/account mutation.
Added T013 approval boundary: never generate baselines just to make tests green.
Added T015: new tests must join normal assurance, not become optional orphan files.
Added T014: existing compatibility tests do not prove all authenticated journeys.
No known planning blocker to the first credential-free public/auth batch.

## Diagnostic candidates (not confirmed defects yet)

- Search accepts overlapping requests and has no cancellation/generation guard;
  reproduce stale results before patching. Consumers: enabled public/localized search.
- Shared content API converts all 404 responses into null, including contact POST;
  determine whether unavailable form incorrectly appears successfully received.
- Password reset schedules navigation without unmount cleanup; reproduce before
  deciding whether user navigation can be unexpectedly overridden.

## Evidence rules

Keep first failing tests/logs and separate product, fixture, environment and missing
prerequisite issues. No full gate or paid trial has run for Feature 113 yet.

## Cycle 2 — first diagnostic sweep and repairs

- F113-01 (high, product): shared API swallowed contact/search/list HTTP404;
  confirmed three red regressions; allow missing only for detail/page reads.
- F113-02 (medium, product): stale search success/failure overwrote newer results
  or validation; confirmed three red regressions; generation-bound responses.
- F113-03 (high, product): unstable verifyEmail callback retriggered the effect on
  error state updates (137 and 129 requests in synthetic browser cases). Stabilized
  callback; exact-one-request unit/browser regressions now pass.
- F113-04 (medium, visual): screenshot inspection found cramped contact controls;
  touch-target regression red; reuse existing GlassCard/GlassButton/input styling.
- F113-E01 (fixture): legacy experience runner omitted restored-layout flags;
  separate journey runner uses both approved flags. No weakened shell assertion.
- F113-E02 (fixture): contact status locator matched menu output too; scope by
  receipt text. Vitest rewrites import.meta URLs; resolve inventory from repo cwd.

Evidence: .artifacts/feature113-first-failures.log,
feature113-browser-first.log, feature113-browser-corrected.log,
feature113-browser-repaired.log, feature113-contact-touch-red.log.
24 focused tests and ten synthetic browser journeys passed before the contact
visual correction. First failures retained. No new baselines approved or live
backend acceptance inferred. Local Compose healthy; isolated mail prerequisite
still under review (local_fake exists, current stack lacks email worker).

## Cycle 3 — additional repair and validation tasks

- F113-05 (medium, product): successful password reset retained its redirect timer
  after unmount. Reproduced; effect-owned cleanup plus abandonment regression.
- F113-06 (medium, product): Explore linked to nonexistent /content. Route inventory
  regression reproduced; canonical profile now points to /journal, generated via
  supported generator. Browser click reaches populated journal in all engines.
- F113-07 (medium, capability gap): search ignored nextCursor. Added manual paging,
  deduplication, preserved rows on failure, retry, stale-page and repeated-cursor
  guards. New tests must never replace incomplete results with silent success.
- E03: Firefox/WebKit restrict service port4190. Changed only journey server to
  4194; no browser security override. Initial multi-engine run was interrupted
  after common prerequisite failure; unrun cases remain unrun, not passed.
- E04: disposable PostgreSQL harness lacked Redis and ended at old migration0017
  after rollback drills. Added isolated Redis, current-schema convergence and API
  runtime credentials; outbox inspection uses a separate read-only fixture observer.
- E05: incorrect psycopg import corrected to existing psycopg2 dependency. Expiry
  fixture initially used negative TTL, which production correctly clamps; backdated
  issuance now explicitly verifies the token is expired before the assertion.

Latest browser evidence: .artifacts/feature113-public-search-all.log (42 pass).
Latest database evidence: .artifacts/feature113-recovery-settings.log (pass; owned
PostgreSQL/Redis containers removed). Earlier recovery logs retained. This is
real database/API evidence, not browser-to-live-backend or external SMTP evidence.
No assurance floor, security control or approved visual baseline was relaxed.

Added acceptance constraints for next batches: profile/state identity in screenshots;
explicit enabled-module fixtures; no synthetic response counted as stored outcome;
preserve disposal failures and first failure logs; validate existing screenshots
against actual restored-layout flags before reuse. Remaining tasks are not closed.

## Cycle 4 — collection paging and integrated browser evidence

- F113-08 (medium, product): collection pages discarded nextCursor, hiding later
  published entries. Four reproductions failed before repair. Added explicit paging,
  duplicate-row suppression, preserved rows/retry on failure, pending-request guard,
  collection-generation isolation and multi-step cursor-cycle detection. Regression:
  react-app/src/**tests**/collection-pagination.test.jsx.
- First Vitest invocation from the repository root did not load the frontend test
  configuration (no tests executed). Corrected working directory; retained both logs.
- Targeted collection/search validation: 11 passed in
  .artifacts/feature113-collection-fixed.log. Four original failures retained in
  .artifacts/feature113-collection-red-corrected.log.
- Integrated synthetic UI journeys: 60 passed in 1.3 minutes across three engines
  and two widths (.artifacts/feature113-journeys-integrated.log). This includes the
  latest search presentation and collection implementation, but does not yet exercise
  collection pagination in the browser or prove real backend persistence there.
- Inspected Firefox desktop search-paginated capture under
  .artifacts/journeys-run-1792036916090: spaced, underlined result headings, intact
  approved shell and no visible overlap. No screenshot baseline was rewritten.
- All existing canonical profiles leave optional blog/docs/portfolio/events modules
  disabled. Next batch needs an isolated enabled-capability fixture/profile; do not
  count missing-route screens as those modules' acceptance or enable production
  capabilities merely to satisfy tests.

No full release gate, publication or paid deployment in this batch. Remaining
workspace, invitation acceptance, media/operator, enabled modules, input-mode and
reviewed comparison coverage remains open; no zero-defect claim is supported.

## Cycle 5 — enabled profiles, workflow actions and recovery

Bounded native-WSL batch on the existing branch: targeted component/contract tests,
then serial browser sweeps. No provider actions. New live request is conditional on
local/CI acceptance and explicit lease limits; owner confirmation is pending.

- F113-09: search guarded immediate repeated cursors but not multi-page cycles.
  New regression failed; retained cursor history now rejects both. All 23 focused
  pagination/inventory tests passed (feature113-pagination-targeted.log).
- F113-10: compatibility catalog omitted implemented optional module packs, making
  enabled-profile acceptance impossible. Registered exact existing versions and
  dependencies, added an explicit .example synthetic profile with deny-indexing,
  no analytics and destroy policy. Deployed Base2 capabilities remain unchanged.
  Profile contract tests pass; generated service profiles are current.
- F113-E06: Volcano selection was intentionally profile-ID scoped. The separate
  journey-reference profile now explicitly shares the existing approved shell,
  without changing selection for other profiles. Initial module browser run is
  diagnostic only: stdin interrupt did not stop its child process, so source edits
  overlapped that invalid run. Verified exact child PID, interrupted it, verified
  exit and performed a clean rebuild/run; no interrupted evidence is accepted.
  Clean enabled-module run: 24 pass (feature113-enabled-modules-clean.log).
- F113-11: Events allowed multiple pending submissions and repeated successful
  booking clicks. Two reproductions failed; per-event in-flight/confirmed guards,
  explicit confirmed-response validation and retry-on-failure now pass. Existing
  GlassButton preserves the component vocabulary. Backend replay protection remains
  separate and is not replaced by client guards.
- F113-12: disposable cleanup ignored failures. Cleanup now attempts all owned
  resources, bounds each attempt, fails an otherwise successful run and reports
  cleanup failure while preserving an original exception. Three mocked failure
  tests pass; updated real-container acceptance remains pending.
- F113-13: accepted viewer invitation navigated to administrator-only UI with no
  confirmation. Browser reproductions failed; show explicit acceptance and a login
  link to refresh access rather than inventing client permissions. Nine identity
  component tests pass; browser rerun pending.
- F113-E07: denied workspace fixture expected an alert, but PermissionRoute redirects
  to account settings. Corrected assertion verifies that redirect and zero workspace
  API requests, rather than counting unrelated settings-service alerts as permission
  evidence. Combined collection paging/workspace browser run: 18 pass across three
  engines/two widths (feature113-workspace-pagination.log). Workspace persistence
  in this run is a stateful UI fixture, not live database evidence.

Next tasks: current-source integrated browser run, screenshot inspection, real
database cleanup validation, supported import/export/media/operations workflows,
preference/input states, coverage review and full gate. No release claim yet.

## Cycle 6 — current workflow evidence and release prerequisites

The owner has now approved the bounded live trial recorded in plan.md. It remains
conditional on local checks and CI, with zero provider actions so far.

- Current integrated journeys: 102 pass across Chromium, Firefox and WebKit,
  including workspace transfer, invitation confirmation, media deletion blocked
  by failed consequence preview, operations stale-data recovery, light/large-text
  keyboard interaction and localized RTL content. Evidence:
  `.artifacts/feature113-journeys-expanded.log`.
- Enabled capability profile: 24 pass on current booking implementation,
  `.artifacts/feature113-enabled-modules-current.log`.
- Real disposable database acceptance and cleanup pass; no owned test containers
  remain. Evidence: `.artifacts/feature113-database-current.log`. External email
  delivery remains intercepted, not tested against a provider.
- Frontend coverage run: 357 tests pass in 82 files. Changed tracked executable
  frontend lines were 84/85 covered; the missed events list failure now has a
  regression. Latest focused booking run passes all four tests, including list
  failure and rejection of an unconfirmed booking response. A fresh full coverage
  gate is still required; the diagnostic count is not a release receipt.
- Two additive screenshot references (mobile contact confirmation and desktop
  search pagination) are byte-identical to inspected captures. The normal
  comparison run passes four cases. No original Volcano reference was changed.
- Current media suite passes 24 applicable checks, with 12 explicitly excluded
  matrix cases: `.artifacts/feature113-media-current.log`. Passing comparison
  tests does not by itself renew the source-bound review manifest.
- Known release prerequisite: shared AppShell/profile changes invalidate old
  media/operations review bindings. Obtain fresh actual-source evidence before
  release; never alter a pass receipt simply to clear the gate (T026).

The coverage inventory still contains earlier pending descriptions and must be
reconciled against actual tests (T027). No full gate, CI or live acceptance is
claimed complete. Capture-only states remain distinct from reviewed comparisons.

Current release-preparation follow-up:

- Operations matrix passes 22 applicable tests (20 explicit matrix exclusions),
  `.artifacts/feature113-operations-current.log`. The supported
  `operations_visual_evidence.py --write` verified its actual runner receipt and
  regenerated bindings for 35 screenshots; no operation baseline changed.
- Frontend lint exits successfully with zero errors and 24 warnings, retained in
  `.artifacts/feature113-lint-current.log`; warnings are not reported as absent.
- `git diff --check` passes. Media review renewal, coverage reconciliation,
  complete gate, hosted CI and bounded live acceptance remain outstanding.
