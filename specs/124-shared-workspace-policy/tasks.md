# Feature 124 task ledger

Status: implementation and acceptance are in progress. Real PostgreSQL, native-browser
and both isolated live-service shell runs have passed at the source checkpoints below.
Whole-database recovery, representative profiles and the full release gate remain open.
Historical pending statements below describe their dated checkpoints, not current results.
Scope approved by user on 2026-10-31 after the four-capability recommendation. Preserve
unrelated dirty Feature 122 files and draft PR 89. Production work follows independent
review of this contract. Do not resume/delegate stopped Expat repair.

## A. Analysis and reproductions (before writers)

- [x] T01 Review spec/plan against constitution and source; inventory every publication,
      public-read/search/export/asset and notification consumer, identity realm and migration
      owner, human authorship provenance and supported local artifact transport. Record exact interfaces, lock order, capability dependencies and evidence paths.
- [ ] T02 Add failing notification tests: two-tab lost update, first-insert race, mandatory
      row omission, returned committed snapshot, timeout/reload, tenant/user isolation (AC1).
- [ ] T03 Add failing review/visibility journeys: direct/scheduled bypass, self approval,
      stale semantic revision (including restore/import/relationship/media mutation),
      public excerpt/body/metadata/flags and asset-version replacement, native Django writes,
      state-only approval carry-forward, permission revocation, policy race, existing content transition, stale
      public projection/export/grant, disabled module and missing policy (AC2/3/5).
- [ ] T04 Add failing consumer tests: transactional enqueue, preference suppression,
      immediate/digest, duplicate/restart, changed recipient access, stale review, local-only
      adapter boundary and failure observability (AC4/6).

## B. Canonical Django foundation (first implementation stage)

- [x] T05 Define common canonical scope/policy/set/approval/intent primitives, closed
      validation and constraints; adapt existing users/sitecontent runtime models without
      conflating Django operator identities with API public identities (AC1-6).
- [ ] T06 Implement additive migrations/backfill and runtime schema mirrors, with genuine
      PostgreSQL migration/restore and restricted request/worker RLS tests. Prove defaults,
      existing-row preservation, mixed-version safety and rollback boundary (AC5/8).
- [ ] T07 Implement canonical CAS and effective-policy/approval decisions with lock-order,
      concurrency and author/reviewer tests; approve Django contracts before API stage.

## C. FastAPI, repositories and workers (second stage)

- [ ] T08 Mirror notification-set read/write contracts, mandatory-row preservation,
      expected-version errors, atomic audit and same-transaction response; document old
      writer rejection and compatibility. Pass focused + real PostgreSQL tests (AC1/6).
- [ ] T09 Implement authorized shared-policy GET/PUT and discovery metadata; exercise all
      roles, tenant tampering, unknown fields, CSRF, disabled dependencies and first save.
- [ ] T10 Implement exact-revision independent approval and shared enforcement in content
      edits, transitions and scheduler. Existing published content remains until edited;
      scheduled unauthorized records block visibly. Prove concurrency/revocation (AC2).
- [ ] T11 Enforce visibility at every inventoried read/search/export/asset boundary;
      reauthorize jobs/downloads and stale grants. No control activated with a known leak
      or asynchronous-only privacy enforcement (AC3).
- [ ] T12 Implement transactional review intent and bounded local-only consumer, UTC daily
      digest and idempotent sink. Recheck live permissions/preferences/state; expose safe
      suppressed/failed/pending outcomes, test outage/restart/replay (AC4/6).
- [ ] T13 Independent backend security/interface review; resolve findings and freeze
      mirrored response shapes before React integration. Record issue ledger and coverage.

## D. React and complete journeys (third stage)

- [ ] T14 Extend service/parser/registry with typed versions, scoped policy controls,
      accessible deep links and existing Save/Cancel/conflict/uncertainty conventions.
- [ ] T15 Integrate review actions/status and local delivery status without claiming
      unwired channels/providers. Test dirty drafts, account changes, navigation, duplicate
      clicks, interrupted requests and keyboard focus (AC1/2/4/7).
- [ ] T16 Run real-service multi-user journeys for AC1-6; verify DB persistence after
      reload/restart and negative direct calls, not only mocks. Test representative existing
      publishing/docs/portfolio profiles; no claim of all-family maturity.
- [ ] T17 Inspect responsive/light/dark/forced-color/accessibility captures against
      approved Obsidian/Volcano references; no baseline laundering (AC7).

## E. Acceptance and delivery

- [ ] T18 Review >=90% changed-line coverage and unchanged floors, critical branch
      evidence, migrations/restore and regressions across settings/content/media consumers.
- [ ] T19 Run supported complete release gate on frozen source after focused repairs;
      list passed/failed/blocked/not-run separately. Baseline image security remains an
      independent blocker until legitimately resolved; no prohibited repair attempt.
- [ ] T20 Produce exact-source release summary and update truthful scope documentation,
      requirement/test map and backlog states. Request applicable publication authority;
      no merge/deploy or push as part of these tasks without that authority.

## Implementation checkpoint (2026-10-31)

- Contract and canonical-model source reviews completed before API/React work.
  Canonical focused tests passed (48), including fresh-install conservative defaults,
  legacy preservation and explicit identity-realm separation. Actual PostgreSQL
  migration, RLS and concurrency remain unverified.
- Notification API local full-suite checkpoint passed 1,441 tests before the later
  policy integration. This is historical local evidence, not the final combined gate.
- Notification/navigation React checkpoint passed 586 tests plus 27 tooling tests,
  lint, types and build. A modal stacking/focus defect was reproduced and repaired;
  actual native browser histories, inert behavior and visual captures remain unrun.
- Policy/review UI and backend integration are implemented and undergoing expanded
  local regression checks. New real PostgreSQL proof cases are wired for the
  disposable integration runner; collection is not execution.
- The database-only review notification consumer passed 50 focused tests. Its
  PostgreSQL delivery/digest proof cases remain unrun. No live email is activated.
- Retention/privacy compatibility, native mutation guards and media transaction
  integration are necessary supporting work for the shared policy boundary. Their
  source reviews and unit tests do not replace restricted-role database evidence.

