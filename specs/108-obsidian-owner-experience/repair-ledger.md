# Feature 108 repair checkpoint

Source: branch `108-obsidian-owner-experience`; last committed candidate
`a1c8582bac7e181fe95e8434cc68699697faf1fe`, with subsequent uncommitted repair work.
Focused results below do not constitute exact-final-source release acceptance.
No new DigitalOcean preview is running. Owner credentials remain private.

| ID  | Root issue / scope                                                                                 | Status and next verification                                                                                                                                                                                                          |
| --- | -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R01 | Shared Obsidian styles leaked into other profiles                                                  | Scoped overrides repaired; 21 account browser tests passed. Recheck affected consumers after remaining theme fixes.                                                                                                                   |
| R02 | Synthetic release unit test depended on host browser cache                                         | Fixture isolated; 40 assurance tests passed. Production browser admission unchanged.                                                                                                                                                  |
| R03 | Disposable PostgreSQL migration process exited 139                                                 | Isolated rerun and subsequent acceptance passed. Native crash cause remains unresolved; do not erase intermittent risk.                                                                                                               |
| R04 | Changed-line coverage was 86.58%, below the existing 90% requirement                               | Added tests: 23 owner-provisioning and 19 preview-entrypoint tests pass. Recalculate coverage before next full gate; do not lower thresholds.                                                                                         |
| R05 | Operations/media/workspace screenshots and source-bound evidence lagged intentional design changes | Baselines recaptured as implementation-review candidates. Operations explicit-mode run: 22 passed, 20 predefined exclusions. Refresh source-bound manifests after the final batch; final owner visual approval remains pending.       |
| R06 | Primary button transition produced insufficient contrast                                           | Removed color/opacity interpolation and retained readable disabled styling. Ultrawide check passed contrast before snapshot comparison.                                                                                               |
| R07 | Light-mode fixtures only changed OS preference; Obsidian still defaulted dark                      | Fixtures now set the explicit light cookie. Workspace then exposed real contrast failures in its violet eyebrow and dark input surface. OPEN: tokenize these elements, check adjacent fields/states, rerun affected light/dark cases. |
| R08 | Media retained purple controls/placeholders                                                        | Shared-token overrides added. Latest media matrix was NOT RUN because the sequential command stopped at workspace failure. Run independently after batch review; prior media pass predates this change and cannot satisfy it.         |
| R09 | Real owner, restricted runtime-role settings, vendor and synthetic live journeys                   | NOT RUN on this candidate. Local restricted-role drill rejected the older superuser-based local runtime. Do not weaken that assertion. Live acceptance remains gated; no preview should be claimed ready.                             |

## Evidence and next batch

### Current repair round

- R04: refreshed API and DigitalOcean coverage; preflight reports 98.66% for the
  committed changed lines. Final committed-batch coverage still must pass the gate.
- R07: workspace text fields and accent copy now use scoped theme tokens. All 24
  workspace checks passed, including explicit light mode.
- R08: media token changes passed 24 checks with 12 predefined matrix exclusions.
- R10: light-header menu used white SVG text; scoped header-button color repaired.
  Added an explicit SVG/header color regression assertion; workspace checks passed.
- Snapshot update discovery: default Playwright `changed` mode can retain an old
  capture within tolerance. The reviewed design refresh now uses `all` to capture
  the actual current frames before rebuilding evidence manifests. This does not
  waive subsequent no-update regression checks or required owner visual review.
- No complete gate or deployment was started during this focused repair round.
  Final capture, exact-source validation and live acceptance remain pending.

- Complete-gate failure record: `.artifacts/complete-gate/20260911T010002Z-1521697/result.json`.
- Local diagnostic logs: `/tmp/f108-workspace-final.log`, `/tmp/f108-operations-final.log`,
  `/tmp/f108-owner-more.log`, `/tmp/f108-entrypoints4.log`. These temporary paths are
  not durable release receipts; retain sanitized evidence before closeout.
- Fix the entire related explicit-theme/field/placeholder group before recapture.
- Collect independent affected-suite results separately, preserving nonzero exits;
  a workspace failure must not prevent safe media diagnostics.
- Finish coverage review, reviewed baselines and source-bound manifest updates before
  another complete gate. Never change tested inputs while a suite is running.
- Keep all incomplete requirements open. No blanket claim of full feature coverage,
  owner visual approval, live readiness, or resolution of the native crash is made.
