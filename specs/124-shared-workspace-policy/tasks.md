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

Native047546a completed8/10 workflows successfully; frontend and inherited media
security failed. Backend/restore and all three real E2E jobs pass. Frontend752/753
unit tests pass, but an immediate Stay lookup after a self-unmounting menu click
runs before the asynchronous blocker dialog renders. The retained DOM preserves
draft/location and lacks the modal; focus restoration is not reached. Audit related
async-opening observations, preserving original security/focus/history assertions
and default timeouts. All439 browser cases, including genuine HC diagnostics, were
skipped; no HC pixels or reference-validity conclusions exist for this head.

The bounded shared-guard readiness audit is independently accepted. Only settings
navigation/discovery tests now await actual modal readiness with default findByRole;
all history, location, draft, focus, inert, discard and forced-auth assertions remain.
Focused103 and full frontend753 plus27tooling checks pass; lint/types/build pass.
No product, HC configuration, baseline or timeout changes. Next native run must
establish genuine HC evidence; the two previous setup attempts still ran zero gate
checks and no new complete-gate trigger is authorized by this diagnostic publication.

Native274d05b reaches genuine HC. Workspace axe fails four primary controls and
operations fails Sign out/incident action: authored#1a0803 over forcedblack reports
1.07:1, while actual screenshots show white labels. Mode is active before/after axe;
this is not the prior ignored configuration. Workspace soft comparisons/four-view
summary are not reached because functional/axe checks remain hard. Media library
and detail pass; picker passes preceding mode/axe but fails stale normal-mode image
comparison, and actual empty search field lacks a visible boundary. Selection after
that hard comparison remains unreached. Hold reference acceptance; implement only
approved HC system-color/control-boundary semantics and preserve all normal design.

The HC-only control repair and hard native assertions are independently accepted
at source. Enabled primary system colors, picker field borders and selected-tab
underline preserve normal styling, disabled behavior and focus. Full frontend757
plus27tooling checks pass; focused15 and native source/config contracts76 pass;
fixture types and exact collection are clean. No baseline changes. Actual HC paint,
computed semantics, axe and reference validity remain pending.

Correct targeted scope: operations empty/recovery fixtures explicitly support only
compact/desktop and skipped HC in274d05b. The partial HC command now selects only
its exact supported main case; original full-suite tests/guards remain unchanged.
Additional executed obligations are3media+1operations, not six claimed states;
operations empty/recovery HC coverage is not established. Prior native total was
434passed/3failed/2skipped, and all workflows are terminal before next publication.

### Recovery preparation on 2026-11-01 (unpublished)

Exact checkout recovered at 93a3eccdcf58482c4b0182ef49c0c80eaae905ff,
tree 9c1654901bff19c4ae448e22981b798db86d14f9. Native run 41221368512 has
434 / 437 browser passes with three failures, confirmed from frontend job
124596436414 logs. Workspace has 23 passed / 1 failed; media HC has 2 passed /
1 failed; operations HC has 1 failed. The other six browser suites pass all
409 cases. The earlier 434 passed / 3 failed / 2 skipped total above belongs to
a different run and is preserved, not reconciled into this run.
The picker Status locator is corrected to exact combobox role/name with its source
contract failing first and all original border/mode/paint/axe/selection guards kept.
No product styling, thresholds, references or accepted manifests are changed.

- [ ] T40 Complete native HC visual recovery: recover artifact 13050237917 and
      artifact 13049683866 bytes, verify ZIP/member hashes, inspect actual/diff pixels
      before proposing the four workspace and one operations reference corrections.
      GitHub metadata matches run/head/ZIP digests; workspace download is blocked by
      proxy CONNECT 403 to the connector's file host. Bytes and pixels remain unverified.
      Picker reference remains unchanged pending fresh native functional/paint evidence.
- [ ] T41 Review and publish the recovered optional operations/media workflow only
      after coordination; run actual full matrices and independently review captures.
      Recovered workflow/backend/test files match all three supplied SHA256 values.
      Full inventories remain 42 operations (22 supported / 20 declared skips) and 36
      media (24 supported / 12 declared skips). No label or workflow run is requested.

Application types and isolated media/operations/workspace fixture types pass.
Line-reporter collection yields 24 / 36 / 42 cases, respectively workspace/media/operations;
tracked operations runner SHA256 stays
2ab8fe705f0640ee47a09cd5ed0d247da64abba3262bfb5be670b7112ed31d89.
Combined fixture type invocation exposes incompatible existing global axe declarations;
individual suite checks pass without source changes to those declarations.
Broader source-contract diagnostic: 104 passed, two failed, eight subtests passed.
Both failures are existing source-bound visual acceptance drift: media review predates
published UI/proof changes; operations manifest has 12 mismatched published-source
hashes at 93a3ecc. Preserve them; real full-matrix review must renew acceptance.
Focused workflow/forced-color contracts pass 91 checks. Initial expanded standard
CI-contract attempt passes 175 and fails four on absent local fastapi/psycopg2
prerequisites. Preserve that failure log. Installing the normal pinned
requirements-dev-api.txt into isolated .venv-api succeeds; pip check is clean and
the four previously blocked contracts then pass 4 / 4 without product changes.
Logs and failure evidence are retained outside the checkout in /workspace/recovery-124.
Full 134-check gate remains unrun, inherited 71 media security findings remain unresolved,
Feature 122 repair remains prohibited, and the broader family roadmap is incomplete.