## Supporting obligations discovered during implementation

- [ ] T21 Enforce native/queryset/raw semantic invalidation, immutable schema and
      independent review-cycle binding. Prove advisory-before-row locking in supported
      Django/API/worker paths; test revocation, contention and transaction rollback.
- [ ] T22 Preserve supported retention and claim-fenced data-rights operations for
      review records through narrow audited helpers, without granting ordinary runtime
      access to erase approval history or exposing personal preferences to organizations.
- [ ] T23 Keep media inspection outside policy critical sections, fence immutable
      results and expired claims, and use a committed exact purge plan before deleting
      local artifacts. Prove partial-failure recovery and prevention of restore/rebinding.
      Remote transport and cross-version orphan limitations must stay explicit.

Draft publication and tested follow-up commits were authorized separately on
2026-10-31. No new feature commit,
merge, deployment, provider activation or complete-gate pass is claimed here.

- [ ] T24 Preserve optional-policy draft/in_review/publication compatibility, including
      a sole owner. Required review remains fail-closed for unknown authorship or no
      independent reviewer. Verify both delivery-policy transition directions, truthful
      zero-recipient status and no automatic audience backfill.

## First draft CI repair batch

At `81226ff5f51a819a6860b0ed811973a0041647a9`, real PostgreSQL applied migrations
0036–0040 successfully. This does not establish runtime/RLS correctness: 73 new
integration cases stopped in fixture setup before their assertions because the
production interactive record INSERT omitted required `schedule_timezone`.
The import-create path had the same omission; both now supply the canonical empty
unscheduled value. Community creation already supplied it. Two failing regressions
were retained before the correction; schema constraints were not weakened.

The isolated identity/settings job passed three assertions but two fixture teardowns
attempted to hard-delete synthetic users. Audit foreign-key nullification correctly
failed against immutable history. Fixture retirement now deactivates only the exact
synthetic users and leaves audit rows for disposable-database teardown, matching the
production pseudonymization/deactivation boundary. Audit triggers and grants remain
unchanged. Focused repair checks pass; a fresh PostgreSQL run is still required.

The environment-sync workflow did not run because its old PR-base filter excluded
stacked feature branches. Its pull-request trigger now covers all bases, with a
regression retaining the original fail-on-drift rule. This is expanded verification,
not a passing result for the previously skipped workflow.

Frontend CI at the same head passed 660 tests and failed one shared-policy reload
unit test before any build/browser stage. The retained result alone does not prove
a production reload defect. A controlled category-transition reproduction showed
that the old test could select an enabled but detached outgoing card button, issue
no second read, and fail its unchanged reconciliation assertion. The test now waits
for the unique destination control, scopes the enabled button to that live form and
asserts the second GET. A pending-read regression also verifies no repeated reload.
There is no production change, timeout increase or weakened success assertion.
Native browser evidence remains unrun for that setup-blocked head.

The inherited media-image release blocker remains separate from these repairs;
no stopped runtime repair is resumed by this feature.

## Second draft CI repair batch

At `767f302804838b8a3435dd39448b0ecee6b527e3`, configuration sync, local unit jobs
and isolated settings PostgreSQL acceptance pass. The main integration fixture now
reaches review submission, exposing a restrictive-only RLS composition on
`sitecontent_contentrevision`. Additive migration 0041 admits only the two existing
workspace roles through an explicit same-tenant parent-record predicate, preserving
parent RLS, forced RLS, restrictive data-rights fencing and grants. Readiness and
negative tests cover the upgrade; repaired PostgreSQL runtime remains pending.

Browser execution now supplies actual evidence. The responsive settings release
matrix and the new policy/review scenarios pass in both layouts. Some navigation
fixtures used nonexistent/hidden controls or obsolete delivery copy; their setup and
assertions now name the real controls and truthful local-adapter behavior.

A separate real defect was reproduced: Discard followed by rapid Back during a
suspended destination can retain the Settings instance and its unsaved draft.
Discard now resets ordinary loaded snapshots before proceeding, once only, without
canceling sent requests or clearing conflict/uncertainty fences. Focused suspended-
destination, pending-success and error-recovery tests pass; the original rapid native
Back assertion is retained. Native verification of the repair remains required.

The dedicated 24-test workspace release matrix had only been collected previously.
It is now a required independent CI suite with its own retained artifact and a
fail-closed aggregate outcome. This does not turn its synthetic API fixtures into
real-service proof. The remaining browser/API/database evidence gap is being addressed
through the existing disposable E2E runner, not a deployed preview or TLS bypass.

## Disposable live-acceptance batch: source ready, execution pending

Checkpoint 2026-10-31: remote
`e6deb5864ea9f38bad25d6261b756d35cefe1e81` has 8/10 workflows passing and all
433 synthetic browser tests green. This is evidence for that source and synthetic
suite only. The backend repair and new live-service acceptance still await their
next published CI run. T16/T19 are not complete, and no deployment is authorized.

Before publication, the combined local contract batch passed 135 tests; the backend
full suite passed 1,649 tests, with mypy covering 272 files and Ruff passing. These
checks do not replace the pending real-service/PostgreSQL/browser CI evidence.

- [x] T25 Extend the existing disposable E2E stack with a shared base2-obsidian
      profile, restricted content worker/beat, encrypted local artifacts and
      one-shot synthetic fixtures; independently source-review the interfaces.
      Static/guard tests and Playwright collection pass, not runtime acceptance.
- [x] T26 Execute both isolated Bash and PowerShell Ubuntu CI jobs on the exact
      next published source. Retain successful JSON/Compose/cleanup/source artifacts
      and first failures. Establish actual login/two-tab UI CAS and authenticated
      API-context approval/visibility/export/asset behavior against PostgreSQL.
      Do not describe API requests as UI clicks or collection as execution.
- [x] T27 Verify actual beat delivery and due-publication denial separately from
      bounded controlled-UTC consumer proofs. Verify immediate/disabled/digest,
      midnight-minus-one-millisecond non-delivery, exact-once restart/replay and
      revoked recipients. Verify the same viewer's own grants before/after fixed
      fixture suspension while still unexpired; label the mutation fixture-driven,
      not a user-facing membership action. Record seeded asset readiness and
      loopback HTTP as non-scanner/non-TLS evidence.
