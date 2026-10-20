# Analysis and issue ledger

## Cycle 1: functional gaps

Reviewed AuthContext.js, apiClient.js, Navigation.js, ProtectedRoute.jsx,
BoundGoogleLogin.jsx, reset/verify/forgot pages and auth/users routes.
Reset and verification redirect after two seconds; Google completion exposes
retry while the parent promise is pending; MFA assumes a password was accepted.
The frontend resendVerification method targets an absent backend route.
Logout swallows network errors and protected UI derives authentication from
persisted user metadata without asynchronous session verification.

## Cycle 2: adjacent consumers and trust boundaries

Expanded tasks to include refresh/bootstrap, duplicate callbacks, logout racing
refresh/sign-in, cross-tab invalidation, Back navigation, token-bearing URLs,
real rate limits and mail budget, root E2E and live selectors. Keep existing
provider nonce security and staging-only policy. UI countdowns cannot replace
server limits. A request acceptance is not proof of inbox delivery.

## Blocking finding

S117-01: active AuthContext.js and apiClient.js persist/read access tokens under
localStorage token and may persist refresh_token. Full auth payloads are also
stored under user. This conflicts with constitution 2.IV. It is a code finding,
not evidence of exfiltration or a breached account. No secrets were read.
Fixing it affects session bootstrapping, API authorization and compatibility,
so obtain scope direction before making that architectural migration.

| ID      | Severity/type        | Reproduction/evidence                                       | Regression and disposition                                     |
| ------- | -------------------- | ----------------------------------------------------------- | -------------------------------------------------------------- |
| S117-01 | high/security design | AuthContext + apiClient storage calls                       | persistence/bootstrap/refresh/tab tests; scope decision needed |
| U117-02 | functional           | resendVerification targets absent /auth/resend-verification | real route/limit/mail tests; planned                           |
| U117-03 | usability            | reset/verify success expires after 2s                       | no forced navigation; planned                                  |
| U117-04 | concurrency/UX       | BoundGoogleLogin.finish enables retry before completion     | pending/reentry/late-result tests; planned                     |
| U117-05 | security/UX          | logout catches and ignores server errors                    | explicit partial outcome, tab/race/history tests; planned      |
| U117-06 | copy                 | MFA says Password accepted after Google                     | both auth methods; planned                                     |

Original planning status: blocked on T004, not gap-free or implementation-ready. No tests,
merges, deployments, account mutations or provider actions performed in this
planning batch. Parent PR82 implementation/CI evidence remains historical and
does not validate the proposed Feature117 changes.

## Cycle 3: approved migration and additional contracts

Owner approved S117-01 scope. Preserve the existing cookie/CSRF boundary; browser
clients must not use JSON refresh-token fallback. In-memory access tokens require
verified bootstrap, synchronous invalidation epochs, stale-response rejection,
cross-tab logout and legacy-storage purge. Refresh-cookie rotation across tabs
needs serialization and independent backend tests; per-tab single-flight alone
is insufficient. Failed logout must block automatic cookie bootstrap until an
explicit new sign-in. Stateless access JWTs are not instantly revoked by refresh
logout: document this limitation rather than claiming global revocation.

Additional acceptance: test denied browser storage, refresh/retry after logout,
StrictMode bootstrap cleanup, delayed login after logout, empty refresh payload,
untrusted persisted user data, cookie-mode prerequisites, and logout repository
failure. Audit API consumer fixtures instead of trusting localStorage mocks.

## Implementation batch 1 results

Implemented memory-only credentials, legacy cleanup, verified-cookie bootstrap,
invalidation epochs, serialized session operations, local logout barrier and
server logout failure reporting. UI profile fixtures now mock verified restore
rather than authenticating via localStorage. Login waits for session readiness.

Preserved first failures: the initial targeted runner invocation supplied conflicting
coverage flags (no tests ran); the supported test:watch run mode corrected it.
Consumer sweep found 18 failing tests / 14 passes: old persisted-profile fixtures,
missing access credentials in success fixtures and bootstrap timing assumptions.
After fixture repair, two failures remained; reassessment found Settings tests
mounted outside the real ProtectedRoute and login could be submitted while session
bootstrap was pending. Corrected the fixture topology and disabled premature
login; the next targeted sweep passed all 61 tests.

Complete frontend unit/coverage run: 404 tests / 87 files passed. Coverage:
statements 81.03%, branches 72.49%, functions 78.35%, lines 82.57% (existing
floors unchanged). Nine backend cookie/CSRF/logout tests passed. Lint exited zero
with 24 warnings and no errors. Diff whitespace validation passed.