### Bounded workspace PNG collection preparation (unpublished)

- [ ] T42 Add forward native collection of the four HC workspace views as separate
      bounded PNG artifacts. Preserve the existing complete artifact and all native
      failure outcomes. Include only exact actual/expected/diff/post-assert PNG names
      and small source/run/hash provenance; reject symlinks, output reuse and inputs
      exceeding 30 MiB per view without truncation. Verify copying, omissions, limits,
      failure provenance and upload contracts; independently review before publication.
      This does not recover artifact 13068039288 or accept any pixels. The parent
      reports that its size exceeds the supported 32 MiB transfer limit. No transfer
      limit or proxy bypass is authorized; snapshot thresholds remain unchanged.

### Screenshot lifecycle slice (preparation)

- [x] T43 Test/import explicitly inventoried synthetic PNGs with archive/member hashes,
      source ancestry, size limits, immutable original outcomes and deduplication.
- [x] T44 Validate separate immutable technical review and later native validation;
      preserve original failures and prohibit automatic baseline/acceptance updates.
- [x] T45 Inventory all screenshot producers, distinguish implemented bounded workspace
      collection from pending adapters, independently review and hold publication.
- [ ] T46 Import verified native workspace diagnostics and four reviewed HC references
      after byte/provenance delivery; retain first failures and run fresh native CI.

Pre-transfer checkpoint: 18 archive contracts passed. Independent review found and
resolved a PNG decode gap: CRC verification now precedes bounded full decoding;
a malformed-IDAT regression rejects the input before writes. No remaining blocking
review findings. At that checkpoint native archive population and fresh workspace
comparison were pending; unit fixtures are not native acceptance evidence.


T46 preparation: fetched unreferenced transfer commit c1fd5134f08af2905268b870a9a784db9896d003
without changing HEAD. Verified 30 supplied records against 29 exact Git blobs,
SHA256, byte sizes, dimensions and full PNG decode. Six immutable manifests now
retain all 30 captures; 20 new PNG objects remain after historical-baseline reuse.
Five technical reviews and one later targeted media/operations validation record
preserve original failures. Prepared only four reviewed workspace HC references.
T46 remains open for parent review/publication and fresh native workspace validation.


Retained archive maintenance: backend API CI validates committed manifests/events,
PNG hashes and full decoding, and historical baseline references with full checkout
history and no persisted credentials. Exact native merge-commit object proofs bind
tested source identity to tree-equivalent retained heads, avoiding dependency on
unreferenced merge or transfer commits. Native visual acceptance remains separate.


### Full matrix follow-up (unpublished)

- [x] T47 Preserve operations run 41283915226 failure (21 passed / 20 skipped /
      1 failed). Reproduce the cascade defect with a failing-first specificity
      regression; scope the correction to the existing reduced-motion media query.
- [x] T48 Prepare bounded per-project PNG and small report/source artifacts alongside
      the original full artifact. Test limits, unchanged bytes, incomplete captures,
      symlink/traversal rejection and unchanged native failure propagation.
- [ ] T49 Independently review and publish the bounded candidate only after review;
      obtain fresh exact-source native reduced-motion/full matrix validation.
- [ ] T50 Supplement media detail top and completed-state visual evidence, compact
      picker actions and large-text selection counter coverage. Diagnose scroll
      control overlap using viewport captures. No baseline edits in this batch.

The separately prepared passing-evidence batch adds 13 files and retains earlier
failures. Full media native success is scoped to 24 supported Chromium cases;
visual acceptance is pending technical review. No complete gate was executed.


### Media coverage/usability preparation (held)

- [x] T51 Import 24 diagnostic PNG captures from run 41283921639 using the verified
      Git transfer, deduplicate existing bytes and preserve native 24 passed / 12
      skipped plus known technical review limitations. Do not promote references.
- [x] T52 Add failing-first source contracts and focused selection-announcement
      regression; reserve intrinsic counter width with responsive toolbar wrapping.
- [x] T53 Add stable detail top/completed and picker-bottom diagnostic captures,
      plus viewport/hit-test evidence for floating controls; preserve old assertions.
- [ ] T54 Independently review the complete candidate, obtain publication review and
      fresh native evidence before accepting any new visual change. Earlier media
      source-bound accepted metadata remains stale; do not rehash it into acceptance.

- [ ] T55 Resolve global footer wording in a separately reviewed copy change.
      HomeFooter.jsx labels its static panel Preview status, but unconditionally
      displays System evidence current with no live-service or evidence freshness
      input. It can mislead beside stale/unavailable operations data. Proposed
      follow-up: label this as preview information and state that service freshness
      is reported in the operations panel; do not claim current build evidence
      without a bound source. No global shell or reference changes in this slice.