- [ ] T28 Complete remaining representative publishing/docs/portfolio profile,
      migration/restore/race and exact-source release obligations. The new required
      descriptor makes the manifest 133 checks; registration does not run the full
      gate, which is not currently invoked by CI. Preserve independent release
      blockers and do not resume stopped Feature 122 work.

The bounded addition preserves real login/cookies/CSRF and restricted roles. Only
one-shot fixture setup has owner credentials; no arbitrary browser-selected tenant,
role-grant bypass or HTTP fixture-control endpoint is introduced. Other authenticated
journeys use the existing API after login, not mocked responses. The local sink is
not a mail provider, the pre-ready PNG is not scanning proof, and no live preview or
TLS bypass is part of this batch.

## First real-service browser execution and bounded repair

At PR head `0e3156f`, the repaired backend real-PostgreSQL jobs passed. Both isolated
Bash and PowerShell E2E stacks became healthy, including the one-shot fixture, and
each ran five tests with four auth passes and one workspace failure. Actions tested
merge checkout `991e82…`; retained artifact metadata binds that checkout to PR head
`0e3156f`. Do not relabel the merge checkout as the feature-head source commit.

The first workspace failure was test selection, not a demonstrated notification
persistence defect: unscoped `getByRole('status')` matched both the route-announcement
output and the saved-notification div. The assertion now selects the exact saved
announcement without changing its required content. An adjacent cleanup failure
was also preserved: `docker compose start celery-content-worker` traversed completed
dependencies and reran the one-shot fixture, which correctly rejected the nonempty
auth database. All service resume paths now use a fixed worker/beat allowlist with
`up -d --no-deps --no-build --no-recreate --pull never`; the seed guard remains
unchanged. Final runner cleanup removed containers, network and volume in both
failed runs. First-failure JSON, traces and Compose logs remain in
`/tmp/base2-ci-0e3156f/{bash,pwsh}/` in the current evidence workspace.

The bounded next run also adds actual shared-policy UI interactions: Keep editing
and category Cancel produce no write; Site and Organization save only their own
field while preserving the other category's draft; two authenticated administrators
produce a real 409, preserve the stale draft and explicitly reload without mutation
replay. Final policy is read/asserted as review-required/public-allowed, not silently
reset by an API setup write. Other content/review/export/asset flows remain
API-context journeys after real login, as documented above.

Independent source review accepted this correction for CI execution. Four focused
source/pure-command guardrails and 15 fixture guards pass, along with Node syntax
and five-test Playwright collection. No local Docker/browser retry was attempted.
Corrected runtime acceptance, later workspace assertions and the full release gate
remain pending; healthy startup and passing auth do not establish those results.

## Public-search identity correction after the next live run

At head `ddcd6f9`, both E2E shells again reported four auth passes and one workspace
failure, now later in the visibility step. Retained evidence binds merge checkout
`73435b0999e76b2be7c576bcabcfadb163538260` to that feature head. Both runs completed
the notification/CSRF step, all new shared-policy UI assertions and real beat delivery
after worker restart. Shared-policy artifacts show versions 1→4 and the four expected
requests including the stale version-3 conflict; beat artifacts show one reviewer
receipt and owner suppression. No fixture replay or recovery error recurred.

The new failure was another test/contract mismatch: `/api/search` returns the
independent SearchDocument UUID, not the ContentRecord UUID. The public detail read
passed 200, and retained search responses eventually contained the correct exact
`urlPath` and title. Comparing their projection ID to the record ID prevented the
positive assertion from passing; importantly, the old negative assertion would
also have passed vacuously if content had leaked. Both predicates are corrected.

The repaired test requires a 200 response and the actual SearchPage/item schema,
complete pagination, exactly one pre-restriction path/title projection and its
captured document ID. One immediate post-restriction search must contain neither
that tuple, that path nor the captured document ID, and must have zero results.
No eventual post-restriction poll or production behavior change is introduced.
The regression uses the production serializer with distinct document/record IDs
and rejects malformed/incomplete pages. An adjacent export/asset/scheduler/digest
producer-field audit found no further response-shape mismatch.

Twenty fixture/source/pure-helper tests pass; all fourteen retained search payloads
from each shell were validated offline against the corrected contract. Independent
source review accepted the repair. Original JSON, traces, logs and extracted
attachments remain under `/tmp/base2-ci-ddcd6f9/{bash,pwsh}/`. The corrected visibility
proof and later export/asset/scheduler/digest assertions still require a fresh CI
run; these offline checks are not runtime acceptance or full-gate completion.

The fixture/source regressions above were initially run only by explicit local
commands: neither existing CI discovery nor the full-gate manifest collected
`e2e/support/test_workspace_fixture.py` or
`e2e/support/test_workspace_journey_source.py`. Both exact paths are now appended
to the existing API-only CI regression step (with pinned Node 20 setup) and the
existing API-Python `frontend-ci-scope-contract` gate descriptor (declaring Node).
No job/check, dependency, coverage floor or existing test is removed. A static
regression verifies both collection paths. This closes the wiring gap in source;
execution of the newly wired checks in CI and the full gate remains pending.

The topology/wiring regression itself is also explicitly collected by both commands;
it is not left as a local-only guard for CI collection.

### Exact-head asset-detail repair after `8d87e75`

The real-service workspace journey reached viewer asset detail after successful
public content/search checks, then received 503 `content_dependency_unavailable`.
Both shells' retained PostgreSQL logs identify `column reference "id" is ambiguous`
in the asset/safe-variant join. This is a production SQL projection defect, not
an invalid fixture, scanner failure, or permission denial. Qualifying the nine
asset-owned projection fields preserves column order, the safe-variant join,
all ACL predicates and download-grant binding. Adjacent upload-replay and
asset-content joins were inspected and already qualify their projection fields.