Evidence: `.artifacts/feature117-session-batch1/` (sanitized test logs). These are
working-tree test results, NOT an exact-source full-gate receipt. Full release
gate count 0; deployment count 0; external provider/mail actions 0. Browser
fixture migration, browser/visual acceptance, changed-line coverage review,
remaining journey work and full release gate are pending. No claim of complete
Feature117 acceptance or absence of unknown defects.

## Cycle 4: account journeys and adjacent consumers

Implemented the shared auth frame preserving existing Volcano geometry, persistent
reset/verification success actions, Caps Lock and password guidance, neutral resend
recovery, pending Google guards, safe return paths, and cross-tab account version
invalidation. Browser fixtures now receive synthetic authenticated server responses
instead of trusting persisted profiles. Live helper bearer values remain only in
the test process. Server navigation permissions derive from active membership;
they are display hints and do not replace server authorization.

New findings and dispositions:

| ID      | Severity/type                | Reproduction/evidence                                        | Regression and disposition                                                                                                                       |
| ------- | ---------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| U117-07 | visual/shared component      | first verification screenshots showed white toast on Volcano | theme tokens, safe-area positioning, dismiss target; toast unit + browser color assertions; fresh mobile WebKit capture reviewed                 |
| U117-08 | functional/one-use operation | StrictMode produced two verification requests                | failing regression preserved in `/tmp/base2-f117-verify-strict-repro.log`; mounted-page promise reuse; four verification tests pass after repair |
| S117-09 | deployment prerequisite      | memory-only sessions require secure refresh cookies          | hosted settings reject disabled cookie mode or insecure cookies; settings regression passed                                                      |
| S117-10 | consumer trust boundary      | live fixture depended on browser-stored permission hints     | server projects allowlisted current membership permissions; six focused regressions; broader integration remains required                        |

Current working-tree evidence (not a release receipt): 39 auth journey browser
checks passed on Chromium/Firefox/WebKit; fresh mobile verification screenshot
reviewed at `.artifacts/layout-109/run-1792449566086/`. Account/settings suite:
21 passed. Operations: 22 passed, 20 intentional matrix skips; error/recovery
states run on compact/desktop Chromium plus desktop Firefox/WebKit, while
geometry runs across the full matrix. Backend settings/navigation/logout/recovery:
182 passed; additional recovery service tests: 12 passed. Earlier journey sweep:
120 passed, before the latest shared-frame/toast changes; do not reuse as exact
final-source evidence. Full frontend coverage is in progress.

Preserve `/tmp/base2-f117-*` logs into durable ignored evidence at batch closeout.
No paid resource, real mail or provider action performed. Full release gate count
0, deployment count 0. Remaining: MFA/recovery acceptance, current full coverage,
remaining consumer/restricted-role suites, gate registration, exact-source gate,
CI and separately authorized bounded live acceptance. No all-green claim.

## Cycle 5: real boundaries and final candidate preparation

Complete frontend coverage: 424 passed, 91 files; 81.73% statements, 73.34%
branches, 79.17% functions, 83.23% lines. GlassInput retained 100% across all
metrics. Complete API coverage runner passed all partitions. Subsequent session
replacement regression invalidates earlier-account epochs on explicit sign-in;
35 focused session/auth tests passed. This later change still requires the final
full gate rather than reusing the earlier frontend receipt.

## Cycle 6: complete-gate integration repair

Candidate `80f635a` completed the first gate in approximately 14 minutes.
Evidence: `.artifacts/complete-gate/20261019T225723Z-1986394/result.json`.
Five checks failed, grouped into four causes: cwd-relative axe loading affected
both dedicated auth and generic layout discovery; the new auth suite also needed
exclusion from the generic layout configuration; Google proof omitted the new
bootstrap request; exact-head repetition evidence and the media review source
binding needed renewal (the latter follows a changed synthetic session fixture).
Dependent blocked checks were not counted as passes.

Repair: import axe through module resolution; dedicate the auth suite to its
required Volcano-configured gate entry; explicitly mock and assert exactly one
bootstrap request in Google proof. Root-invoked auth suite now passes 42 checks,
Google proof passes two, and generic layout discovery succeeds. Save fresh media
captures alongside unchanged baseline comparisons and use the existing guarded
review-renewal helper. Generate exact-head repetitions before the next gate.

