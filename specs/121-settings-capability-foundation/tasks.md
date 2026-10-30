# Tasks and acceptance ledger

- [x] T1 Read constitution, existing Feature 103, runtime manifests and settings contracts.
- [x] T2 Record bounded scope, architecture, environment and explicit non-goals.
- [x] T3 Write failing role/capability/registry/first-write API regression tests (AC1/3/4/5).
- [x] T4 Implement additive registry and safe preference write snapshot (AC1/3/4/5).
- [x] T5 Write search/deep-link/failure/recovery/repeated-save UI regressions (AC1/2/4/6).
- [x] T6 Integrate discovery and safety into existing SettingsCenter (AC1/2/3/4/5/6).
- [x] T7 Integrate appearance behavior and applied-state tests (AC7).
- [x] T8 Review site-family roadmap, exact issue ledger and documentation (AC5/8).
- [x] T9 Focused API/React/static checks and changed-line coverage review (AC8).
- [ ] T10 Full gate, database concurrency/RLS and responsive visual/accessibility acceptance (AC8).
- [ ] T11 Parent-controlled draft PR; no merge/deployment implied.

## Issues

| ID      | Severity  | Reproduction / cause                                                                | Regression                                  | State                                                                           |
| ------- | --------- | ----------------------------------------------------------------------------------- | ------------------------------------------- | ------------------------------------------------------------------------------- |
| S121-01 | Medium    | Non-admin capabilities include organization/developer from accounts flag alone      | tenant role matrix + failed capabilities UI | Implemented; focused pass, broader acceptance pending                           |
| S121-02 | Medium    | Search filters categories, not individual controls                                  | setting synonym + fragment focus            | Implemented; focused pass, broader acceptance pending                           |
| S121-03 | High      | Missing initial row SELECT lock cannot fence concurrent INSERT                      | unique conflict and exact write snapshot    | Implemented; focused pass, broader acceptance pending                           |
| S121-04 | Medium    | Failed preference read leaves editable defaults                                     | unavailable read + retry/discard            | Implemented; focused pass, broader acceptance pending                           |
| S121-05 | Medium    | Notification GET includes updated_at, subsequent PUT spreads it into closed payload | repeated saves with server timestamp        | Implemented; focused pass, broader acceptance pending                           |
| S121-06 | Medium    | Appearance values stored but not applied to theme/accessibility consumers           | appearance integration                      | Implemented; focused pass, broader acceptance pending                           |
| S121-07 | High      | Organization audit selects actor membership not event tenant                        | audit isolation repair                      | Implemented; focused pass, broader acceptance pending                           |
| S121-08 | Assurance | Docker / dependencies absent in cloud checkout                                      | supported runner prerequisite evidence      | Dependencies provisioned through repo scripts; Docker/browser execution blocked |

No passing focused test substitutes for T10. Full implementation/release status
will be updated only with exact-source evidence.

## First focused results (2026-10-30, not release approval)

- API red: 10 expected failures / 5 passes for missing discovery and preference race
  behavior (`local diagnostic: base2-121-api-red.txt`). API green: 193 passing settings discovery,
  contract, repository and validation cases (`local diagnostic: base2-121-api-green.txt`).
- UI red: 8 expected failures / 1 pass (`local diagnostic: base2-121-ui-red.txt`). UI green after
  recovery/negative cases: 45 passing settings/discovery/parser cases
  (`local diagnostic: base2-121-ui-green.txt`).
- Focused ESLint passed for SettingsCenter, discovery parser and new unit tests.
- Typecheck found 10 missing ThemeContext declaration/useContext unknown errors in
  the header/toggle integration; corrected before browser validation. No weakening or suppression of the check.
- Real PostgreSQL tests added in `api/tests/test_settings_postgres.py` with a barrier
  forcing concurrent first inserts, exact snapshots, tenant/user predicates and
  repeated timestamp-bearing notification roundtrips. Not yet run locally; Docker
  unavailable. Parent wired explicit invocation in isolated migrated PostgreSQL CI.
- Browser `settings-foundation.spec.ts` adds 7 cases for deep-link/apply/reload,
  unavailable reads, conflict/discard/new-version save, repeated notifications,
  fail-closed discovery and mobile/desktop catalog accessibility. Not yet run.
- Frontend CI now explicitly invokes the new foundation suite, existing settings
  platform suite and settings responsive release matrix. No baseline was updated.

## Additional discovered issues

| ID      | Severity | Reproduction / cause                                                              | Regression / repair                                                          | State                             |
| ------- | -------- | --------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- | --------------------------------- |
| S121-09 | High     | Async save can call updateUser after account changes                              | Keyed account/site/epoch remount + mounted guard; late-save regression       | Fixed, focused pass               |
| S121-10 | Medium   | Unauthorized direct category could render before redirect effect                  | Render only admitted category in same render; redirect remains compatibility | Fixed, review pending             |
| S121-11 | Medium   | Partial notification rows leave search anchors without controls                   | Search filtered to actual rows; focused unavailable deep-link recovery       | Fixed, focused pass               |
| S121-12 | Medium   | Successful locale update triggers background reload that can overwrite next draft | Mount-scoped reads keyed by account, locale snapshot                         | Fixed, review pending             |
| S121-13 | Medium   | Unbounded discovery GET can keep whole settings loader pending                    | 10-second initial GET timeouts in the settings service                       | Fixed, focused validation pending |