The focused projection regression first failed and then passed; 21 repository
unit tests pass. Two new restricted-role PostgreSQL cases distinguish parent
metadata from safe-variant digest/type in the signed grant and retain cross-tenant
and private-nonowner denial assertions. They are collected, not yet executed on
the repaired head. Independent source review accepted the three-file backend
repair. Original failure evidence remains under `/tmp/base2-ci-8d87e75/`;
red/green evidence is `/tmp/124-asset-projection-{red,green}.log`.

A separate Celery operations task error in the same Compose evidence comes from
an absent read-only operations-probes JSON mount. The E2E fixture owner is
restoring the existing development-topology mount and its topology assertion;
this is unrelated to the asset GET failure and does not change images, scanner
code, grants or runtime permissions. Its real-service correction also awaits CI.

Asset download, exports, restrictive visibility, scheduler revocation and digest
assertions after the failed GET were not reached on `8d87e75`; no acceptance is
inferred for those journey stages from prior PostgreSQL or unit results.

Final frozen backend validation: Ruff clean, mypy 272 files clean, and full API
unit suite 1,649 passed, 8 skipped, 104 integration/performance cases deselected
in 32.12 seconds. Logs and coverage are `/tmp/124-asset-final-*`. These results
validate local source behavior; the two added PostgreSQL cases and continued
real-service journey require execution after the approved follow-up publication.

The subsequent head `bb9026d` run (Actions merge checkout
`425bf71d3f9f0caf0c6663fe98064a626dc62ca9`) passed the first four workspace
steps in both shells. Retained `public-search-visibility` attachments show the
exact public projection before restriction and a complete zero-item response
immediately afterwards. Member reads, export/asset grants and the same actor's
unexpired grants before/after fixed fixture suspension passed (approximately
1.2–1.5 seconds elapsed against a 60-second TTL). The canonical catalog mount
also eliminated its missing-file exception; operations collection completed four
times per shell. A separate operations readiness permission error concerning
`django_migrations` is not an asset or route failure and is not resolved here.

The next failure was the acceptance helper's `GET /api/admin/overview` returning
404: the real identity router and UI client require `/api/identity/admin/overview`.
Its PATCH role route had the same missing `/identity` prefix. Only these two
helper paths are corrected; actual password reauthentication, role payload,
`expected_updated_at` CAS and worker-stop/revoke/denial/resume ordering remain
unchanged. A regression executes the helper with fake HTTP, checks its emitted
methods/paths against the production router and validates its payload against
the production request model. All 28 topology/fixture/source tests pass, and
Playwright collection lists five tests; neither is runtime acceptance.

Original failure logs and attachments remain under
`/tmp/base2-ci-bb9026d/{bash,pwsh}/`. Semantic-edit invalidation, stale approval 409
and publication 422 were reached before the failing role helper. Actual reviewer
role revocation, the resulting due-scheduler denial, and the final controlled-clock
digest/replay/recipient-revocation step still require corrected CI execution.
Representative-profile and full-gate execution obligations remain open.

### Restricted operations migration observation after `bb9026d`

With the operations catalog mounted, collection completed four times per shell
with 16 samples, but its `migrations.state` adapter attempted API schema-ledger
SQL through the intentionally restricted runtime-worker connection. PostgreSQL
denied `django_migrations` reads. The adapter reported `migrations.unknown` and
`unavailable`; successful collection did not mean this probe, or all probes, was
healthy. The API process already has the authorized schema-ledger capability and
exposes its bounded readiness result at the existing `/api/health` endpoint.

The runtime worker now observes that endpoint without new grants, credentials,
SQL fallbacks or routes. The schema-specific HTTP mode retains the existing
local hostname allowlist and validates the fixed path, explicit port, absent
userinfo/query/fragment/base path, and bounded timeout. It disables ambient
proxies, rejects redirects before another request, reads at most 4,097 bytes and
rejects bodies above 4 KiB. Only HTTP 200 and exact API/service/schema/overall
boolean readiness fields produce `migrations.ready`; missing, malformed,
oversized, non-200, unrelated unhealthy, or transport-failed observations remain
`migrations.unknown`/`unavailable`. Generic HTTP probe behavior is not redefined.

The fixture owner separately supplies the existing approved `nginx` network alias
for the E2E frontend and `http://nginx:8080` to the runtime worker. This points the
observer to the actual isolated proxy without widening its hostname allowlist.
The topology and runtime observation still require next-head CI execution.

Initial and security-review regressions were reproduced before their repairs;
56 focused operations tests pass. Independent source review accepted the proxy,
redirect, authority, size and failure checks. Final frozen validation: 1,689 API
unit tests passed, 8 skipped, 104 integration/performance cases deselected;
Ruff clean, mypy 273 files clean, and all 35 changed executable production lines
covered. Evidence: `/tmp/124-probe-reviewed-final-*` and original
`/tmp/base2-ci-bb9026d/`. Unit coverage is not live network/probe acceptance or a
claim that every operations service is healthy.

The pending acceptance now also polls the real owner-authenticated operations
overview for the specific latest `migrations.state` sample in `preview`, before
beat is stopped for the controlled-clock digest proof. It requires schema version
1 and the fixed site, exactly one enabled matching service, `healthy` /
`migrations.ready`, valid observation/expiry timestamps, observation age at most
the canonical 300-second freshness window (at most five seconds of future clock
skew), and unexpired evidence. The bounded 120-second poll uses the real clock and
attaches the observed sample; no privileged CLI/schema read or requirement that
unrelated probes be healthy is added. Pure regression cases reject stale,
expired, malformed, wrong-site/environment and duplicate observations and retain
an unrelated degraded probe. Thirty local topology/support tests pass; actual
fresh ready observation remains pending CI, not inferred from collection counts.

## Acceptance reconciliation and bounded recovery correction

At `4532892a5172adebcdeafb169708e78989d90370`, all ten workflows are terminal:
nine pass and only the inherited media-security workflow fails. Both isolated Bash
and PowerShell runs pass all five tests and all six ordered workspace substeps.
This closes T26/T27 for that source: real settings UI conflicts, independent review,
synchronous public search restriction, authorized asset/export access, same-actor
unexpired grant revocation, scheduler role revocation and controlled-UTC digest/replay
are executed. The seeded asset and fixed membership-suspension action remain explicitly
fixture-driven; no scanner, TLS or live-email proof is inferred. The next source adds
a persisted operations sample assertion and requires fresh CI for that addition.

