# Task → analysis → refinement

## Cycle 1 — Why green tests missed the rejected design

The previous suites required generic rails and reviewed newly generated screenshots,
not preservation of the original accepted menus. V002/V003 add original-state
references before repairs. Replacing controls with similarly functional controls
is explicitly insufficient. Keep negative structural checks and image comparison.

## Cycle 2 — Preserve working changes and approval boundaries

A blanket revert of PR #68 would discard account/privacy/security work. V004 is
limited to Home composition. All other code remains intact. V006 is a real owner
checkpoint; don't repeat the prior broad rollout before visual confirmation.
V007–V010 retain permission filtering, focus/modal behavior, real content readiness,
error states, profiles, locales and coverage. No baseline updates merely for green.

## Issue ledger

### Cycle 14 — live readiness and fixture alignment

VOL-21 (evidence prerequisite): first gate on d9d919c rejected the old exact-source
repetition receipt. Generate through `feature_106_repetitions.py` before complete
validation of a new commit; never patch/relabel the receipt. Corrected gate passed.

VOL-22 (test readiness): signup updated browser history before React necessarily
committed the pathname-keyed navigation. The shared-menu test could click the old
signup menu and then observe the fresh closed dashboard menu. Require the Dashboard
heading before interaction, not a fixed sleep/retry or product timing change.
Corrected full live run passed that complete settings journey in 27.8 seconds.

VOL-23 (operator fixture): running media with revised credentials exposed that the
workstation principal helper ignored `BASE2_LIVE_FIXTURE_REVISION`. Access denial
was correct. Helper now uses one validated identity for credentials and principal;
its pure regression covers default/-r1/-r99 and hostile/out-of-range identities.
Affected live media replay passed in 1.2 minutes after actual principal correction.
No API permission expansion, auth bypass or product/image change was made.

Acceptance: all live surfaces have passing evidence; owner login and runtime checks
pass. Preserve original failures and separately identify test-only source from the
deployed application commit. Supported standard assurance and hosted checks cover
this test/docs closeout, without rebuilding an identical application or extending
its lease. Owner review and expiry cleanup remain outstanding external checkpoints.

### Cycle 13 — PostgreSQL and live-negative evidence

Reproduced missing table privileges with actual restricted credentials. The next
round exposed an adjacent worker-only policy referencing private audit rows for API
reads; scope that unchanged claim predicate explicitly to the data-rights worker,
not by granting API audit access. First passing role round also corrected a test
UUID/string comparison (the API normalizes receipt IDs through its UUID schema).
After workstation restart, reran the final expanded PostgreSQL suite: public reads,
private/draft/cross-tenant denial, direct SQL write denial, moderated community
inserts, form replay/conflict, forbidden outbound adapter, pool tenant reset,
workspace/data-rights acceptance and migration reverse checks all passed.

Durable evidence: `.artifacts/feature110/public-content-postgres-restart.log`.
Focused API tests: 42 pass; migration tests: eight pass. Repository and new migration
each have 100% statement coverage; this is not universal defect assurance. Coverage
JSON and logs are under `.artifacts/feature110/public-content-*`.
Both stronger live route tests fail on the old deployment's 503s as expected,
after collecting all route failures: `public-content-live-negative.log`.
Disposable-runner errors now redact command arguments, which contained ephemeral
test credentials; failed containers were removed and no live credential was used.
No style or baseline changed. Full gate, hosted CI, merge and corrected live
acceptance remain required. Existing preview expiry was restored after restart.

### Cycle 12 — approved public-content repair refinement

Owner approved secure backend repair. C01–C06 cover reads and adjacent writes.
Use column-scoped grants, never the privileged workspace pool. Restrictive API-only
SELECT policies must intersect existing permissive tenant policies, keeping drafts
and private media invisible even to direct SQL. INSERT is limited to moderated
community drafts, queued tenant-bound forms and disabled delivery outbox records;
no UPDATE/DELETE or form payload reads. Preserve other roles' existing policies.
New RLS tables need reversible baseline policy preservation and real forward/reverse
checks. Tests must exercise the production repository under actual restricted
credentials, not mocks or database-owner queries. Inspect required insert columns,
idempotent receipt behavior, tenant reset and migration readiness. Unexpected 5xx
must fail live acceptance even if page screenshots show the correct shell.