- [x] T56 Close bounded viewport-observation delivery: persist and attach identical
      explicitly named synthetic geometry JSON, validate its strict schema and
      64 KiB limit, package it only with the corresponding project/case viewport
      PNGs and record byte/hash provenance. Exclude arbitrary/private JSON and
      preserve missing-data visibility and original native failure outcomes.

### Native media follow-up on head 173c17ea

- [x] T57 Diagnose run 41287894771 compact/400-zoom preview failures: native
      images confirm right-edge horizontal clipping. Constrain the existing mobile
      grid and preview inline size; preserve 14rem minimum height and ratio-1 check.
- [x] T58 Move supplementary viewport scrolling after the established full-page
      comparison/current capture. Keep hard comparison failures and rethrow them after diagnostics, remove screenshot-only header style, and verify authored sticky
      positioning before viewport diagnostics. Light mismatch was floating-control
      placement; no light baseline update is authorized by that failure.
- [ ] T59 Obtain independent review and fresh native validation for this narrow
      follow-up. Preserve the original 20 passed / 12 declared skips / 4 failures.
      Large-text counter reflow is intentional but references remain unchanged
      pending fresh pixel review. Centered hit tests in four reviewed projects
      do not establish absence of obstruction at every scroll position.
- [x] T60 Set an explicit light foreground on the authored dark preview gradient;
      verify computed foreground contrast against both stops in non-forced modes.
      Keep native forced-color adjustment and existing accessibility checks.
- [x] T61 Extend bounded viewport observations to all visible card targets, using
      version 2 with explicit card/target indices, maximum 25 unique targets per
      sampled viewport, unchanged 64 KiB limit and backward validation of version 1.
- [ ] T62 Resolve confirmed floating-control overlap with non-centered card text.
      Existing centered-only observations missed this defect. Review a responsive
      control placement strategy before changing shared navigation or references.

Native review further confirms landscape-touch ascend intersections with first
card-action rectangles on cards 0, 2 and 4 despite clear center hit tests; pixels
show circles covering button corners. Desktop, high-contrast, reduced-motion, RTL
and phone-DPR3 viewport samples 0/2 also obscure neighboring-card filenames omitted
by the former centered-card observations. Version 2 enumerates all visible targets
and retains rectangle intersections independently of center hits. A clear center
must never certify an unobstructed action or erase a corner-overlap finding.

### Reserved control-space implementation (owner-approved; publication held)

- [x] T63 Map shared movement consumers, document/element scroll assumptions and
      modal locks before implementing a distinct shell slice on 2939e45f.
- [x] T64 Add desktop logical gutters and compact bounded content plus separate
      dock, preserving button appearance, movement toggle and legacy consumers.
- [x] T65 Add explicit target metrics/events/edges/anchor alignment, responsive
      position preservation, stale-timer cancellation and target-aware modal locks.
- [x] T66 Migrate actual media/operations/interaction scroll helpers; add unit and
      native geometry contracts for corners/all visible targets, focus, footer,
      toggle, forced colors, RTL, zoom and short landscape.
- [ ] T67 Finish independent review and local validation; obtain parent publication
      review, then fresh native cross-device evidence and technical pixel review.
      No reference or acceptance-manifest updates are part of this source candidate.

Review-driven corrections in the shell draft: malformed fragments are ignored;
retained hashes do not replay on target-only transitions; observer cleanup covers
both layout subscriptions; native edge checks use the real target. Drawer body
locking has one owner and nested-target locking is separate from focus trapping.
Pending legacy section movement timers/frames now cancel on unmount or target
change; an immediate-unmount regression covers the previously escaping callback.

Further shell review corrections: all modal/document overflow owners now share
reference counting; ancestor-inert palette shortcuts are blocked. Repeated picker
button-close and out-of-order lock release have regressions. POP restoration keeps
pending offsets during bounded async content growth, with observer cleanup tests;
cold compact fragments wait for the real target without resize/hash replay.
Native execution and actual mobile virtual-keyboard behavior remain pending.

History identity audit: cold and native null-state fragments no longer share a
custom `default` slot. Real href fragment regression covers repeated fragments,
Back/Forward, query changes, keyed-save isolation and unchanged history state.
Unkeyed nested-scrollport exact-offset restoration remains a stated limitation.

### Native shared-shell repair on cb674560 (publication held)

Original run 41295005783: 423 / 443 browser cases passed; 20 failed. Full media
41295029086: 7 passed / 17 failed / 12 declared skips. Full operations
41295038159: 1 passed / 21 failed / 20 declared skips. Preserve those outcomes
and all original references; current repairs are not fresh native validation.

- [ ] T68 Verify scoped focus margins exclude dialog descendants while retaining
      the existing media pending-action alignment tolerance of 2 pixels.