The same checkpoint passes the real restricted-role PostgreSQL suite, including
policy CAS/lock waits, membership revocation, notification retries/digest boundaries,
media claims and two asset/variant projection regressions. Those are existing race
evidence, not missing solely because broad aggregate tasks remain unchecked.
Frontend verification passes 668 UI tests, 27 tooling tests and 433 browser executions.
Native Storybook builds pass; external Chromatic publication is skipped without its
token. The unchanged 71 inherited media findings remain a release blocker.

A distinct T06/T18/T28 gap remains: record-level restore and fresh migrations do not
prove whole-database backup/restore of policy, preference versions, review history
and durable notification effects. Source analysis also finds that both production
dump and restore omit ownership/ACLs. A restored database can therefore lose runtime
grants and regain default PUBLIC EXECUTE on SECURITY DEFINER functions. Do not call
restored runtime functions or repair grants in a fixture to manufacture acceptance.

- [ ] T29 Implement a versioned authenticated recovery security manifest, preserving
      source ownership/ACL/RLS and checking exact existing roles, effective memberships
      and trusted definer ownership. Reject legacy or mismatched evidence before
      restore; verify restored catalogs before runtime execution or success receipts.
      No real target, credential, new role or deployment is authorized by this task.
- [ ] T30 Exercise the production encrypted backup/isolated restore path with two
      fresh owned disposable databases and actual matching PostgreSQL tools. Verify
      security parity, restored Feature124 state and restricted-runtime denials/replay
      effects; prove source unchanged and tear down only exact owned test databases.
- [ ] T31 Resolve the supported workspace/public-pack type-key compatibility gap
      before claiming blog/docs/portfolio representative journeys. Use an explicit
      generated-profile allowlist and retain disabled-profile negative checks.

These bounded obligations complete Feature124 acceptance before broader family
engines advance. They do not reopen stopped media-runtime repair or authorize
merging, provider activation, real backups or deployment.

## Native sign-out regression after a4c60ab

Both isolated live-service shell runs now pass all seven workspace steps, including
a fresh persisted `migrations.ready` sample from the owner operations API. This is
not an all-probes health claim. The same candidate has a retained shared-layout
390px failure: sign-out clears account actions but ends on public Home instead of
Sign in. Its earlier appearance screenshots passed; later sign-out isolation
assertions did not execute. Final Storybook/Chromatic stages were skipped after
that frontend failure, unlike earlier token-only publication skips.

- [x] T32 Resolve the real competing logout destinations with a controlled delayed
      completion reproduction, canonical Sign in target, retained failure guidance
      and explicit native response/navigation/account-isolation evidence. Preserve
      the original failure; do not relax assertions or update image baselines.

Shared-layout browser failures now retain a trace in the existing evidence artifact.
Automatic retries remain zero; this improves diagnosis without weakening any test.

### Recovery and sign-out candidate source checkpoint

Independent reviews accepted the closed recovery envelope, disposable restore
harness and controlled sign-out repair before publication. The combined local
repository-contract run passes 251 tests. API validation passes 1,689 unit tests,
mypy and Ruff; the new actual restore case is collected but has not run locally.
Frontend validation passes 672 unit tests and 27 tooling tests, lint, types and
build. Changed executable lines in the recovery/security implementation and the
three sign-out statements are covered; existing coverage floors are unchanged.
These results do not substitute for native restore or browser execution.

A local ancestry check initially failed because this checkout lacked history.
Fetching its missing history established the unchanged planning baseline as an
ancestor, and the exact original check passed. No baseline policy was altered.
The native full-gate checkout must likewise include sufficient history.

### Native checkpoint at c1cab86

All ten workflows are terminal: frontend passes all seven browser suites including
both native sign-out widths and the required aggregate; final Storybook build also
passes. Both real-service shells pass all seven ordered workspace steps. Hosted
Chromatic publication is again skipped for its absent token.

The new dedicated restoration job reaches source migration, policy/preference/history
seeding and revocation assertions, then fails before target restore during its first
libpq catalog capture. Python's service-file writer emitted spaces around `=`,
which its own connection parser accepts but libpq rejects before SQL. This code-level
diagnosis awaits corrected native confirmation. The bounded fixture correction writes canonical `key=value`; safe fixed diagnostic categories
retain client failure status without exposing service contents, SQL or credentials.
The security envelope is unchanged and repaired native restore remains pending.

### Type compatibility and repository quality checkpoint

Canonical/API/React validation now accepts the exact existing public-pack keys
`blog-post`, `doc-page`, and `portfolio-item` without renaming. Field/preset keys
remain underscore-only; a reproduced native final-newline validation inconsistency
is corrected with strict anchors. Migration 0042 changes validator state only and
rewrites no data. Three real restricted-role PostgreSQL cases are collected and
explicitly wired; their native execution and generated-profile journeys remain
pending. API units pass 1,732 tests, frontend 692 plus 27 tooling tests, and changed
executable lines are covered (API 12/12, common 3/3, sitecontent 2/2, SchemaBuilder 3/3).

Expanded full-tree Django lint found 34 existing formatting/import findings. A
bounded cleanup preserves normalized AST and setup/import ordering; the live race
script keeps its direct CLI behavior behind a tested `main()` guard. Full Django
Ruff is now clean and enforced in both fixed backend CI matrix entries; no lint
rules or coverage floors were relaxed. The post-cleanup supported Django run passes
222 tests, with the separate readiness file also verified. The live race script is
not executed locally; its actual PostgreSQL proof remains part of native acceptance.

- [ ] T34 Repair the confirmed supported-pack search-link mismatch and existing
      stale projections, then follow returned links in representative live journeys.
      Current worker URLs use type names while pack pages use `/blog`, `/docs` and
      `/portfolio`. Preserve document IDs, tenant/visibility checks and intentional
      custom paths; do not call generic search inclusion usable page navigation.