### Cycle 11 — live proof and bounded follow-up

VOL-19 (test defect, fixed): settings save succeeded but `getByRole('status')`
matched both the retained navigation output and the success message. Filter the
two assertions by their expected message; do not alter the approved navigation.
Full affected live journey passed after correction (24.7 seconds). Original failed
attempt remains in `/tmp/f110-live-browser.log`; corrected evidence is in
`/tmp/f110-live-settings-r1.log`. Supported auto assurance selects the standard
test-only scope, not another full product release gate.

VOL-20 (functional blocker, awaiting scope decision): public CMS endpoints return
503 from `InsufficientPrivilege`. The public repository uses the API role that
migration 0032 intentionally restricted. A blanket grant or switching every method
to the workspace pool is not an acceptable unreviewed repair: public reads, drafts,
search, media and form writes have distinct permissions and tenant boundaries.
Evidence: `/tmp/f110-live-content-diagnostic.log` and mobile About screenshot in
the current preview's `browser-f110-final` directory. Before implementation, add
least-privilege role/tenant/unpublished-content/write-denial regressions and real
Postgres acceptance, plus live route readiness assertions that reject unexpected
5xx while collecting independent failures. Shell-layout success is not content
readiness. No database permission change made pending owner's scope decision.

### Cycle 10 — preserve reviewed ancestry after squash merge

VOL-18: the f5537a8 complete gate passed 115 checks, failed the Media review
ancestry contract and correctly blocked four dependent checks. PR #70's squash
retained the exact source tree but not reviewed ancestor 662e34b. Evidence:
`20261013T205050Z-881166/media-library-contract.log`. Integrated the original
reviewed branch history through merge c4f3fbb, preserving the complete f5537a8
tree (verified empty diff); retained current repair docs when resolving three
add/add documentation markers. No review receipt or image changed. The review
contract now passes. All remaining feature merges must preserve ancestry, now
documented in AGENTS.md. Current complete validation is still required; no failed
or blocked result is relabeled. The sole new code repair remains VOL-17.

### Cycle 9 — live cold-start health probe

VOL-17 (live blocker): main 278b063 exactly matches the 120-check/20-hosted-check
candidate; all 10 post-merge workflows pass. Live preview 20261013-202131 built
and started successfully, but scheduler health repeatedly timed out at 10 seconds.
A bounded read-only diagnostic took 23.46 seconds and returned healthy. Scheduled
tasks execute successfully, memory is available and the scheduler is not OOM-killed.
The probe imports operations_runtime, which pulls in database, repository, storage
and application settings merely to read one Redis heartbeat under 0.25 CPU/128 MiB.
pgAdmin also initially exceeded startup checks, then recovered without a restart.

Evidence: `/tmp/f110-live-heartbeat-diagnostic.log`, `/tmp/f110-live-launch.log`.
Stopped only the exact source-bound bootstrap; the launcher's error cleanup removed
its droplet. Inventory confirms zero droplets/DNS records. No partial site was
published. R18–R21 cover all 9 Compose consumers, shared function behavior,
negative evidence, import dependency isolation and actual constrained execution.
Keep the 10-second deadline, CPU/memory budgets and epoch/freshness rules unchanged.
No UI or authentication changes. One corrected local/release round before another
bounded preview; do not repeatedly launch while this prerequisite is unresolved.

Repair checkpoint: all 32 focused heartbeat/operations cases pass; the new reader
has 19/19 covered lines. Existing fresh/stale/future/wrong-epoch/malformed/Redis-
unavailable behavior and 30–120 second bounds are preserved. Fresh-interpreter
checks reject application/database imports. Constrained acceptance passed at
2.308 seconds, then 3.807 seconds after final fixture cleanup, below the unchanged
10-second deadline. This is not a direct same-host speedup comparison to the live
23.46-second diagnostic. CI smoke reuses its existing API image for this acceptance
under the same 0.25 CPU/128 MiB, read-only/networkless/no-new-privileges limits.
No timeout/resource/security/design exception was introduced. Current-source full
release/hosted evidence and corrected live verification remain required.