- [ ] T69 Verify available-width operations grids and workspace record/inspector
      containment in large text, light and high contrast; do not conceal overflow.
- [ ] T70 Verify pointer movement double-click lifetime and zoom drawer reachability.
      The pointer regression reproduces immediate first-click removal. Retain the
      control while pointer or focus engages it, preserving immediate single-click
      movement and slow double-click recognition without a guessed timer.
- [ ] T71 Resolve compact timeout and Firefox contact focus from native trace/DOM
      evidence. Existing logs do not identify compact's stalled action or Firefox's
      actual focus progression. Keep assertions and timeouts unchanged; new bounded
      console diagnostics are preparation, not fixes or proof of resolution.
- [ ] T72 Execute later independent operations states despite snapshot differences;
      native soft comparison errors remain fatal and successful reference-byte
      attachments remain distinct from current actual captures. State-specific
      viewport captures supplement fullPage under nested scrolling.
- [ ] T73 Verify named-route captures before navigation and visible footer evidence.
      Schema v4 retains original scrollport/intersection geometry and adds the
      sticky-header-unobscured rectangle plus all four persistent shell controls.
      Previous v1/v2/v3 receipts remain immutable. Compact drawer toggles now occupy side slots in the reserved control strip;
      colors/icons/curved edges are retained with 44-56px targets. Movement-disabled
      positions remain unchanged. Native
      footer checks include all four persistent controls. Fresh native proof is pending.

Review v2 correction: geometry v4 permits three/four unique present control IDs per
target, while v1-v3 retain their two-control cap; duplicate IDs are rejected. Exact
three/four-overlap bytes round-trip through bounded packaging without suppressing
native failure. Strict focus diagnostics export only allowlisted tags/roles/IDs.

### Native prerequisite and bounded-part correction (publication held)

- [ ] T74 Replace obsolete authoring/non-authoring class assertions while keeping
      mobile padding, edit-state transitions and containment coverage; run all
      frontend unit/tooling tests with unchanged coverage floors. Original run
      41314685335 remains 783 passed / 4 failed, with no standard browser execution.
- [ ] T75 Split operations/media diagnostic members into deterministic <=30 MiB
      ZIP parts, bind exact member/part identities and upload parts independently.
      Reproduce the old aggregate-budget failure; test boundary, tamper, unsafe
      path, interrupted packaging and failure-preserving upload behavior. Original
      WebKit packaging failure in run 41314740935 remains preserved. Native
      transport validation and current pixel review are still required.

### Native functional and continuous evidence batch on da4d0a72 (held)

Original standard 41316879851 remains 423 passed / 20 failed; media 41316950722
12 passed / 12 failed / 12 declared skips; operations 41316938996 1 passed /
21 failed / 20 declared skips. No reference acceptance is implied.

- [ ] T76 Reproduce keyed Forward 100-versus-180 ownership loss, Firefox Tab
      returning to descend, and zoom timeout after completed movement checks;
      retain exact offset/focus/time limits and establish causes before repair.
- [ ] T77 Add bounded overlapping native viewport sweeps with interval-union,
      route/state/target binding, attempted frames before fatal assertions and
      failure-preserving cleanup. Cover nested pages and dialogs explicitly;
      count/byte ceilings fail incomplete evidence rather than truncate it.
- [ ] T78 Review both slices independently, run complete unit/tooling/contracts,
      types/lint/archive validation, and hold publication for parent review.

### Post-14a1441b native review: RTL separation and neutral-focus evidence (held)

Standard run 41323136993: 808 unit + 27 tooling passed; browser suites 423 passed /
21 failed out of 444. Compact keyed Back/Forward (100/180), zoom exact-zero Ascend,
and the Firefox contact focus suite passed in this run. RTL and light 200% RTL
failed the unchanged focus-ring separation assertion; no baseline was accepted.

- [ ] T79 Clear legacy physical circle offsets only inside the bottom dock so
      writing-direction-aware grid slots retain the reserved gap. Preserve target
      dimensions, focus outlines, side/off modes and native intersection assertions.
      Require fresh all-four-control RTL captures and geometry after review.
- [ ] T80 Retain original focused context separately from neutral-focus content
      sweeps; restore original focus and scroll without replacing earlier failures.
      Schema 2 must explicitly state geometric-only completeness and require
      independent unobscured-content review. Original schema 1 records stay intact.
      Operations landscape run 41323158842 and six workspace mobile/tablet sweeps
      from run 41323136993 are not eligible as unobscured reference evidence:
      the focused Skip overlay hides content despite their geometric interval union.

## Reference sequence renewal source preparation (2026-11-01)

Source checkpoint 3d065cfc0d6a9facbb4f1bb4dc188ae6b5be4db4, tree
f56bfbc159929e11a7cbfcc3c397ef9172732ea2: standard native run 41327081761
completed 425 passed / 19 failed; optional media 41327121096 completed 12 passed /
12 failed / 12 declared skips, and operations 41327110311 completed 1 passed /
21 failed / 20 declared skips. Browser failures remain comparisons. The compact
Back/Forward 100/180, zoom Ascend, Firefox Name focus and all 28 dock focus
captures passed their native checks. Independent review specifically inspected
17 landscape operations neutral frames, 41 workspace neutral frames plus six
original focus contexts, and all 28 dock controls. These facts establish the
scoped repairs, not release or reference acceptance. Security remains failing.