### Native prerequisite fixes and representative candidate

At `0fa9f1b24365fb96878726b3f21b7b562ecee3d7`, frontend and both real-service shell
runs pass. Backend reveals two test prerequisites: Django's separate development
environment did not install Ruff, and the three direct-route PostgreSQL type cases
lacked a cursor signing key. Declare the existing pinned Ruff version in Django's
dev requirements; install a scoped synthetic key and prove codec/scope behavior
before requesting the database fixture. Production cursor requirements are unchanged.
The dedicated restore was skipped after earlier integration failures, not verified.

Independent restore diagnosis now runs after an actually executed core integration
step even if that step fails, but never after skipped setup or cancellation. Both
steps remain fail-on-error, and successful restoration evidence is retained only
after its own verified success. This gathers independent failures without making a
failed backend job pass or weakening disposable-role/client/database prerequisites.

The supported-pack worker now uses the real `/blog`, `/docs` and `/portfolio` paths.
Exact legacy generated paths at equal source timestamps are corrected by a URL-only
conditional update; newer/custom/tombstoned/stale projections and content history
remain protected. Eighteen real PostgreSQL cases are collected. Scoped discovery
predicate tests execute real restricted-worker SQL with a fixture-only tenant
conjunction; they do not claim global queue fairness or local database execution.
Full API validation passes 1,743 unit tests, Ruff and mypy; changed worker executable
lines are covered 6/6. Native PostgreSQL proof remains pending.

The new representative journey uses conservative fresh defaults, then actual UI
optional→required→public policy transitions before any content exists. It creates,
reviews and publishes all three real family types, follows returned public search
links, and checks immediate restriction and retained member access. The explicit
matrix is base2 Bash/PowerShell plus journey-reference Bash; each selects four auth
tests and exactly its one workspace journey, without skip-based success. The
journey-reference frontend build passes locally. Runtime and image review remain
pending, and no generic custom-type page renderer is claimed.

The complete-gate manifest now has 134 required checks: 132 prior descriptors are
unchanged, the base2 check is explicitly profile-bound, and one required representative
check is added. Both use a closed native-shell/profile wrapper with profile-separated
JSON/traces/screenshots so sequential runs cannot overwrite each other's evidence.
The wrapper does not establish real cancellation cleanup; current reporters do not
produce the configured HTML report. Registration and source tests do not run or pass
the full release gate.

### New concrete findings at 5c6a8d5

All three family records are independently reviewed/published and canonical search
paths are returned; the first blog link reaches the correct route and title. Its
body assertion fails because public excerpt/body are empty, although private values
persist. Later family rendering/restriction is unreached. Do not weaken that assertion
or auto-expose private JSON; the missing explicit authoring capability is real.

- [ ] T35 Implement explicit bounded public excerpt/body authoring, atomic CAS/history
      and canonical/API/UI validation, with legacy restore coverage and private-value
      non-disclosure. Verify normal UI use, review invalidation/re-review, restoration
      and public rendering in the representative native journey.

The same candidate performs actual encrypted backup and pg_restore, then correctly
fails strict security-catalog parity before restored runtime use or success receipt.
The exact differing field is still unknown. Add only bounded sanitized failure
diagnostics and retain strict comparison; no guessed normalization or privilege repair.
An API-only source guard also imported an unavailable Playwright package; evaluate
its actual config logic with only the decorator supplied in the source-test harness,
while real Playwright validation remains native collection/execution evidence.


### Public-authoring and restore diagnostics checkpoint

Public-authoring canonical/API source has independent review acceptance, with 216
focused API checks and 73 canonical checks passing. Unmanaged/static history retains
its prior values-only behavior and unrestricted public text; managed history remains
strict. Seven new PostgreSQL cases are collected, not yet executed. UI implementation
and focused checks exist, but final stale-response review, broad frontend checks and
native representative authoring/rendering proof remain pending. T35 is not complete.

At e387465 the restore executes pg_restore but fails exact parity on 78 catalog
objects and one policy. The first twelve emitted differences are explicit owner-only
ACL arrays versus NULL. PostgreSQL documents default-ACL representation differences,
but the omitted object/policy differences are not yet established. Diagnostics-only
commit a0ef808 expands closed hashed evidence to 96 entries with per-category
reservation and bounded size, without normalizing catalogs or relaxing acceptance.
The complete 134-check release gate remains unrun. No merge or deployment occurred.


Final local public-authoring API validation passes 1,787 tests with eight skips,
86.16% suite coverage, Ruff and mypy; changed executable source coverage is 82/82.
The native-CI-shaped Django run initially found a sibling API import unavailable
from django/; a test-only resolved-file import fixes that parity test without path
pollution. The rerun passes all 256 Django tests with 76.60% coverage; migration
check reports no changes. Existing pinned Ruff passes Django; the local Django
venv itself lacks Ruff despite the declared development requirement.

Independent UI source review accepted atomic copy/value save, permission/legacy
restore behavior and dirty/late-response protection after repairing stale
post-mutation detail acceptance. Full frontend checks remain pending. Root review
of the representative journey confirms explicit public creation/editing, persisted
copy checks, distinct private-value absence and unchanged three-family restrictions.
The native journey and seven new PostgreSQL cases still await publication/execution.
Recovery/journey contracts pass 141 checks locally.

Expanded a0ef808 restore evidence has no omissions: 71 relation ACL differences,
two function ACL differences, five constraint-definition differences and one policy
USING-expression difference. Their meaning is under investigation; no normalization
or restored-runtime success has been accepted.


Final frozen frontend suite passes 738 tests across 109 files plus 27 tooling
tests. Lines85.70%, statements83.78%, branches77.42%, functions82.56%; existing
floors unchanged. Lint has zero errors (30 existing declaration warnings), typecheck
and build pass. This is unit/static evidence, not native browser acceptance.

- [ ] T36 Repair restore evidence representation with security manifest v2: precise
      PostgreSQL default ACL expansion and token-aware proven literal-array cast
      equivalence. Preserve strict semantic authority, reject incompatible v1 restore,
      test exact native hashes and malicious/non-equivalent differences, independently
      review, then establish actual restored runtime and success receipt. Not complete.