### Cycle 8 — authorized final-image repair

VOL-15 (release blocker): source 667fb93 passes all 120 local gate checks and
19 hosted checks, but the final inspector image fails Grype. Preserved evidence:
`.artifacts/feature110/hosted-sbom-r2`. Deduplicated roots include Python 3.14,
OpenSSL, zlib, pip-wheel and glibc packages in the old pinned base. Repository
dependency scanning passes. Refresh immutable same-vendor builder/runtime pins,
checking the new Python ABI and all binary dependencies before release testing.

VOL-16: the normalized SARIF summary reports no critical findings despite a raw
critical Python finding. Raw scanner exit remains the release authority; inspect
severity normalization and cover numeric critical scores without weakening gates.

R14–R17 cover migration, networkless parser/supervisor boundaries, fresh spool,
resource limits, recovery, exact production-image scan, hosted gates and rollback.
No database/schema or UI change is involved. Owner's continuation explicitly
approves this runtime repair. Deployment remains gated and bounded. The local
image scan precedes expensive release reruns to avoid repeating CI-only discovery.

Cycle 8 validation: registry-resolved amd64 builder ea666e12 and production
3e56a297 both provide Python 3.15.0. The previous cffi 2.0.0 has no compatible
binary wheel; cffi 2.1.1 and Pillow's cp315 wheel were downloaded in the target
builder, hashed and installed with unchanged closed-set/binary-only constraints.
Cryptography's abi3 and the pure-Python wheel hashes remain unchanged.

Actual container acceptance passes PNG/PDF/OGG/MP4, malware rejection, UID 65534,
no-new-privileges, inaccessible signing secrets/supervisor memory, signed spool
and memory bounds (1,084,661,760 bytes peak under 1,610,612,736). Fresh-volume,
terminal permissions, crowded-residue rejection and restart recovery pass.
The production target excludes acceptance code. Grype 0.120.1 (official binary,
verified release SHA-256) with a valid 2026-10-13 database finds zero production
image vulnerabilities. Evidence: `.artifacts/feature110/runtime-repair/`.

VOL-16 reproduced with 8 failing assertions, then repaired ruleId/ruleIndex score
lookup, highest-severity retention and malformed numeric rejection. All 17 adapter
tests pass; reprocessing the original 80 findings now reports 1 critical, 14 high,
30 moderate and 35 low. The 41 isolation tests and 4 unchanged-reference contracts
pass. No ignore, severity floor, resource limit, privilege or screenshot changed.
Remaining: exact-source full and hosted gates, merge, bounded live verification,
and owner acceptance. VOL-07's historical native fault remains disclosed.

### Cycle 7 — hosted dependency findings

The expanded provider audit additionally found oauthlib 3.3.1 (PYSEC-2026-4114),
fixed in 4.0.0. Reviewed upstream changelog: breaking changes affect OAuth server
revocation/validation APIs, not Base2's provider client composition. Cover client
request construction and constant-time PKCE comparisons in credential-free tests.
No OAuth server redesign or live credential flow is introduced. API and Django
fresh audits now report zero findings. The inspector's static closed-set audit
reports zero; installing its platform-specific cffi wheel on WSL Python 3.12
correctly fails the hash guard. Do not replace that unrelated pinned wheel hash:
the actual inspector image is the required installation/runtime proof.

VOL-14 (release blocker): PR #70 hosted pip-audit and SBOM scan failed after the
local 120-check gate passed. Preserved raw/normalized evidence under
`.artifacts/feature110/hosted-pip-audit` and `hosted-sbom`. Deduplicated dependency
families are urllib3 2.7.0, PyJWT 2.13.0, pypdf 6.16.2 and Django 6.1. They affect
HTTP/provider calls, auth/claims, hostile PDF handling and Django request handling.
Include API and provider locks plus the separately hashed inspector dependency.

