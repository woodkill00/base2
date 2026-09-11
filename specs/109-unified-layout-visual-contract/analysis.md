# Tasks → analysis → refinement

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