- [ ] T81 Preserve desktop full-page comparisons. Add nested viewport overview
      and complete neutral segment comparisons, tied to exact state/geometry,
      dependency/configuration identities, reviewed source ancestry and an
      explicit review record. Missing/changed sets remain fatal and read-only.
- [ ] T82 Retain actual/expected/diff only when those roles exist, with independent
      receipt validation. Bound collection across all configured states; preserve
      full artifacts and native failures. Add exact journey comparison collection
      and privacy-safe producer exclusion receipts. Test tamper and error precedence.
- [ ] T83 Independently review final source, then obtain genuine native captures
      before any image approval. No old full-page reference may be replaced by
      merely the first nested viewport. Two original journey actuals remain
      unavailable due to the 32 MiB transfer cap; no substitute image is accepted.

Source-v2 review corrections for T81–T83: preserve picker failure while continuing
ready checks; remove the operations legacy header override before genuine sequences;
require explicit target applicability; separate named-route reference namespaces;
and retrieve validated partial transport without converting packaging failure to
success. Native validation and every new image approval remain pending.

## Native reference infrastructure repair (2026-11-01)

Head 599beaa4313bc946cd2a992831773c6ab6506b8e: standard run 41338007556
completed 399 passed / 45 failed, media 41338046706 completed 1 passed / 23 failed /
12 declared skips, and operations 41338039571 completed 22 failed / 20 declared
skips. Font inventory symlink rejection occurred before sequence comparison;
these runs produced no sequence candidates or missing-reference verdicts.
Original artifacts and diagnostic sweeps remain preserved. Backend run 41338007718
also exposed a direct-script import failure masked locally by PYTHONPATH.

- [ ] T84 Correct direct archive CLI imports using the script's own repository
      root; test without PYTHONPATH from an unrelated cwd and preserve the fatal
      missing-manifest guard. Revalidate the complete committed archive.
- [ ] T85 Separate installed-font alias resolution from strict reference paths.
      Require canonical bytes within explicit system-font roots, retain bounds,
      and emit only bounded root-relative identities. Runtime identity failure
      must remain fatal with no candidate binding, while independently ready
      later states execute. Exact offending historical native alias is unknown.
- [ ] T86 Correct the demonstrated scaled document/element anchor-coordinate
      mismatch and add bounded toggle/close checkpoints. The zoom offset-zero
      failure at line 560 is not proven resolved until fresh native validation;
      retain its positive-offset assertion and all subsequent Ascend checks.
- [ ] T87 Review finite producer-specific journey retention additions separately.
      Source predicts 180 excluded journey outputs, but historical exact paths
      remain unavailable. One layout and one Volcano exclusion remain unidentified.
      Preserve unknown counts and require new native identities before claiming recovery.

## Responsive content and modal repair (2026-11-01, source 796f11a9)

Historical native comparisons remain failures; no references are renewed by this batch.
Current scope is synthetic fixtures and existing UI, with no live writes/providers.

- [ ] T88 Keep media card action borders and labels within available card width;
      verify all visible actions numerically and inspect fresh desktop pixels.
- [ ] T89 Give operations cancellation shared background inertness, stacking and
      scroll-lock ownership. Prove heading Shift+Tab, background guards, Escape,
      Keep job and asynchronous confirmation focus, including a removed row.
- [ ] T90 Resolve T55 using neutral footer wording without a live freshness claim.
      Require new pixels for every affected footer; retain old evidence unchanged.
- [ ] T91 Add selected-record edit diagnostics at compact, large-text and desktop.
      Use a per-test synthetic versioned PATCH store matching the existing journey:
      persist explicit values/public content, reject stale If-Match, verify discard,
      save and reload. Empty-inspector references do not prove selected editing.
      The native workspace inventory becomes 36 identities: 27 supported cases
      and 9 declared skips (the additional selected-state test runs in 3 projects).
- [ ] T92 Stack import options and the shared type selector by available width;
      retain native controls and expose the full selected filename separately.
      Assert policy/type text fits the native controls; filename summary is not a
      claim that the native file-control filename itself never ellipsizes.

Selected-state transport adds two exact diagnostic PNG names per supported project
and two compact continuous states (each maximum 64 segments plus original focus
context and 3 sampled views). Successfully captured edit/saved states do not run
a redundant generic afterEach sweep; early failures still attempt it.
No new expected/reference PNGs or image approval. Existing
collector per-file/part/total limits remain fatal and unchanged.

