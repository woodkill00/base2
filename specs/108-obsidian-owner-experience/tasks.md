# Ordered tasks

All implementation tasks remain pending. Each task records test command, exact source and evidence when completed. Dependencies are mandatory; regression tests precede fixes.

- [ ] T001 [FR-001 FR-014] (depends: none) Inventory PublicRoutes, localized routes, settings tabs, role/module guards and all interactive controls; publish route/state matrix with expected assertions.
- [ ] T002 [FR-002 FR-003] (depends: T001) Inventory homepage canonical tokens, theme preferences, shared shells and generated profiles; define approved visual contract and viewport/contrast matrix.
- [ ] T003 [FR-004 FR-005] (depends: T001) Add failing realistic Axios 422 signup regressions and policy-helper expectations in apiErrors/signup tests; include normalized and repeated-normalization cases.
- [ ] T004 [FR-004 FR-005] (depends: T003) Repair error normalization and accessible signup policy/field errors; test 400/401/403/422/429/5xx/offline and safe correlation IDs.
- [ ] T005 [FR-007] (depends: T001) Reproduce preference RLS failure with production-equivalent limited PostgreSQL role; trace actor/tenant transaction context and expected audit/version behavior.
- [ ] T006 [FR-007] (depends: T005) Repair settings repository/request context without bypassing RLS; verify read/write, stale version, rollback and cross-user/tenant denial.
- [ ] T007 [FR-008 FR-009 FR-010] (depends: T001) Specify exact owner environment/tenant/minimum role and Vaultwarden-reference contract; test disabled/missing/malformed/conflicting configuration before implementation.
- [ ] T008 [FR-008 FR-010] (depends: T007) Implement idempotent owner provisioning using canonical auth models/service after migrations; test existing-security preservation, identity conflicts and parallel creation.
- [ ] T009 [FR-009 FR-011] (depends: T008) Integrate opt-in provisioning into supported deployment wrappers; resolve private secrets without arguments/logs and emit safe owner-readiness receipts.
- [ ] T010 [FR-010 FR-011 FR-012] (depends: T009) Test restart, redeploy and empty-DB recreation using synthetic identities; verify retained state versus fresh-account semantics and no owner credential mutation.
- [ ] T011 [FR-002 FR-003] (depends: T002 T004) Refactor shared page/auth/form/status/navigation styles into canonical tokens; preserve theme/contrast choices and supported generated profiles.
- [ ] T012 [FR-002 FR-004 FR-006] (depends: T011) Apply shared design to login/signup/verification/recovery/invitation and all auth states; test keyboard, errors and responsive forms.
- [ ] T013 [FR-001 FR-002 FR-003] (depends: T011) Apply shared design to public content/search/contact/events/collection/detail/error and localized routes; test enabled/disabled modules and route matrix.
- [ ] T014 [FR-001 FR-002 FR-007] (depends: T006 T011) Apply shared design to dashboard/settings/workspace/media/operations/first-party admin; test controls, persistence, menus, dialogs and scroll behavior.
- [ ] T015 [FR-006 FR-012] (depends: T004 T006 T010) Add integrated synthetic account journeys for registration/verification/login/logout/recovery/invitation/MFA/session and authorization with positive/negative cases.
- [ ] T016 [FR-003 FR-013] (depends: T012 T013 T014) Capture deterministic matrix screenshots with explicit fonts/layout readiness, stable fixtures and reduced motion; verify scrolling, zoom, focus, contrast and localization.
- [ ] T017 [FR-013 FR-014] (depends: T015 T016) Add CI route-drift/visual/functional/accessibility checks; require reviewed baseline updates and test generated reference profiles against the same contract.
- [ ] T018 [FR-015 FR-016] (depends: T009 T017) Integrate compact exact-source test/evidence reporting with existing assurance and durable notifications; add failed/skipped/stale evidence and retry-bound tests.
- [ ] T019 [FR-007] (depends: T006) Add pooled-connection alternating-user/tenant, parallel-request and exception/rollback tests proving transaction-local identity never leaks; cover notification preferences using the same context.
- [ ] T020 [FR-008 FR-009 FR-010] (depends: T008 T009) Test pre-existing disabled/unverified/MFA-enabled users, same-email/different-tenant and name collisions, concurrent launches and explicit credential rotation; no silent resets or verification bypass.
- [ ] T021 [FR-009 FR-011 FR-012] (depends: T009 T010) Document secure owner activation and verification handoff, retention/recreation versus restore, missing-secret recovery and bounded MFA wait. Test wrong environment/profile and ensure generic generated sites never seed the owner.
- [ ] T022 [FR-006 FR-013 FR-014] (depends: T015 T016) Test inventory checker against a deliberately unlisted route/state and invalid baseline; ensure it fails. Define smoke versus full matrix budgets and manual visual approval status; test screenshots do not pass with blank animation regions.
- [ ] T023 [FR-006 FR-012] (depends: T015) Verify test-mail/provider isolation, token expiry/replay/rate limiting and real-owner mutation guard; unavailable real providers remain explicit acceptance blockers where required.
- [ ] T024 [FR-015 FR-016] (depends: T018) Fault-test shell/SSH/browser failure followed by successful cleanup, alert delivery failure, critical skips and lease expiry during acceptance; preserve failing exit status and durable queued alert without extending TTL.
- [ ] T025 [FR-002 FR-006 FR-016] (depends: T013 T014 T020) Verify vendor/edge login boundaries and application owner separation with synthetic roles; audit cookie/CSRF, denied routes, secret redaction and mobile/auth layout regressions before release.
- [ ] T026 [FR-016] (depends: T018 T019 T020 T021 T022 T023 T024 T025) Run complete release authority after targeted fixes; record source-bound coverage, security results, unresolved risks and rollback proof.
- [ ] T027 [FR-006 FR-011 FR-012 FR-013 FR-015 FR-016] (depends: T026) After separate activation approval, run bounded live preview owner login and synthetic journeys, vendor access, screenshots/human review, rollback and verified teardown; do not mark critical skips green.
- [ ] T028 [FR-001 FR-014 FR-015 FR-016] (depends: T027) Close requirement/evidence ledger, publish operational runbook and future-route checklist; record owner review and any blockers before release.