The final five test-only gap closures pass: frontend743/743 plus27tooling; all156
added executable UI lines covered. Final coverage lines85.84%, statements83.92%,
branches77.59%, functions82.77%. No production changes followed reviewed UI source.

Restore-v2 source passed independent adversarial review after closing a Unicode
function-identifier lexer boundary defect and unsupported opaque-postfix handling.
All 179 direct recovery/backup contracts pass, with 297/297 module statements covered;
signed v1 evidence is explicitly rejected. Actual native restore/runtime proof is
still pending, so T36 remains open.

Opt-in exact-head hosted complete-gate workflow is implemented and source-reviewed,
with 81 focused CI/policy/runner checks. It is label-event-only, same-repository,
read-only, source-bound and has no publication-triggered execution. Separate existing
pinned environments avoid the combined pytest-cov requirement conflict; setup and
runtime dependency closure remain unverified on a fresh hosted runner. Actual
repetition evidence and the unchanged 134-check gate run sequentially; private
allowlisted evidence is validated and archived with modes preserved. No label has
been applied and the full gate has not run. Restoration and media-security remain
separate release obligations.

Combined recovery/gate contracts pass238 checks locally. The representative journey
now captures actual filled public-copy create/edit forms at1440 and390 widths,
checks overflow/control reachability and restores viewport without reload;49 source
contracts and five-case collection pass. Screenshots and native writes remain pending.

### Native findings at 95471e4

The native restore now passes actual pg_restore, strict v2 catalog parity, table
reconciliation and schema-version checks, then fails because a valid empty-object
archive does not materialize its objects directory. Keep strict path/reference checks;
create the owned empty object root after archive validation rather than relax checks.
Restored-role behavior and the final success receipt remain unreached.

Five new public-authoring PG cases fail on fixture setup: editor used as publisher
instead of owner/admin, incorrect expected exception for a correctly denied viewer,
and missing synthetic cursor signing configuration. Repair only fixture helpers and
assert explicit editor publication denial; preserve production authorization.

Semgrep correctly flags four exec(code, {}) calls in the new workflow archive tests.
Replace with bounded subprocess execution of the actual trusted extracted script;
retain positive/negative archive regressions without suppression or altered rule policy.
Current head's remaining native browser/security runs are still pending; do not cancel.

This native repair batch is independently source-reviewed: empty object root
materialization keeps strict reference/archive checks; PG fixtures retain editor
publication denial and correct scoped cursor signing; archive tests use bounded
subprocesses without ambient credentials or eval suppression. Backup/recovery185
checks and workflow/runner84 checks pass. Full API rerun passes1792 tests with eight
skips and86.25% coverage; eight PG cases collect but actual rerun is pending.
No restore receipt or full-gate pass is claimed, and current native runs are retained.

Native representative UI creation/editing and independent publication of all three
families succeeds. Search's `excerpt` is an existing generated320-codepoint body
snippet, not the record's curated excerpt; correct only that test expectation while
retaining exact curated detail and privacy assertions.56 focused checks pass.
The public detail/link/restriction loop remains unreached on95471e4.

- [ ] T37 Fix actual390px public-authoring cramping with scoped mobile spacing,
      preserve desktop/design, verify practical field width and focused viewport
      visibility, independently review actual pixels and re-run affected acceptance.

All four create/edit screenshots at1440/390 were inspected. Desktop composition is
clear; mobile textareas are about124px wide due cumulative padding. No overflow is
not sufficient acceptance. Fixed-shell overlap in full-page captures needs viewport
confirmation before calling it a persistent obstruction. T37 is not complete.

Native workspace screenshot matrix reports six record-page mismatches. The shared
browser author fixture omitted content-workspace.write, correctly hiding New record
and shifting toolbar geometry; repair that fixture, never weaken production access.
Record response mocks also need the new explicit publicContent pair before selection.
All twelve retained axe reports have zero violations, but this does not establish
visual acceptance. Divider/focus differences are being compared with the previous
passing artifact before classifying a new defect or changing styles. No baselines
have been updated. Mobile padding repair is restricted to active create/edit state;
other workspace states retain established mobile and desktop class values.

Prior passing a0ef808 artifact comparison establishes that bright Records dividers
and WebKit's focused Skip link predate this batch and fit prior snapshot tolerance.
Missing fixture permission is the new record-page geometry cause. Keep this repair
fixture-only with unchanged baselines/focus; separately track the existing divider
mismatch (actual RGB229,231,235 vs approved RGB43,43,43) for a scoped compatibility
correction, not a global stylesheet rewrite. Current shared-layout/approved-Volcano
stages also report failures; their causes await complete retained logs/artifacts and
must not be attributed to workspace fixture drift without evidence.

Final scoped mobile repair is independently source-approved and frozen:752 frontend
unit tests plus27 tooling checks pass, all five added executable callback lines are
covered, and lint/types/build pass. Compact layout activates only for creation or
actual inspector editing, including pristine edit entry; default workspace panels
retain original class values. No CSS/theme/shell/baseline changes. Native240px field
width, focused viewport visibility and pixel acceptance remain pending.

All95471e4 workflows are terminal: frontend743 unit+27 tooling pass, native415/433
pass and18 fail. Remaining review failures in shared-layout/Volcano are stale
record mocks lacking publicContent, causing intentional response validation failure
before receipts/review controls render. Six journey failures omit author write
permission before creation. Audit all three browser record-producing fixtures and
mirror atomic public-copy persistence in mocked writes; retain all original review,
unprivileged, mutation and screenshot assertions. Journey artifact upload path also
needs investigation because failure screenshots were reported but not retained.

Final browser fixture/evidence batch is independently accepted. All three record-
producing browser fixtures now model required permissions and explicit public copy;
POST/PATCH/If-Match/reload assertions and unprivileged no-request checks remain.
Current-run journey/module upload directories replace the ambiguous hidden-root
wildcard, without enabling hidden files or uploading builds/other runs. Combined
final recovery/gate/settings/journey contracts pass314 checks. Current95471e4 CI is
fully terminal before next publication; all repaired native paths still require rerun.