Validation boundary: static, full unit/tooling, expanded contracts, type/lint and
archive integrity precede independent review/publication. Native browser validation
and fresh pixel review remain pending. The previously recorded WebKit-mobile
afterEach footer ratio-zero/timeout remains an open diagnostic issue; this batch
does not raise its timeout or weaken footer reachability. Named-route fallback
captures prove their observed fallback states, not populated content readiness.

- [ ] T93 Preserve cancellation's authored card/button/focus styling after portal
      relocation using an explicit surface scope, never a duplicate shell root.
      Assert light/theme token colors, keyboard focus paint, system forced colors
      and exact-zero reduced motion in the cancellation state itself. Source-v1
      remains retained; the portal styling correction is a distinct v2 delta.
      Lock counts do not constitute nested-modal keyboard/focus arbitration.
      Current cancellation settlement keeps its existing return-focus policy;
      deliberate user focus changes during the request are not separately tracked.

- [ ] T94 Keep the background Cancel locator exact while the cancellation dialog
      is open. Native run 41351046458 on 33b2d5d3 failed all 14 main cases at the
      programmatic background-focus probe because partial names also matched the
      dialog action (English, Arabic and German). Preserve that first failure,
      the focus attempt, and the assertion that the inert shell cannot own focus.
      The narrow selector correction requires fresh native lifecycle evidence;
      static uniqueness does not establish browser inertness or cancellation success.
      Separate current-run blockers remain: workspace policy/type label fit,
      selected-edit field locator, and WebKit body timeout. No references renewed.

- [ ] T95 Correct selected-edit lookup to the exact textbox accessible name;
      preserve actual Tab, discard, save, reload and stale-version assertions.
      The populated textarea is nested inside its label, so raw exact label text
      also includes the initial value. Original three native locator failures are
      retained; no edit/save checkpoint was reached in run 41351017132.
- [ ] T96 Reserve enough width for Content type after the card's authored padding
      and remove redundant horizontal Imports-panel padding only in narrow detail
      containers. Native failures measured 143/150px available versus 153.76px
      required for Content type, and 59.4px versus 78.79px for Commit policy.
      Keep the full-label and enclosure assertions unchanged; fresh native pixels
      must establish readability. WebKit's 60-second body timeout remains open;
      current checkpoint receipts require inspection before a causal repair.

- [ ] T97 Repair selected-editor media heading hierarchy (record h3 → media h4)
      and reset the structured fieldset's browser min-content inline minimum so
      its native file control can shrink within the inspector. Preserve disabled
      fieldset semantics, existing styling, axe and all native containment checks.
      Run 41354479659 proves focus, Discard, zero updates, original record equality,
      reopen and original-title assertions in all three selected-edit scenarios.
      Compact then fails heading-order; desktop/large-text fail panel scrollWidth
      containment despite enclosed outer edges. Save remains unproven. The
      fieldset sizing repair needs fresh native geometry/pixels; DOM tests do not
      establish browser layout. Optional runs preserve both legacy screenshot
      mismatches and missing sequence-reference failures. WebKit capture ownership
      remains a separate read-only proposal; no timeout or coverage changes here.
      Fresh native pixels additionally show the viewport-md relationship grid
      squeezing Add relationship into a tall word-broken column. Replace its
      fixed minimum columns plus residual action slot with available-width tracks
      (14rem preferred, bounded by full available width). Extend native containment
      to all nested structured sections, fieldsets, forms and controls. No clipping
      concealment; media sections retain their original styling.


- [ ] T98 Repair the standard gates exposed by native head 237298: preserve the
      original 919-pass/1-fail unit result and 401-pass/4-fail backend contracts.
      Edit entry sets inspector state before its passive onEditingChange effect
      reconciles parent spacing; require both form readiness and parent editing
      presentation before asserting pristine width, without sleeps or weakening
      the disabled Save assertion. Update source contracts to require ownershipStep
      around the same capability, divider, keyboard and forced-color operations.
      Inventory the direct ownership screenshot producer and hash-bound delegated
      callers; verify it remains in sequence dependency fingerprints. Run the full
      standard unit command and exact backend CI contract selection. Selected Save,
      native heading/containment and ownership quiescence remain unproven because
      the original standard browser suites were setup-blocked. No reference,
      timeout, acceptance or security changes; publication held for review.

- [ ] T99 Retain selected-details mobile width after save/discard independently
      of editing mode. Native 656507 selected cases prove save/reload and all
      scoped assertions, but compact saved controls visibly clip and wrap within
      words. Add full authored-label width checks for Secure file, relationship,
      review/publish/delete actions and the native Choose File button. That native
      width check is necessary, not sufficient pixel proof; inspect fresh frames.

