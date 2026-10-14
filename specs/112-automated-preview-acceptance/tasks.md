# Tasks

- [x] T001 Inspect current source, evidence, live tests and approved baselines.
- [x] T002 Map coverage gaps and run tasks/analysis/additional-tasks review.
- [x] T003 Add fixed live acceptance inventory and fail-closed result evaluation tests.
- [x] T004 Integrate safe source-bound reporter; partial/filtered/skipped/flaky runs fail.
- [x] T005 Require prerequisites before launch, without logging credential values.
- [x] T006 Add reusable-owner login and logout verification without account mutation.
- [x] T007 Add live approved-reference visual comparisons without baseline updates.
- [x] T008 Tighten real public-content response verification; retain known detail 404 states.
- [x] T009 Integrate contract regressions into the normal release gate.
- [x] T010 Document coverage, live execution requirements and lifecycle separation.
- [x] T011 Repeat analysis; validate targeted tests, coverage and browser collection.
- [ ] T012 Run complete local gate once ready and record honest residual blockers.

Additional analysis tasks: never count a screenshot as comparison; reject retries
even if a later attempt passes; do not mutate reusable owner preferences; separate
mocked visual evidence from live backend evidence; do not infer cleanup from browser
success; preserve missing prerequisites as blocked, not skipped-success.
