# Tasks and issue ledger

- [x] T001 Preserve live failure evidence and verify teardown.
- [x] T002 Map shared consumers and refine this bounded repair.
- [x] T003 Add interceptor/session/context regressions, then implement explicit reauth.
- [x] T004 Add shared accessible notice and tests for safe return and lifecycle.
- [x] T005 Fix Google frame rendering and add unit plus iframe/browser regression.
- [x] T006 Update live acceptance to exercise explicit reauth and manual action retry.
- [ ] T007 Run focused tests, coverage review, responsive visuals and adjacent consumers.
- [ ] T008 Run complete gate and CI after review; request merge/new trial authority.
- [ ] T009 Run approved automated-only acceptance, inspect evidence and verify teardown.

## Issues

1. High, product: a recent-auth 401 is refreshed/retried then invalidates a valid
   session. Reproduction: settings privacy export after document navigation.
   Evidence: /tmp/base2-f118-live-browser.log; browser acceptance 13 pass/1 fail.
   Missing completed export also explains runtime verifier failure, not a separate
   confirmed worker defect. Status: repair pending.
2. Medium, visual: Google's dark button has a white iframe canvas under inherited
   dark color-scheme. Live google-ready-login.png and
   google-frame-light-context-diagnostic.png demonstrate the isolated correction.
   Status: repair pending.

Evidence root: /home/woodkill/.local/state/base2-full-preview/base2-full-20261020-095030.
That trial is destroyed; inventory confirmed zero droplets and managed DNS records.
No additional trial is authorized.

Analysis 1: distinguish freshness from expiry; never weaken server freshness.
Analysis 2: add stale response, retry-marked response, explicit authentication
failure/MFA, safe return, adjacent consumers and real iframe rendering tests.
No known design gap remains; verification and implementation tasks remain open.

## Repair verification

Regression-first run reproduced three failing assertions. Interceptor/context/
notice/Google focused suite now passes 40 tests. Full frontend run passes 441
tests in 92 files, 83.38% lines, 73.60% branches:
`/tmp/base2-f119-frontend-final.log`. Lint has zero errors and 24 existing
declaration warnings.

Google fixture browser run: seven passed, including actual isolated frames at
390/1440 widths and dark/light preferences; mobile capture inspected.
Account journeys: 54 passed across Chromium/Firefox/WebKit before final notice
focus refinement. Final focused freshness flow: 12 passed across all three
engines, both widths/preferences, including viewport/focus and explicit retry.
Final freshness evidence: `.artifacts/layout-109/run-1792491982512/`.
Mobile screenshot inspected; notice is visible without changing the Volcano
menus or composition. Real provider rendering still requires a new approved trial.

Analysis 3: browser accessibility exposed a skip-link ordering interaction from
placing the notice above the entire shell. Moved it into each shell's main content.
Analysis 4: full unit sweep found 21 cascading standalone-layout failures.
A dedicated boolean-only notice context fixed the dependency without weakening
the strict authentication hook. Full frontend rerun is green; original failed
run remains `/tmp/base2-f119-frontend.log`.

Complete release gate, exact-source coverage policy, final broad visuals/CI and
new live acceptance remain pending. No baselines changed; no new paid trial run.

## Final evidence-dependency repair

First complete gate on dc31607: 114 passed, 2 failed, 16 dependent checks blocked.
Evidence: `.artifacts/complete-gate/20261020T103033Z-2755546/result.json`.
Both failures were legitimate source-bound review invalidation after the AppShell
change: operations visual manifest and media review ancestry. Original failures
are retained; blocked checks are not passes.

Analysis 5: preserve Operations' already-localized 403 freshness handling rather
than emit a duplicate global notice. The new shared path applies only to exact
401 freshness responses. Focused client regression: 17 passed.
Bind both visual review surfaces to the new notice/context/auth dependencies.
Supported media renewal passed 24 tests with 12 intentional exclusions and
unchanged references. Operations comparison passed 22 tests with 20 intentional
exclusions; a dedicated capture run retained review images outside the shared
test-results directory at `.artifacts/f119-operations-review/`. Media desktop
and Operations fresh-auth recovery captures were inspected. No snapshots changed.

Type checking passes. Changed-line policy before the final 401-only refinement
was 95.83% against 90%; the complete gate must regenerate final coverage.
The broad optional format check reports 14 pre-existing unchanged files at
`/tmp/base2-f119-format.log`; changed sources pass formatting and commit hooks.
Final source release/CI and new paid trial remain uncompleted, not waived.
