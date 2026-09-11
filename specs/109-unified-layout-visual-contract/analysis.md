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

Ready to begin T001. Implementation, baseline approval and live acceptance are pending.
