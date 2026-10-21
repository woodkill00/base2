# Tasks and issue ledger

- [x] T001 Preserve live failure evidence and verify teardown.
- [x] T002 Map shared consumers and refine this bounded repair.
- [x] T003 Add interceptor/session/context regressions, then implement explicit reauth.
- [x] T004 Add shared accessible notice and tests for safe return and lifecycle.
- [x] T005 Fix Google frame rendering and add unit plus iframe/browser regression.
- [x] T006 Update live acceptance to exercise explicit reauth and manual action retry.
- [x] T007 Run focused tests, coverage review, responsive visuals and adjacent consumers.
- [x] T008 Run complete gate and CI after review; request merge/new trial authority.
- [ ] T009 Run approved automated-only acceptance, inspect evidence and verify teardown.
- [x] T010 Reproduce and repair live audit-window assertion ordering, preserving the five-event UI.
- [ ] T011 Validate and publish the test-only follow-up; obtain fresh authority for a new live trial.
- [x] T012 Repair newly reported dependency findings across API, isolated decoder and frontend locks.
- [ ] T013 Verify hash-bound decoder installation, media compatibility, dependency audits and full release gate.
- [ ] T014 Publish the dependency repair and merge PR 87 only after all CI checks pass; no paid trial.

## October 21 dependency repair batch

Owner approved expanding PR 87 beyond its test-only scope to repair dependency
audit blockers. CI run 39560323523 reports follow-redirects and Vite high findings,
plus Certifi and Pillow findings. Other PR checks passed. Raw evidence is retained
under `.artifacts/pr87-security/`. Do not suppress advisories or weaken gates.

Analysis 7: Pillow exists both in the API lock and hash-bound Python 3.15 isolated
inspector. Update both; retain immutable images, network isolation and hashes.
Check derivative generation, hostile-media rejection and inspector attestation.
Frontend changes need production build, Storybook and existing visual matrices.
Use targeted lock regeneration, preserve unrelated dependency versions, then
fresh audits and targeted regressions before one full release gate. Rollback is
the previous commit, not a security exception. No live resources authorized.

Analysis 8: use vendor release notes and registry metadata for fixed versions;
Pillow 13 drops Python 3.10 but our API uses 3.12 and inspector 3.15. Verify actual
decoder installation and existing image-processing behaviors, not only pins.
Keep synthetic old-version attestation fixtures where they test generic parsing.

Analysis 9: the fresh registry audit also reports critical Storybook advisory
GHSA-f2ph-cmg5-wxc8, fixed in 8.6.19. Include the aligned 8.6.19 package family
in this same dependency batch and verify its static build; do not suppress it.

Analysis 10: fresh Python audit reports five pypdf advisories absent from the
original CI report. Update both consumers to 6.21.2, including its hash-bound
universal wheel. Vendor changelog includes further parsing resource bounds in
6.21.2. Re-run PDF derivative/hostile-input coverage and fresh audits before gate.

Targeted results: 26 dependency/CI policy tests and 53 media tests passed.
Fresh API, Django and frontend dependency audits report no known findings.
Both Python environments pass pip check; frontend production and Storybook builds
passed. The inspector builder installed Pillow 13 using the PyPI-published CPython
3.15 manylinux wheel hash; final paired PDF build/visual/full validation follows.
Sources: Pillow 13 release notes, pypdf changelog, GitHub GHSA-f2ph-cmg5-wxc8,
and official PyPI/npm package metadata. No advisory exceptions or runtime bypasses.

## Issues

1. High, product: a recent-auth 401 is refreshed/retried then invalidates a valid
   session. Reproduction: settings privacy export after document navigation.
   Evidence: /tmp/base2-f118-live-browser.log; browser acceptance 13 pass/1 fail.
   Missing completed export also explains runtime verifier failure, not a separate
   confirmed worker defect. Status: repaired; explicit reauthentication and completed export verified live.
2. Medium, visual: Google's dark button has a white iframe canvas under inherited
   dark color-scheme. Live google-ready-login.png and
   google-frame-light-context-diagnostic.png demonstrate the isolated correction.
   Status: repaired; live Google readiness passed and actual screenshot inspected.

Evidence root: /home/woodkill/.local/state/base2-full-preview/base2-full-20261020-095030.
That trial is destroyed; inventory confirmed zero droplets and managed DNS records.
The subsequent approved trial and its terminal result are recorded below.

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

## Merged repair and automated live trial

PR #86 merged with review ancestry preserved to main
5aa827aa8b1b8b5a726ae321c891e8e73462c5e7.
Feature gate: 132 passed on 83fe61fd; all 20 PR checks and all 10 post-merge
workflows passed. Changed-line coverage was 95.45%, above the 90% floor.

First merged-source gate: 130 passed, one failed, one blocked:
`.artifacts/complete-gate/20261020T133032Z-2960644/result.json`.
The factory test raised an internal Python tarfile SystemError, not a product
assertion. A bounded isolated diagnostic passed (7 factory tests, 2 dependent
preflight tests); Git connectivity passed and memory/disk were healthy.
One unchanged-source diagnostic full gate passed all 132:
`.artifacts/complete-gate/20261020T135015Z-3006821/result.json`.
The unexplained intermittent interpreter failure remains a residual risk,
not erased by retry and not addressed by weakening retry/gate policies.

Approved automated-only trial: base2-full-20261020-140734, exact merged source,
Frankfurt, staging certificates, 60-minute/USD 0.25 ceiling.
All 17 services became healthy and eight route probes passed.
Browser acceptance: 13 passed, one failed; original evidence retained under
`~/.local/state/base2-full-preview/base2-full-20261020-140734/browser`.
Google rendering and freshness recovery passed; screenshots were inspected.
Runtime verification passed: completedExportCount=1, preferenceAuditCount=1,
migrationLedgerVerified=true. No test emails or interactive Google sign-in.
Teardown completed and provider inventory confirmed zero droplets/preview DNS.

Analysis 6: the remaining live failure is fixture ordering, not lost audit data.
The organization UI intentionally shows only the latest five security events.
Explicit sign-in and export polling add newer session events, displacing the
earlier preference update. Check the preference event immediately after saving,
before refresh-heavy flows; preserve the bounded UI and all later security checks.
Add an assertion-order contract (observed failing before repair) and a component
regression proving older events fall outside the five-event window.
No runtime, authorization, source-binding, acceptance-reporter, or baseline changes.
The corrected test has not yet passed live; T009 remains open. The approved trial
is consumed. A new paid trial requires fresh owner approval after validation.
