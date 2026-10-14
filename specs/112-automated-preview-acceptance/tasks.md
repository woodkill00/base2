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
- [x] T012 Final candidate c12ebde passed all 122 complete-gate checks; permitted native retry and live/CI prerequisites recorded explicitly.

Additional analysis tasks: never count a screenshot as comparison; reject retries
even if a later attempt passes; do not mutate reusable owner preferences; separate
mocked visual evidence from live backend evidence; do not infer cleanup from browser
success; preserve missing prerequisites as blocked, not skipped-success.

## Authorized publication and live closeout

- [x] T013 Remove redundant focused coverage reporting; retain mandatory full API coverage and regression-test its selection.
- [x] T014 Connect validated private owner/receipt inputs to the existing browser entrypoint, with negative tests.
- [x] T018 Reject stale receipts using the current integrity-checked durable lease before reading owner credentials; test destroyed, missing, tampered, source/address drift and credential-read ordering.
- [ ] T015 Validate candidate, publish PR, pass CI, preserve history on merge and check post-merge CI.
- [ ] T016 Launch one existing 60-minute bounded preview, run full automated acceptance without bypasses.
- [ ] T017 Perform exact-identity teardown, verify retained receipt and inventory, record failures and residual risks.

Analysis: user authorized this continuation on 2026-10-15. No new provider, account,
design, broad token access or extended lease. Limit diagnostic repetitions to three
focused runs after relevant correction, then reassess. One full gate once code is
ready. Existing native-crash evidence stays retained; removing redundant reporting
does not prove the interpreter's root cause fixed.