- [ ] T100 Split corpus into Records/Schema/current and Imports/Exports/current.
      Both fresh cases retain original Records preparation, static-header fixture,
      keyboard/theme/axe checks and Records→Schemas transitions; the second then
      traverses Imports→Exports. This replaces the uninterrupted four-view capture
      journey with paired scenarios and increases aggregate permitted setup,
      execution and output work; it is not a proven timeout-performance repair.
      48 configured cases = 24 corpus + 12 vocabulary + 3 supported selected +
      9 selected skips. Named comparisons remain 48; generic corpus opportunities
      increase from 12 to 24. Keep 60s/test, 10s assertions, 64 segments/state,
      512 ownership frames, 192 checkpoint events/128KiB, all image/transport caps.
      Preflight estimates do not guarantee completion: actual geometry/bytes and
      runtime budgets remain fatal/incomplete when exceeded. Exact new producer,
      title/state bindings invalidate prior sequence candidates; no PNG approval.

- [ ] T101 Reserve whole compact inspector rows for saved workflow and confirmation
      actions, preserving primary/ghost hierarchy, order, versioned transitions and
      desktop layout. Native 16f2a3c proves Secure file recovered but Submit for
      review still fails strict width (108.331 available vs 108.34159851074219
      required), despite one rendered line and containment. Later compact Publish,
      Delete, relationship and file-caption guards were not reached; do not infer
      their success. Retain strict width, line, containment and count assertions;
      emit the same bounded numeric diagnostics for all fixed saved action labels.
      Validate all three workflow cancel/confirm transitions and narrow container
      scoping. Fresh native compact/desktop/large-text pixels and complete saved
      guards remain required; no tolerance, reference or acceptance changes.

- [ ] T102 Retain native inline workflow and restore confirmation attempts in a
      separate compact/desktop/large-text synthetic case. Ordinary Saved and
      operations cancellation captures do not prove these panels. First unit
      reproduction found missing entry focus on all four panels (4 failed,
      35 passed). Add safe-dismissal entry focus, local Escape dismissal and
      explicit trigger restoration only; preserve inline non-modal presentation,
      disabled/dirty guards and all actual transition handlers. Native coverage
      opens Submit/Publish/Delete/Restore, captures before assertions, checks
      strict full-label width/containment and viewport visibility, dismisses by
      Escape and button, and forbids every content mutation request. A per-case
      cloned version-2 record and existing version-1 history contract expose
      Restore without performing it. Register four exact attempt states plus
      required generic current coverage; retain primary errors and partial frames.
      60 configured cases = 24 corpus + 12 vocabulary + 3 selected + 3 confirmation
      + 18 declared skips. No existing obligation is removed. New case maximum
      is 4 attempt PNGs + generic 64 segments + focus context + 3 samples = 72
      ownership frames, below unchanged 512 ceiling; byte/transport bounds remain
      fail-closed, not guaranteed fit: simultaneous maximum 72 x 32MiB x three
      projects alone exceeds 6GiB. Do not raise caps to make this maximum fit.
      WebKit confirmation is declared skipped;
      existing 192-event checkpoint cap and all per-test timeouts unchanged.
      Native confirmation fit/focus and independent pixels remain pending; no
      reference approval. Full logs and original focus regression must be retained.

- [ ] T103 Preserve same-record focus when confirmation flows are interrupted.
      Retain the 10-fail/41-pass reproduction: dirty or hidden triggers cannot
      safely receive return focus, and authoritative version changes can remove
      an entry-focused panel. Observe focused-panel detachment with stable refs,
      then restore after commit only if focus has not moved elsewhere. Prefer
      the connected, enabled, visible same-record trigger; otherwise use that
      record's programmatically focusable heading without adding a Tab stop.
      Never restore across account/type/record identity boundaries. Cover both
      panels, Escape and button dismissal, repeated dirty opens, hidden triggers,
      retained/removed triggers on version refresh, outside-focus intent and
      blocked mutation guards. Keep all cleared transport paths/obligations/caps
      byte-identical. Native confirmation evidence remains pending review/run.

### T104 — Confirmation surface width and authored unobscured entry (held)

- Original exact-head native run `41385754860` at `7841d440` retained two real confirmation failures: compact Submit for review's focused Keep unchanged label wraps (`94.081` available versus `101.802963` required); large-text Restore's top boundary sits behind the sticky header. Desktop completed all four; large-text completed Submit/Publish/Delete before Restore; compact's four obligations remain incomplete. Parent reviewed exact attempts `6d136efa5166389c046324a1f8e044a4abf21c45766cd44954639365d9e1d054` and `544f6e43a2adf8ceb5b5ab3929c1e41d03a4fbe2ab62842494512d060b5ab20d`.
- Narrow confirmation surfaces now use half-rem inline padding inside the existing narrow detail-card query, preserving the border, vertical padding, button hierarchy, full-row actions, and wider layout. No label/fit tolerance changed.
- After safe entry focus, both inline panels use the existing shell scroll-target adapter's measured header inset. The latest target is read only on entry; target replacement or editing does not refocus an open panel. Native confirmation checks no longer impose browser-centered scrolling over the authored placement; attempted screenshot, strict whole-box visibility, ratio-one viewport, label/line/containment, Escape/cancel restoration and zero-mutation assertions remain.
- Original local reproduction: six failed,55 passed before product/test-placement correction. All original native failures and previous review artifacts remain immutable. Wrong-cwd test/format invocation errors were retained separately; they are not functional test results.
- This patch is held for independent review and fresh native proof. No new reference acceptance, security/runtime changes, timeout/cap changes, or publication. Scenario counts, producer paths, four confirmation obligations and generic capture remain unchanged.