### Native success evidence at5ec50d0

Actual encrypted restoration now passes, including strict v2 catalog parity,
restricted-role behavior and cleanup before the success receipt. Receipt runId
00e0cb96991c4cc2bb2fb0921c78d81d binds mergef6da96640b3d9c3b1694eb668fec59bdcef77a83;
artifact13046722661 records securityVerified/sourceUnchanged/mainUnchanged=true and
policy/CAS/revocation/cross-tenant/history/worker-read-only/delivery-replay checks.
Root verified that merge and published head have identical tree
f9bdf08f364208e05e11beae89294d2ab8a9fac8 and head is an ancestor of the merge.
All eight new public-authoring PostgreSQL cases executed without skips; ordinary
backend workflow passes. Semgrep's four new findings are resolved.

Representative real E2E passes all five tests and six feature steps: normal UI
creation/editing, all three independent publications, public detail/body/private
absence, actual search-link navigation and immediate visibility restriction with
member access retained. Policy evidence is v3 public→v4 members-only, search3→0.
Isolated containers, volume and network are removed. Artifact13047730312 retains
six authoring captures and three public plus three restricted page captures.
Nine authoring/public screenshots were actually visually inspected:390px cramping
is resolved, focused controls/counters are unobstructed, desktop design preserved.
This is acceptance of those states, not a claim of every possible visual state.

Frontend751/752 unit tests pass; one new test observes parent presentation classes
before the edit-state effect settles after Discard. Preserve the native failure and
repair observation only if asynchronous transition is confirmed. All433 browser
checks are skipped because that unit stage failed, not accepted. Full134gate still
has not been invoked; media71 remains a separate blocked release obligation.

The test-only async observation repair is independently accepted: it waits actual
form exit and all original parent-spacing assertions with the existing timeout,
without changing product code or adding sleeps. Final local frontend752 tests plus
27 tooling checks pass; lint is clean apart from30 existing declaration warnings.
Coverage lines85.86%, statements83.94%, branches77.63%, functions82.80%; no production
executable delta. Native5ec50d0 is terminal with8/10 workflows green; only this
frontend unit observation and inherited media-security fail. Backend/restore and
all three real E2E jobs pass. First complete-gate invocation remains next, not passed.

### First complete-gate workflow setup attempt

The first opt-in workflow41214219187 on7fcbc15 verified exact clean source, installed
all three Python environments and passed dependency/import preflights and pinned
Node24.20.0/npm11.19.0 checks. Root npm ci then failed resolving peer dependencies
missing from the existing lock. No browsers/images/repetitions or134gate checks ran.
Safe stage-summary artifact13046803635 is retained; no pass receipts were fabricated.
Existing security workflows already install root dependencies with --legacy-peer-deps.
Match that established locked policy in the opt-in workflow, with a consistency
regression; do not regenerate locks, update unrelated dependencies or suppress errors.
Local copied-lock offline legacy dry-run succeeds265packages with unchanged hashes,
but uses npm11.9 and is not proof of the hosted install. Native rerun remains required.

- [ ] T38 Restore approved white/10 Records separator color with a scoped existing
      utility and native computed-paint assertion. Current matrix already passes;
      this corrects documented pre-existing tolerated drift, not the earlier fixture
      permission failure. No global CSS/framework/baseline changes.

T38 source and native assertion are independently accepted. The production change
is one existing border-white/10 utility on Records items; divider widths/layout
and global styles are unchanged. Native checks sample real computed1px solid paint
and respect forced-color CanvasText instead of disabling accessibility preferences.
Full frontend753 tests plus27 tooling pass, focused17/lint/types/build are green;
53 fixture contracts and24 matrix cases collect. Actual native paint verification
and pixel review remain pending. Root install-policy repair has85 focused checks
and independent acceptance; neither repair changes locks, permissions or baselines.

T38 normal-color native paint assertions and all24 workspace cases pass atc0c2751;
actual desktop/tablet/mobile/light pixels show restored subtle lines and intact
layout. Forced-color acceptance is NOT established by the conditional helper: the
named project uses an unsupported top-level setting. Do not infer that axe reset
it. Installed runner/type inspection confirms only contextOptions forwards that
option. Workspace/media/operations share the configuration defect; settings is
correct, and media-library's explicit prior runtime emulation was genuine.

- [ ] T39 Correct the three forced-color context configurations and assert actual
      expected media state across their specs. Preserve hard functional/axe/receipt
      semantics, collect truthful workspace HC comparison failures, inspect genuine
      pixels before reference corrections, and establish real native acceptance.

Second complete-gate workflow41215984737 passed dependency/browser/font setup and
both source-built images, then rejected post-setup source dirt before repetitions
or any134checks. Fresh-Git reproduction shows the two generated service virtualenvs
were not ignored (local private excludes had masked that). Root-only generated-env
ignores plus bounded quoted path diagnostics are independently accepted with92
checks; tracked edits/other untracked/nested paths and wrongSHA still fail. The prior
hosted paths were not printed, so this is reproduced diagnosis, not observed path
output from that run. No source reset, broad ignores or false pass receipt.

T39 implementation is independently source-reviewed: explicit contextOptions and
runtime active/none assertions, truthful HC-only workspace comparison batching,
and six additional targeted media/operations HC cases in native CI. The targeted
operations run uses line reporter and checks its tracked full-matrix receipt remains
unchanged, preserving original command failure even if receipt reads fail. Reviewed
reference files and visual-review manifests remain untouched.74 focused contracts,
fixture types and all configured collections pass; genuine native state/pixels are
not yet accepted. The accidental --list empty operations receipt was preserved for
diagnosis and restored exactly to HEAD, never accepted as new evidence; subsequent
collection uses explicit line reporter and verifies unchanged bytes.

Existing operations visual-review metadata already drifts from11 published sources
before this repair. Obtain fresh full-matrix evidence and source-bound review later;
never merely rehash it as accepted. Next publication is for genuine-state diagnostics.
Do not invoke the expensive complete gate again until those visual prerequisites
are established. The two prior complete-gate workflows executed zero gate checks.