Upstream PyJWT 2.15.1 wheel was read without installation; `_merge_options` copies
caller options before setting defaults. This independently resolves ambiguity in
GHSA-gvp8-978c-rx2q's empty fix-version field (affected range ends at 2.13.0).
Add a red/green options-reuse regression rather than assuming a version bump is
sufficient. Other findings have same-major fixes listed by both audits. R11–R13
cover lock consistency, auth/negative claims, PDF/provider consumers and source-
bound release validation. No known planning gap for this bounded repair. Keep
visual source unchanged; no audit exclusion or live resource until acceptance.

### Migration verification checkpoint

VOL-13: Tailwind v4 resets `::file-selector-button`, changing the existing
Workspace imports control height by 1px in Chromium and 3px in mobile WebKit.
Retained first failure in `/tmp/f110-migration-workspace.log` (21 passed, 3 failed).
Restore the native v3 control with `all: revert`, inherited font and button
appearance; no snapshot replacement. Focused compact/zoom/WebKit reproduction
passed 6 cases in `/tmp/f110-file-button-repair.log`.

Final shared-source sweep: Operations 22 applicable passed/20 intentional skips,
Media 24 passed/12 intentional skips, Workspace 24 passed, Volcano 69 passed,
Ember compatibility 15 passed and Northstar settings 10 passed. Logs are
`/tmp/f110-final-{operations,media-release,workspace-release,volcano,compatibility,settings-release}.log`.
All existing PNGs are unchanged. Current route captures are retained in
`.artifacts/layout-109/run-1791916009357`; desktop Journal error-state composition
and compact Workspace import geometry were inspected. TypeScript passes, lint
has zero errors and 24 existing warnings, and the all-dependency audit reports
zero vulnerabilities. These checks do not replace coverage or the full release
gate. A shell-loop invocation lost its variables at the launcher boundary before
tests loaded; corrected explicit WSL commands above ran all named suites.

## Cycle 3 — Owner-approved extension (2026-10-13)

Owner confirmed the exact recovered design and instructed future work to build on
it, never silently replace it. Extend original navigation through optional route
data, preserving the no-prop Home behavior and reference hashes. Route changes
must not use Home's section-scroll timers; page movement must not change routes.
Use existing permission-filtered navigation, without changing API authorization.
Retain page-specific context and account controls. Activation, modal isolation,
source binding and all-page coverage remain explicit release blockers until tested.
Budget: one focused unit/type/lint round, one unchanged Home comparison round,
then affected route/state captures. No paid resource or full gate until ready.

| Issue                                   | Cause                                                      | Regression/evidence                                                                                               | Status            |
| --------------------------------------- | ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ----------------- |
| VOL-01 Original side menus replaced     | Home selected SharedLayout/HomeSharedControls              | Original-menu screenshot and DOM contract                                                                         | Open              |
| VOL-02 Gradient and composition missing | New Home branch omitted original wrapper                   | Original Home screenshot/background contract                                                                      | Open              |
| VOL-03 Visual identity unguarded        | Structural tests accepted new design as baseline           | Freeze pre-edit original captures; owner checkpoint                                                               | Open              |
| VOL-04 Other pages need matching design | Generic shared panels not original menus                   | V007–V009 after reference confirmation                                                                            | Pending           |
| VOL-05 Route headings inherit hero size | Original global typography applies outside Home            | `volcano-route-sweep-110`: 16 route cases fail at 144px; scope page typography, preserve Home                     | Repair under test |
| VOL-06 Footer overflows at CSS zoom     | Viewport media query cannot detect reduced container width | `volcano-routes-final-local-110`: two light/200% zoom cases overflow 316px; route-scoped container breakpoints    | Repair under test |
| VOL-07 Native coverage process crash    | Unknown native runtime fault, not an assertion             | `/tmp/f110-frontend-coverage-final.log`: Node v24.20.0 segmentation fault, no terminal summary or coverage report | Release blocker   |