### Held confirmation capture settlement candidate (be6 follow-up)

- Confirmation entry alone requests explicit instant shell alignment; default navigation/movement scrolling remains unchanged. Smooth scrolling is a source hypothesis, not an established cause of the original native captures.
- Capture settlement observes at most 32 probes and 1,000 ms within existing test/ownership budgets. It does not repeatedly scroll until visibility passes. Each state retains its one attempted screenshot before fatal endpoint/visibility validation, including best-effort capture after settlement failure.
- New exact-producer confirmation endpoint receipts bind source/tree/run/attempt/project/state, PNG bytes/hash, bounded numeric geometry and enumerated focus immediately before/after capture. Strict collector validation independently derives visible clipping; endpoint agreement is not intermediate compositor proof or pixel acceptance. Partial receipts remain diagnostic and incomplete. Four named confirmation obligations and generic fallback remain required.
- Original be6 failures, prior reference bytes, and the unrelated operations runner modification remain retained. No reference renewal, zoom migration change, publication, timeout/cap increase, security/runtime change, or live mutation is included. Fresh native confirmation and original-resolution pixel review are required after independent source review.

- Review revision: confirmation ownership schema 2 requires mandatory exact endpoint-receipt/frame crossbindings; legacy ownership schema 1 remains historical diagnostics, not capture-time proof. Endpoint schema 2 verifies layout-derived max/scale, sticky header presence, explicit elastic overscroll as incomplete, and complete CRC/deflate/scanline PNG decoding plus raster/DPR binding. The original v1 artifact and reviewer repros remain retained.

### Held inverse-toggle lock-handoff correction (2250 follow-up)

- Published `2250c173` / standard `41401040398` retained 399 browser passes, 63 failures and 18 declared skips: 56 reference-only cases, compact Submit endpoint failure, and six inverse movement failures. Parent verified matching head/merge tree `9c34240a2f0143684e24e3c53ae16cbaee4bde48`. No failures are relabeled passing.
- Native zoom records original nested offset 1305.5, clamped document offset 2379, then nested offset 1189.5; original landmark gap remains 212.578125 instead of returning to -19.421875. All six cases stop before Escape/after-close/footer/180/exact-zero. Console geometry is not an image-hash-bound receipt.
- Deterministic real-navigation/adapter fixture reproduces exactly 1189.5 versus required 1305.5 when the old nested overflow lock temporarily owns sticky positioning. Bookmark geometry is now sampled in the parent passive effect after child lock cleanup, rather than the earlier layout effect. One migration correction, observation-only settling, genuine user-input/viewport invalidation, focus/locks/history, and all strict native assertions remain unchanged.
- Native geometry regression covers round-trip preservation and rejection after user scroll-away/back or viewport change. This establishes the source failure mechanism under the fixture; fresh native evidence is still required before claiming the six cases repaired.
- Compact Submit's separate 0.40625px header overlap is confirmed by parent receipt/pixels. Rendered-boundary plus real entry-spacing correction remains a proposal, not included here. Desktop/large-text eight confirmation attempts were independently valid. No reference/security changes, timeout/cap increases, or publication of this held correction.

### Held standard forced-color retention correction (3a1 follow-up)

- Parent mapped 99/102 legacy actuals and 107/113 sequence sets (572/588 images). Missing standard HC originals remain in the 34,026,133-byte artifact 13125460077, above the 32 MiB retrieval limit. Optional images are not substitutes; this patch cannot recover historical bytes.
- Add exact standard media HC (three authored cases) and operations HC (main case) roots and independent native outcomes to bounded staging. Closed producer/state/name rules include all registered outputs, not only currently missing sets. Preserve the full original artifact, safe partial uploads, producer quarantine, original native failures, strict receipt/image binding and unchanged count/byte/wrapper budgets. Missing declared forced producers are fatal with explicit incomplete metadata.
- Tests cover failure-first omission, exact project/title identities, roles/hash fidelity, missing producers, invalid receipt quarantine, future registered states and ZIP overhead. Typed archive dispatch remains a separate reviewed slice. No reference, product, security/runtime or acceptance changes; no publication until independent review.

- Parent review revision: HC media observations now require each declared viewport's exact already-validated PNG from the same producer. Missing indices 0/2/4 quarantine the library producer and remain fatal/incomplete while valid detail/picker originals survive. Five failure-first regressions (four missing-viewport cases and desktop-only HC leakage) are retained; a fixture-parent setup failure is separately recorded.
- HC operations allowlist now excludes desktop-only legacy cancellation names and their nonexistent sequence state. The genuine HC `operations-cancel` and `operations-center-chromium-high-contrast` states remain registered. No schema, count, byte, threshold, timeout or original-artifact changes.