User-facing scope, limitations and recovery instructions:
`docs/settings-capability-foundation.md`. Audit repair evidence is separately in
`audit-scope.md`; no old events are relabeled or rewritten.

## Final own focused batch (2026-10-30)

- **193/193 API settings tests pass** after exact account/personal scope assertions;
  focused Ruff clean. Parent's broad API result before the final test-only tightening:
  1,365 passed / 8 skipped; mypy 250 files passed. No claim that schema-owner SQL
  tests prove RLS. Docker/PostgreSQL integration awaits the dedicated CI job.
- **59/59 React settings tests pass** across existing settings, discovery journeys,
  and parser contracts. Focused aggregate: 95.72% lines / 82.03% branches. Existing
  floors unchanged. Source-line diagnostic intersects `git diff` added lines with
  Istanbul executable statement starts: SettingsCenter 170/175 (97.14%), discovery
  parser 41/41, settings service 6/6. This is not a substituted release receipt.
  Evidence: `.artifacts/feature-121/frontend-focused-coverage/` and
  `.artifacts/feature-121/changed-line-diagnostic.json`.
- Additional unit coverage exercises repeated failed discovery/recovery, failed
  reloads, all appearance fields, unsaved full-unload warning, region validation,
  notification validation, timeout uncertainty, and no automatic mutation replay.
- One new test fixture used lowercase `email` where the actual accessible label is
  `Marketing Email delivery`; corrected the unit selector and exact browser label,
  then reran the complete focused batch. This was fixture drift, not a hidden pass.
- Appearance integration includes corrected TypeScript declarations; its focused checks/typecheck and
  build pass. Parent owns final broad frontend validation for the integrated source.
- **Local browser execution is blocked before page navigation:** installed system
  Chromium failed sandbox socket EPERM; authorized escalation failed at runtime
  bwrap protected-path setup before executing. No further bypass/retry. No new or
  existing screenshot is claimed reviewed; no visual baseline was modified.
- New/extended browser suites are wired to pinned CI browsers. Full settings release
  visual, accessibility, live topology, restricted-runtime RLS, and exact-source
  complete-gate acceptance remain required before release. Draft PR is not approval.

### Additional safety correction

S121-14 (medium): preference/notification mutations had no timeout and could freeze
forms indefinitely. Both now use 10 seconds. Timeout/network/5xx or malformed-write
response uncertainty preserves the draft, blocks another save, and requires explicit
reload/discard reconciliation; no automatic PUT replay. Covered by both settings
forms in unit tests. Notification reads now reject malformed/duplicate/invalid rows
instead of silently enabling defaults. Organization's embedded account-security
history is explicitly labeled across-sites, separate from actual organization audit.

## Final reviewer followup

- S121-15 (medium): developer settings linked `/docs` as API documentation even though
  that path is public content documentation. Added a failing regression (1 failed /
  20 passed in that file), then removed the misleading action. English/German/Arabic
  help now states API documentation access is deployment-managed and no endpoint link
  is configured. The real credential-administration link is retained. Evidence:
  `local diagnostic: base2-121-devdocs-red.txt`.
- Repaired the existing layout freshness-recovery fixture with a stable synthetic
  account ID and complete capability/notification/security-event response shapes.
  The real reauthentication flow and export/refresh assertions are unchanged.
- **Final focused UI: 60/60 pass**, 96.23% aggregate lines, 82.57% branches, unchanged
  floors. Evidence refreshed at the same focused-coverage artifact location.
- Production/test sources frozen for final integrated broad validation.
  Local browser acceptance remains blocked, not passed; pinned CI must establish it.

## Integrated pre-PR verification

- Full frontend lint, TypeScript, production build, and 527 tests across 98 files passed.
- Critical glass/theme subset measured with the repository coverage evaluator: 100% lines, statements, functions, and branches; policy floors unchanged.
- Full API non-integration run passed (1,365 passing progress markers, eight skipped); API typecheck passed for 250 files and final Ruff passed. The coverage invocation includes test modules, so its 88.63% result is not a production-only coverage claim.
- CI wiring and frontend selection regression checks: 27 passed.
- Local browser execution was blocked before navigation by the execution environment. No local visual, PostgreSQL, restricted-role, or complete-gate pass is claimed.
- Draft-PR CI includes real isolated PostgreSQL audit/settings persistence tests, the full account/settings browser suite, responsive settings matrix, and existing layout/Volcano checks. Results remain pending until those jobs execute.