VOL-06 focused repair passed both light/zoom cases in `volcano-zoom-repair-110`;
signup capture inspected, no reference updates. VOL-07 preflight found ~30 GiB
available memory, no matching kernel OOM/segfault entry, and the existing
single-worker/no-concurrent-marking/no-concurrent-recompilation flags were already
in use. Earlier 320-test pass remains historical, not final-source proof. Permit
one safe, same-command diagnostic retry with a separate log; preserve first crash,
and stop the full-suite retry loop if it recurs. Do not treat retry success as a
native-fault resolution or use missing coverage as a pass.

The permitted diagnostic retry completed all 321 tests and generated coverage.
Critical glass/theme coverage is 100% in all four metrics, without changed floors.
VOL-07 remains an unresolved intermittent environment issue; no second retry or
claim of native stability. Committed changed-line coverage and complete release
validation are separate pending checks.

After committing the composition as b5aeb36, real changed-line coverage reported
83.33% (65/78), below the unchanged 90% floor. Missing lines were the keyboard
trap/restoration and route-only scroll action. Added focused regressions exercising
Tab/Shift+Tab, existing inert preservation, cleanup and scroll-without-navigation;
all four route-adapter tests pass. Complete coverage recollection remains required.

Final composition validation at 72f3a1f: 323 frontend tests and all 69 browser
cases passed. Recollected changed-line coverage is 78/78 (100%); critical glass
coverage is 100% in all metrics. VOL-05 and VOL-06 are fixed in this candidate.
The original Home reference hashes are unchanged. VOL-01/02/04 are corrected in
the preview composition, but remain unreleased. VOL-03 has an owner-approved
reference guard and explicit repository preservation policy. VOL-07 remains open.
Do not mark V008–V012 complete based on these synthetic/Chromium-only results.

## Release cycle 4 — shipping and proof alignment

### Cycle 6 — approved dependency migration

VOL-11: v4 sibling spacing moved margins to previous children, shifting Operations
sections. Restore existing integer spacing utilities through the config plugin;
unit checks cover spacing direction, reversal and unchanged glass styles. The
initial fractional static-selector prototype was rejected by v4 before build;
no fractional legacy class is present, so compatibility covers existing integer
utilities only. VOL-12: unitless text leading accumulated one-pixel mobile drift
under fluid root sizes; preserve v3 rem leading. Corrected compact/desktop matrix
passes 6/6 without changing snapshots (`/tmp/f110-leading-repair.log`). Other
independent matrices still require validation; no release claim is made.

Owner approved the broader repair. One registry/audit sweep confirmed braces is
present only through Tailwind 3; same-major updates cover the other findings.
Pinned Axios 1.20.0 and Tailwind/PostCSS 4.3.3, updated affected transitive packages
with lifecycle scripts disabled. All-dependency npm audit now reports zero.
The expected red build proved the old PostCSS plugin is incompatible with v4.
The dedicated plugin plus retained JavaScript config, unlayered utilities and
explicit v3 border/placeholder/cursor compatibility pass the original two-viewport
comparison (all eight frozen PNGs, no replacements). Compiler/lockfile sources now
join Operations/Media evidence bindings. Broader profile and state checks remain.
Budget: one no-update shared-matrix sweep, batch any compatibility regressions,
then current coverage and full gate. No snapshot updates are authorized by this
dependency migration. Evidence: `/tmp/f110-audit-after.log`,
`/tmp/f110-tailwind-red.log`, `/tmp/f110-tailwind-reference.log`.

### Cycle 5 — dependency release blocker

Round 2 completed all 120 checks on a603bfd: 119 passed, one audit failure.
VOL-08/09 now pass in the full gate. VOL-10 is dependency/advisory drift since the
older lockfile: 11 affected dependency entries, grouped into axios, brace expansion,
braces/Tailwind build chain, PostCSS selector parser, source-map-js and undici.
Evidence: `20261013T175414Z-636889/frontend-production-audit.log`.
Registry verification: braces 3.0.3 is still latest; Tailwind 3 latest is 3.4.19;
Axios latest is 1.20.0. Upstream reviewed advisory
https://github.com/advisories/GHSA-vfj7-8cjw-p6xm lists no patched braces release.
The audit proposes a breaking Tailwind 4 update, not an ordinary safe patch.

