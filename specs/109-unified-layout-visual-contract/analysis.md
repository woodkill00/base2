# Tasks → analysis → refinement

## Cycle 7 — Complete-gate findings

The exact-source gate at 0a6510e found stale Operations and Media visual review
bindings after AppShell changed, plus the critical-glass coverage floor (100%
lines/statements/functions and 99% branches). Changed-line coverage passed at
94.95%; do not lower either floor. Refine T022/T024/T025: exercise routed shared
mode, resize observer measurements, drawer events and all filtering branches;
rerun and visually inspect the existing Operations/Media capture matrices before
regenerating their source bindings. Keep original failed gate evidence. No live
launch while these required checks fail; rerun focused checks before a new gate.

Enabled-layout Media browser checks additionally found stale modal-isolation
selectors and a 20px footer touch target. A failing unit regression covers shared
header/rail/footer isolation; repair the selector and give footer links 44px targets.
Update sticky-header assertions to the single shared header frame, not the removed
duplicate bars. Increase shared heading-selector specificity to prevent lazy-loaded
Media CSS from restoring oversized page titles; cover authorized routes too.
Visual evidence bindings now include shared CSS, route policy, profile and runtime.

The refreshed capture dimension contract caught genuine 200%-text reflow failure:
viewport-only rail breakpoints squeezed Operations cards into single-letter
columns. Keep the 5000px capture ceiling. Use an 80rem named container query and
the same measured-width/root-font threshold for drawer behavior, including resize
and font changes. Add real-browser large-text drawer visibility plus a unit case
for font/container changes; rerun affected matrices before accepting those captures.

## Cycle 6 — Release integration and keyboard review

Batch scope: T009/T011/T017/T019/T020/T023/T024. Restore Home controls and
rich footer through shared slots without the legacy delayed scroll snapping.
Resolve legacy TypeScript declarations against actual runtime shims. Test drawer
resize focus and closed-details keyboard exclusion in real browsers. Enable the
shared layout explicitly in both Compose build paths, retaining a build-time
rollback switch. Add source-bound evidence and required release checks; do not
infer final owner visual acceptance from automation. Budget: one all-page sweep,
one focused cross-browser diagnostic batch, fixes before affected reruns, then
the complete gate only when prerequisites are met. No paid launch during repairs.

## Cycle 5 — All-page direction and route-family integration

The owner explicitly directed completion across all pages after the prototype
handoff. Proceed with the remaining page integrations under the existing opt-in
flag; this direction does not assert screenshot acceptance or authorize deployment.
AppShell route-policy resolution and PublicShell delegation cover page families
without duplicating layout code. Preserve all route/permission checks and verify
actual authenticated destinations as well as guest redirects, not merely the
presence of a shell on a redirected page. T014–T016 integration is implemented;
their complete functional/release acceptance remains open.

Review caught inherited giant heading sizes: add a maximum page-title size check
alongside body-overflow checks. Enabled-module and permission checks both govern
shortcuts, tested independently; default-profile tests must explicitly select
accounts enablement rather than assume it. Test/report fixtures retain disabled
and service-error semantics honestly. No synthetic response proves live API success.

## Cycle 1 — Scope and structural coverage

Findings from inspected shells: three competing structures, no right slot in AppShell,
public shell omissions and duplicate-global-navigation risk. A generic "restyle pages"
task would not prevent recurrence. Resolved in T001–T011 with route inventory, explicit
policy, slot contract, consolidation and failing tests. Guest/auth omissions cannot be
assumed approved (T003/T014). Third-party admin surfaces excluded explicitly.

## Cycle 2 — Verification and rollout gaps

Review found insufficient coverage for nested/locale/module routes, keyboard and touch
scrolling, breakpoint edges, errors/long content, theme compatibility, immutable retry
artifacts and owner review. Refined T004/T009/T012/T017/T019–T023 and the acceptance
contract. Added representative approval hold T013 before rollout, negative controls
T021, source-bound baseline review T022 and final separate owner decision T027.
Added exact-head stability preflight T024 to avoid the Feature 108 wasted full-gate
attempt; existing security/release checks remain mandatory. Rollback and bounded
teardown are explicit T026/T028, not implied by a passing screenshot.

## Cycle 3 — Final plan audit

Check sequential dependencies, unique IDs, complete FR/task coverage, test-first
ordering, defined scope and explicit acceptance holds with `validate_plan.py`.
The validator caught an omitted T016 reference in FR-002's traceability row;
the mapping was corrected and validation rerun successfully. Five validator tests
cover valid planning, invalid dependencies, duplicate IDs, false completion and
missing traceability. These tests check plan consistency, not rendered appearance.
No known blocking omission remains in the planning scope. This is not proof that
implementation will have no defects. Unresolved design preferences are represented
as explicit approval tasks, not silently resolved or claimed completed.

## Cycle 4 — Prototype evidence and remaining acceptance

Implementation is underway; see `progress.md`. New browser checks exposed hidden
Home section clipping caused by legacy viewport selectors, then a decorative tab
extending beyond its card. Corrected the shared-container rules and tab position;
retained failures and added section-level geometry checks. Type validation also
found new React 18 inert/React type-version mismatches and test query typing errors;
corrected them without weakening the check. Legacy type-support failures remain.

Refine T008/T011 to preserve complete Home palette, movement, utility and footer
behavior before replacing the default layout. Refine T009/T012 for resize focus,
route transitions and actual functional/error states. T019 must reject reused
attempt directories and bind screenshot readiness and exact source; distinct
manual attempt names alone do not enforce immutability. T024 must resolve or
formally classify the existing global typecheck failures. These remain explicit
open items; no full acceptance or zero-gap implementation claim is made.

## Cycle 8 — Live acceptance alignment

T027 preflight found a stale live-only assertion expecting the removed floating
Home dialog. The intended palette is now a labelled region inside the shared
context rail. Update the live assertion to that contract, retaining visibility,
Escape, geometry and disabled privileged-action checks. Extend the same supported
live suite with 22 guest paths at mobile/desktop widths and shared-shell checks on
the real signup-to-Dashboard and nine Settings flows. Do not confuse expected
permission denials or restricted media with successful privileged workflows.
Typecheck precedes live execution; capture failures without retries or baseline
rewrites. This is test-only refinement, not a change to the deployed application.
