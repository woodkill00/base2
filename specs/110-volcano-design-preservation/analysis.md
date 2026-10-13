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
