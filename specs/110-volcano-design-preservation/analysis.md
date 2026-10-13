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