The first gate also passed 427 frontend unit tests (83.31% line coverage), all
73 Volcano preservation checks, 120 user journeys and restricted database
acceptance. These successes do not make the failed gate acceptable. Full-gate
count: 1; deployment count: 0. No baselines changed, no live-resource authority
assumed, and no failure receipts edited.

Media renewal on clean repair commit `e898f45` completed: 24 passed, 12
intentional exclusions, zero flaky/unexpected cases, unchanged reference image
inventory. Current captures were retained and representative desktop, compact,
zoomed picker and light-detail captures inspected. The supported renewal helper
updated only the review source binding; no reference images were rewritten.
Parent merge and a new bounded live preview remain awaiting owner approval.

## Cycle 7: complete evidence-binding audit

Second gate on `ae83bac` finished with one failed check:
`operations-visual-contract`. Its source hashes predated Navigation's explicit
logout result and the operations session fixture migration. Other independent
checks passed; dependent blocked checks were not promoted to passes. Evidence:
`.artifacts/complete-gate/20261019T231455Z-2028132/result.json`.

Audited remaining source-bound visual consumers together. Operations needed a
fixed manifest renewal; media was current, workspace evidence is generated from
current sources. Added retained current operations screenshots, ran the actual
matrix (22 passed, 20 deliberate state-matrix exclusions), inspected desktop,
compact and unavailable-data captures, and used the supported evidence builder.
The regenerated manifest changes exactly two source hashes; all 35 approved
image hashes and the runner receipt remain unchanged. Eleven visual-manifest
contract tests passed. Captures: `.artifacts/feature117-batch2/operations-captures/`.

A draft-push attempt during the gate triggered the normal local pre-push suite;
that attempt and its owned child processes were stopped to avoid overlapping
heavy work. No push occurred and no hook was bypassed. Retry publication only
after the complete gate finishes, so the supported hook can reuse exact evidence.
Full-gate attempts so far: 2. Cloud deployments/provider mail actions: 0.

Disposable PostgreSQL acceptance first failed closed on resend (503): the old
fixture had no trusted FRONTEND_URL. Added only `https://example.test` to its
environment; missing-origin rejection remains regression tested. Second trial
passed restricted-role registration/permission projection, real Redis resend
limits including concurrent requests (one 202, one 429), recovery, replay,
password rotation/revocation, migrations and RLS. Temporary containers were
verified absent. No real delivery or reusable-account mutation occurred.

Settings release: 10 passed. Expanded auth-browser accessibility run: 39 passed,
three new recovery cases failed on one ambiguous `status` locator shared with
the shell output. Scoped the locator to the form; all three passed on rerun.
Fresh accepted/recovery screenshot reviewed (Chromium, light preference, mobile):
`.artifacts/layout-109/run-1792450522509/`. No baseline changes or suppressed
accessibility findings. Required browser check added to the complete gate with
a no-retry contract test. Full gate and live deployment remain outstanding.

## Cycle 8 — pre-deployment request inventory

PRs #82 and #83 were merged with history preserved after all 20 checks passed.
Merged source `9e5174b10a67266329bbe81e9878862722bc67ea` has the exact tree of
the 132-check passing candidate `67b737c`. No paid resource was created.

The live-preflight sweep found test-fixture drift: the empty-form acceptance
inventory still expected only Google preparation, omitting one verified
refresh-cookie bootstrap per full document navigation. The product must retain
that secure bootstrap. Reproduction: `/tmp/base2-f117-bootstrap-repro.log`;
the new contract assertion fails against the old live fixture.

T028 fixes the exact request multiset (two document bootstraps, one Google
challenge when enabled), not a broad exclusion. Empty submissions must still
produce zero extra requests. A real provider-free browser regression exercises
signup then login navigation and rejects missing/extra requests. No credential,
provider, design or runtime behavior changes. Required focused contract/browser
checks precede clean-source stability and full release validation. The merged
gate was stopped before editing to avoid testing mutable inputs.
Focused validation: 19 contract tests and three browser tests passed. The first
browser launch was blocked by an orphaned preview listener from the stopped
gate; its exact owned process tree was terminated before the successful rerun.
Evidence: `/tmp/base2-f117-bootstrap-contract.log`,
`/tmp/base2-f117-bootstrap-browser.log` and
`/tmp/base2-f117-bootstrap-browser-r2.log`. No known blocking scope gaps remain;
final-source gate/CI, follow-up merge and live acceptance remain outstanding.
