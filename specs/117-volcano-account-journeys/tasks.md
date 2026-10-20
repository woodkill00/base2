# Tasks and acceptance

- [x] T001 Audit active auth pages, API client, context, guards and provider adapter.
- [x] T002 Confirm parent PR82 remains open; create stacked feature branch.
- [x] T003 Run tasks → analysis → refined tasks → analysis; record security blocker.
- [x] T004 Obtain owner direction on including the session-storage migration (owner: “yes include it”).
- [x] T005 Specify migration/bootstrap/rollback contract and repeat analysis (cycle 3; migration.md).
- [x] T006 Add failing session, stale response, tab/logout and return-URL regressions.
- [x] T007 Implement approved session migration and purge legacy credentials safely.
- [x] T008 Audit canonical verification model/service and define resend API contract.
- [x] T009 Test neutral responses, account/IP limits, concurrent requests, exhausted
      mail budget, already-verified/unknown users and adapter failure without real mail.
- [x] T010 Implement supported verification recovery route and typed frontend adapter.
- [x] T011 Extract shared Volcano auth composition without replacing design sources.
- [x] T012 Add Caps Lock guidance and accessible live password requirements.
- [x] T013 Guard duplicate/overlapping email, Google and MFA submissions; retain
      nonce expiry, cancellation, processing and explicit retry behavior.
- [x] T014 Replace reset/verification timed redirects with persistent success actions.
- [x] T015 Add invalid/expired-link recovery, inbox guidance and server-bound resend state.
- [x] T016 Correct method-neutral MFA copy and test code paste/recovery/expiry.
- [x] T017 Make logout success/failure explicit; clear private UI and prevent late
      auth responses, other tabs or browser Back from restoring stale authenticated UI.
- [x] T018 Add safe session-expiry explanation and bounded internal return navigation.
- [x] T019 Audit all root E2E, frontend, live helpers and generated profile consumers.
- [x] T020 Validate keyboard, screen-reader announcements, loading/error/disabled states,
      mobile/desktop, zoom, reduced motion, preferences and screenshot review.
- [x] T021 Run restricted-role integration and server-boundary/security regressions.
- [x] T022 Review changed-line and critical-component coverage; preserve all floors.
- [ ] T023 Run exact-source stability prerequisites and complete release gate.
- [ ] T024 Record limitations, source-bound results and rollback; publish/observe CI
      within applicable authority. Paid/live trial requires a fresh bounded approval.
- [ ] T025 Validate verification StrictMode single-use behavior and hosted cookie
      prerequisites through the final source-bound release gate (targeted tests passed).
- [x] T026 Verify server-derived navigation permissions using the restricted runtime
      role; do not reintroduce browser-storage permission or credential shortcuts.
- [ ] T027 Execute the separately authorized live acceptance trial only after CI;
      collect visual/functional evidence, verify teardown and report residual risks.
- [ ] T028 Repair the live empty-form request inventory for verified session bootstrap;
      reproduce the mismatch, test actual document navigation offline, preserve exact
      request counts and rerun the required gates before the approved live trial.

## Current bounded batch

Session and browser fixtures are implemented. Cross-tab logout and secure-cookie
deployment preflight passed targeted checks; account switching, final adjacent
consumer coverage and restricted-role acceptance still need final review.

Latest complete frontend working-tree run: 424 tests across 91 files passed;
83.23% line coverage and 100% GlassInput coverage. Subsequent focused MFA paste,
expiry/restart, Caps Lock and verification checks: 11 passed. Lint: zero errors,
24 warnings. Browser results: auth 39 passed, account 21 passed, operations
22 passed/20 intentional matrix skips, media 24 passed/12 intentional matrix
skips. See analysis.md for source timing and evidence; these are not final
exact-source release receipts. Complete backend coverage is in progress.
No complete release gate or deployment performed. Parent PR82 remains open.

Candidate preparation: workspace release 24 passed; real browser Back after
logout passed in three engines. Restricted-role acceptance including new resend
concurrency and navigation projection passed after correcting the synthetic
frontend-origin fixture. Tasks 019–027 remain gated on final-source evidence,
publication/approvals and live acceptance; do not equate implementation with
release completion.
