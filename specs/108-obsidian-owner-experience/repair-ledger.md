# Feature 108 repair checkpoint

Source: branch `108-obsidian-owner-experience`; last committed candidate
`a1c8582bac7e181fe95e8434cc68699697faf1fe`, with subsequent uncommitted repair work.
Focused results below do not constitute exact-final-source release acceptance.
Historical checkpoint above is superseded by the live batch below. Owner credentials remain private.

## Live acceptance repair batch (2026-09-11)

### Subsequent deployment setup batch

`99c6c15ab386a57d00da2c153e7bbe1569900bc8` passed its exact release gate
and replaced the old preview after verified zero-resource cleanup. Five live
journeys passed again; export remained queued. Do not erase this second failure.
Read-only diagnostics found the lifecycle table has no `base2-obsidian` row,
so the dispatcher correctly admits no work. Runtime tracebacks were separately
`FileNotFoundError` loading the operations probe catalog, not dispatch exceptions.

- R14: initialize only the explicitly enabled disposable preview through canonical
  lifecycle provision/transition functions before workers start. Preserve existing
  ownership, revisions and suspension/deletion state; never reactivate arbitrary tenants.
  Cover fresh PostgreSQL bootstrap, exact replay, missing/invalid authority and conflicts.
- R15: mount the single public operations probe catalog read-only in the runtime
  worker; no repository-wide or secret-directory mount. Test composition and file validity.
- Operator timer setup also caught an argument placed after the command boundary.
  It was stopped and replaced before execution; verified ExecStart and working
  directory now point to the exact lease cleanup. No provider action was caused.

Analysis: retain R10-R12 code regressions, but distinguish them from the live
activation blocker. Add bootstrap ordering/real-role coverage instead of changing
the dispatch security filter or increasing browser timeouts. This batch is not
live-verified; current live source remains `99c6c15` until gated deployment.

Setup-batch preflight: 16 initializer tests, 20 deployment-entrypoint tests and
real restricted-role PostgreSQL acceptance passed, including fresh lifecycle
bootstrap and exact replay. Complete API (28 partitions) and deployment coverage
collection passed. The broader sanitized live diagnostic found no tracebacks in
API, Django, privacy, email or content workers; runtime failures are the missing
catalog already covered by R15. Final exact-source gate and live export remain due.

Candidate `655d9574d69f6aea75e46d76494c331ff9a21dfe` passed all 114 required
release groups and was pushed and deployed as `base2-full-20260911-015705`.
The preview expires at 02:57 UTC, with a WSL teardown timer; no extension planned.
Real owner login/read-only settings and restricted-role settings isolation passed.
Five of six live browser journeys passed, including operator application logins
and media. Synthetic privacy export remained queued; live acceptance is FAILED,
not complete. Private evidence resides in the operator preview state directory.

| ID  | Root issue / reproduction                                          | Repair and verification                                                                                                          |
| --- | ------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------- |
| R10 | Dispatch query selects only ID but consumes ID and token           | Select both fields; focused regression passes; real restricted-role dispatch/claim handoff required.                             |
| R11 | Dispatch lease changes roll back before Celery handoff             | Commit discovery before pool reset; test duplicate discovery cannot redispatch committed leases and a separate worker can claim. |
| R12 | Snapshot configured after tenant binding starts transaction        | Set options before tenant/claim binding; test ordering, exception cleanup, real export and reused connection isolation.          |
| R13 | Runtime diagnostic counts protected exports without tenant context | Repair diagnostic to bind exact preview tenant; do not interpret invisible RLS rows as no stored operations.                     |

Focused repair checks: 19 repository/worker tests, three transaction-order tests,
and existing five-part data-rights matrix pass. Disposable PostgreSQL acceptance
now passes actual repository/pool/export execution and the existing security denials.
Complete API coverage collection passed (27 partitions). Next: committed-source changed-line coverage,
one exact-source release gate, then authorized live verification. No production
queue replay, owner mutation, permission relaxation or timeout inflation.

Analysis cycle: SQL-only role tests missed application-level row unpacking and
commit ownership; mocked export connections missed transaction ordering. Add
real adapter coverage to the existing restricted-role acceptance rather than a
second broad suite. Existing security denials must remain intact. No known
planning blocker remains in this batch; passing execution evidence is still due.

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

### Pending-action capture stability

A no-update media regression run found a light detail-dialog scroll mismatch
(23 passed, one failed). The next release was stopped during its prerequisite
stability runner; its full gate never started. Comparison showed identical content
at different scroll offsets. The test normalized the pending-action anchor only for
desktop; normalization and the existing two-pixel geometry assertion now apply to
every representative modal project. Capture regeneration passed 24 tests with 12
predefined exclusions. Two no-update repetitions are required before the next gate.
No screenshot tolerance or accessibility assertion was relaxed.

### Release record reconciliation

The gate on `fa8e688b1f3f0898d7e6a902d5eccbbcb392f117` completed with 109
passing groups, one failed media review-source contract and four blocked dependent
groups. Evidence: `.artifacts/complete-gate/20260911T013219Z-1584486/result.json`.
The application's reviewed media captures had changed, but Feature 105's manual
technical-review descriptor still referenced `df37eb9`. Its source binding is now
updated to the actually reviewed `fa8e688` capture commit; no generated test result
or pass receipt was edited. Owner product/design approval remains separate.

The media review validator now includes shared shell, theme and CSS dependencies.
Preflight passed Operations/media review validation, workspace/baseline contracts,
visual-assurance contracts and media planning. No application code changed in this
reconciliation. Future preflight must check all review descriptors as well as
screenshots before the complete gate; checking only Operations metadata was a gap.

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