Adjacent consumers include PostCSS compilation, generated site profiles, Storybook,
coverage/source-map processing and test DOM networking. Proposed R07–R10 cover
their compatibility, security and screenshot acceptance. No known planning gap
remains for that proposed batch, but the broader migration requires owner direction.
Do not weaken the all-dependency audit, replace approved screenshots, or label the
candidate release-ready. Preserve exact candidate, private evidence and rollback.
VOL-07 also recurred as incomplete frontend output; the permitted single retry
passed, but the first exit remains a disclosed unresolved environment issue.

VOL-08 focused checks pass on desktop/tablet/mobile (3/3); VOL-09 contract plus
negative bounds pass (6/6). The first focused browser invocation used repo root
instead of react-app and failed loading axe before any test; corrected working
directory ran the actual regression. Evidence: `/tmp/f110-gate-repair-correct-cwd.log`.
Final composition validation also passed 323 frontend cases, 69 unchanged-reference
and route cases, and exact-source repetitions. Changed executable coverage is
78/78; critical UI metrics remain 100%. VOL-07 has not recurred in these completed
runs but remains a disclosed environment risk, not a claim of a native-runtime fix.

Complete gate round 1 (`20261013T174245Z-616450`) failed with two independent
fixture/evidence-contract findings; dependent checks are not passed. VOL-08: the
legacy interaction test clicks Search after Escape correctly closes its menu;
explicitly assert closed, reopen and assert open before clicking. VOL-09: the
reviewed enlarged-text page plus restored footer is 5813px, exceeding an old
5000px screenshot-height assumption. Permit 6000px only for this named capture,
retain all other bounds and the existing 12.8M decoded-pixel maximum; add negative
oversize cases. No original Home PNG, comparison threshold, coverage floor or
product security rule changes. Revalidate both focused contracts before rerunning
the complete gate. This is the only known repair batch from the completed sweep.

Release discovery also found undersized original edge tabs and header theme control
on touch landscape. Route-only coarse-pointer minimum targets now preserve their
design while meeting 44px usability. Corrected Operations matrix: 22 passed,
20 intentional project/state skips; 35 captures. Media: 24 passed, 12 intentional
project/state skips. Workspace shipping-layout matrix: 24 passed, 48 captures.
Reviewed actual compact, desktop, enlarged-text, RTL, light and modal captures.
No original Home reference changed. Live assertions now test original menus and
modal palette instead of the rejected generic panels. These are local synthetic
results, not a live-deployment or final-owner acceptance claim.

Docker/Compose and Operations/Media/restricted release matrices now select the
approved Volcano build. The complete gate has mandatory reference and route checks.
Existing Feature 109 checks remain as legacy fallback coverage, not production
proof. New shared component/style sources join review dependency manifests.

Operations discovery (desktop/compact, six cases) found a closed command panel
still contributing off-screen geometry; render it display:none only in its closed
route-shell state, preserving the Home reference. Compact screenshots also showed
account-button wrapping: scoped nowrap/padding fixes retain the original header.
Media discovery passed three cases; three screenshot mismatches reflect intentional
shell changes. Actual detail and Operations compact captures inspected before
baseline refresh; no original Home baseline will be changed. Remaining matrices
must check accessibility, touch targets, focus and recovery before acceptance.

The expanded round passed 67 cases and failed the two zoom cases. Guest route
guards and every unchanged Home capture passed. Full frontend suite passed all
320 tests after correcting the helper's implicit status role. Coverage preflight
found the new AppShell activation branch uncovered (critical lines 99.69%, floor
100%); added a real AppShell activation regression, passing focused checks.
Preflight other-surface reports are not current-source release evidence, and its
changed-line comparison excluded uncommitted edits: final clean-source coverage
is still required. No floors have been changed.

Route adapter focused round: initial guest fixture omitted the accounts module;
fixed the fixture explicitly (no permission logic weakened). 19 focused tests,
TypeScript and lint pass. All eight Home images still match in the first route
sweep; 16 route checks correctly fail on one shared typography cause. No snapshot
baseline changed and no deployment performed.
