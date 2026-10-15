# Tasks

- [x] T001 Read constitution, current source, latest acceptance and existing suites.
- [x] T002 Create feature branch, requirements, batch budget and initial analysis.
- [x] T003 Add route/role/state/evidence ledger and fail-closed schema/drift tests (R01).
- [x] T004 Add public form/recovery browser state regressions (R02,R04,R06).
- [x] T005 Repair reproduced public/auth defects with focused regressions (R02,R04).
- [ ] T006 Verify local Compose and disposable account/mail prerequisites (R02,R05).
- [x] T007 Complete backend registration/verification/reset/replay/session journeys (R02).
- [x] T008 Cover dashboard links and persisted settings, roles and session revocation (R03).
- [x] T009 Cover enabled populated content, detail links, search pagination and locales (R04).
- [x] T010 Cover workspace create/edit/reload/import/export and permissions (R05).
- [x] T011 Cover invitation acceptance/expiry, booking lifecycle and role boundaries (R05).
- [x] T012 Extend media and operations safe lifecycle/recovery journeys (R05).
- [ ] T013 Capture and inspect missing page/state visuals; obtain any required reference approval (R06).
- [x] T014 Extend critical journeys across browser engines, input modes and user preferences (R07).
- [x] T015 Integrate ledger and journey checks into supported assurance/CI (R08).
- [ ] T016 Re-run tasks -> analysis -> additional/fixed tasks review; close known gaps.
- [ ] T017 Run affected integration, coverage and visual checks, then complete release gate.
- [ ] T018 Record exact-source results, residual risks and approval-gated live next steps.

No unchecked task is implied complete by a previous feature's green gate.

### Additional tasks from analysis cycle 4

- [x] T019 Reproduce and repair collection paging, retry, deduplication and stale/cyclic pages.
- [x] T020 Add isolated enabled-capability browser profile without changing deployed capabilities.
- [x] T021 Exercise collection pagination in browsers, including failed-page recovery.
- [x] T022 Audit pagination-cycle guards across adjacent search consumers.
- [x] T023 Validate disposable-container cleanup failure reporting without masking original failures.
- [x] T024 Verify updated cleanup through the real disposable database acceptance runner.
- [x] T025 Complete current-source invitation confirmation and booking retry browser validation.

### Additional tasks from analysis cycle 6

- [x] T026 Refresh source-bound media/operations visual reviews after actual current-source runs, preserving original references and review ancestry.
- [ ] T027 Reconcile route coverage inventory with current evidence and explicitly retain unsupported or external-delivery limitations.
- [ ] T028 After local gates and CI pass, perform the separately approved bounded live acceptance and verify teardown.
- [x] T029 Validate and use guarded media review renewal for unchanged references, with clean-source and failed/incomplete-run rejection tests.

## Implemented evidence (not whole-feature completion)

- Public/auth batch: 42 synthetic UI journeys pass across Chromium/Firefox/WebKit
  at 390/1440, with actual-state accessibility, overflow and screenshot checks.
- Fixed swallowed HTTP404, stale searches, repeated verification requests,
  abandoned-reset redirect, undersized contact controls and Explore destination.
  Search pagination now preserves results, deduplicates and supports error retry.
- Disposable PostgreSQL/Redis acceptance passes real registration, duplicate
  rejection, verification/replay, reset/replay/expiry, session revocation,
  password rotation, persisted preferences/version conflicts and mandatory
  notifications. External Celery delivery is intercepted, not claimed tested.
- Initial partial T005/T008/T009 coverage was extended in cycles 5-6; complete
  release tasks remain open. No publication, merge or live trial for Feature113.
- Integrated public/protected synthetic UI run now passes all 60 cases on three
  engines at both widths. Collection/search focused checks pass 11 tests; collection
  browser pagination was subsequently completed as T021.
