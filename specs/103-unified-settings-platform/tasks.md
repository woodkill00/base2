# Ordered Tasks: Unified Account and Settings Platform

## Phase 1 - Specification and inventory

- [x] T001 Create Feature 103 branch from clean aligned `main`.
- [x] T002 Record product-pattern research and standards.
- [x] T003 Define user stories, edge cases, FR-001..FR-035, and measurable outcomes.
- [x] T004 Define implementation plan, rollback, and constitution gates.
- [x] T005 Define data entities and version/conflict semantics.
- [x] T006 Define settings API v1 contracts and typed errors.
- [x] T007 Define validation quickstart and traceability rule.
- [x] T008 Inventory existing profile, identity, privacy, organization, manifest, and visual contracts.
- [x] T009 Build exact FR-to-task/test/evidence traceability matrix.

## Phase 2 - Analysis cycle

- [x] T010 Analyze product completeness and category discoverability.
- [x] T011 Analyze model/API compatibility, migration, downgrade, backup, and restore.
- [x] T012 Analyze authentication, authorization, tenant, CSRF, replay, concurrency, URL, and secret threats.
- [x] T013 Analyze accessibility, responsive, browser, input, state, and visual coverage.
- [x] T014 Analyze generator/profile capability drift and disabled-feature behavior.
- [x] T015 Analyze operational, dependency, worker, network, and partial-failure behavior.
- [x] T016 Add every corrective task found by T010-T015.
- [x] T017 Repeat analysis until zero unresolved specification/task findings remain.

## Phase 3 - Test-first canonical models

- [x] T018 Add failing Django tests for preference defaults, choices, uniqueness, and versions.
- [x] T019 Add failing Django tests for notification uniqueness and mandatory delivery.
- [x] T020 Add failing migration forward/backward and model-state tests.
- [x] T021 Implement canonical Django preference and notification models.
- [x] T022 Add and validate the Django migration.
- [x] T023 Register safe admin inspection without exposing sensitive fields.

## Phase 4 - Test-first API persistence and contracts

- [x] T024 Add failing SQL migration parity tests.
- [x] T025 Add failing repository tests for defaults, create, read, update, conflict, and rollback.
- [x] T026 Add failing owner/cross-user/cross-tenant repository tests.
- [x] T027 Add failing preferences endpoint contract and unknown-field tests.
- [x] T028 Add failing notification contract and mandatory-family tests.
- [x] T029 Add failing capability and security-event projection tests.
- [x] T030 Add failing unsafe avatar URL tests.
- [x] T031 Implement SQL migration with indexes, constraints, and versioning.
- [x] T032 Implement settings repository transactions.
- [x] T033 Implement typed Pydantic request/response schemas.
- [x] T034 Implement capability, preference, notification, and security-event routes.
- [x] T035 Add redacted audit events for relevant settings changes.
- [x] T036 Harden profile avatar validation without dereferencing URLs.
- [x] T037 Register routes and update OpenAPI/contract evidence.

## Phase 5 - Generator and capability packs

- [x] T038 Add failing manifest schema/default/unknown-field tests.
- [x] T039 Add failing generated-profile enable/disable/dependency tests.
- [x] T040 Map settings capabilities from the existing closed module manifest without creating a second drifting vocabulary.
- [x] T041 Add safe runtime settings capability configuration.
- [x] T042 Verify all built-in profiles and generated fixtures.
- [x] T043 Prove disabled settings are absent in UI metadata and unusable at API boundaries.

## Phase 6 - Test-first unified React shell

- [x] T044 Add failing shell overview, route, redirect, and breadcrumb tests.
- [x] T045 Add failing settings search, synonym, no-result, and focus tests.
- [x] T046 Add failing loading, empty, malformed, unavailable, and retry-state tests.
- [x] T047 Add failing preference save, rollback, conflict, and unsaved-change tests.
- [x] T048 Add failing keyboard, announcement, label, focus, and axe tests.
- [x] T049 Implement typed settings service and error normalization.
- [x] T050 Implement adaptive SettingsShell, category navigation, overview, and search.
- [x] T051 Implement profile category and safe avatar guidance.
- [x] T052 Integrate account-health, MFA, recovery, sessions, and security events.
- [x] T053 Integrate privacy consent, operation history, export, correction, deactivation, and deletion.
- [x] T054 Implement notification category with mandatory/optional semantics.
- [x] T055 Implement appearance and accessibility category.
- [x] T056 Implement language, timezone, formats, and week-start category.
- [x] T057 Integrate organization and developer categories behind capabilities.
- [x] T058 Add separated confirmation and danger-zone components.
- [x] T059 Replace duplicate navigation while retaining compatible deep links.

## Phase 7 - Visual and user interaction assurance

- [x] T060 Add deterministic authenticated settings fixture with no real credentials.
- [x] T061 Add geometry/overflow/focus/target-size/announcement assertions.
- [x] T062 Add overview, profile, security, privacy, notification, appearance, locale, error, loading, empty, confirmation, and danger-state screenshots.
- [x] T063 Add compact, DPR3, short-landscape, tablet, desktop, ultrawide, 200%-text, and 400%-zoom coverage.
- [x] T064 Add light, dark, high-contrast, reduced-motion, keyboard, touch, Chromium, Firefox, and WebKit coverage where deterministic.
- [x] T065 Add contact sheet, artifact integrity, dimensions, route/state metadata, and explicit review sidecars.
- [x] T066 Verify no secrets, recovery codes, tokens, emails, or unsafe personal data enter visual artifacts.
- [x] T067 Review screenshots as user experiences and create corrective tasks for clipping, hierarchy, readability, motion, and discoverability.
- [x] T068 Repeat visual capture/review until zero unresolved visual findings remain.

## Phase 8 - Security, reliability, and compatibility gates

- [x] T069 Run Django model/migration suites.
- [x] T070 Run API unit, contract, integration, PostgreSQL, and coverage suites.
- [x] T071 Run auth, tenant, CSRF, replay, conflict, URL, malformed-output, and secret negative tests.
- [x] T072 Run React unit, lint, format, build, axe, and coverage suites.
- [x] T073 Run settings Playwright interaction and compatibility suites.
- [x] T074 Run generated-site/profile and module lifecycle matrices.
- [x] T075 Run visual representative and expanded release matrices.
- [x] T076 Run dependency, license, SBOM, audit, threat-model, and edge-security checks.
- [x] T077 Run staged/history secret scans with zero findings.
- [x] T078 Run complete repository gate and repair every reproducible failure.
- [x] T079 Repeat implemented-system analysis and add every corrective regression task.
- [x] T080 Require zero unresolved implementation findings and complete FR traceability.

## Phase 9 - Publication and live acceptance

- [x] T081 Commit exact feature changes and verify clean status.
- [x] T082 Push branch and publish reviewed PR.
- [ ] T083 Require all executable CI checks green and classify infrastructure-only failures explicitly.
- [ ] T084 Merge exact reviewed head and verify remote/local `main` alignment.
- [ ] T085 Separately admit one bounded exact-main staging-certificate canary.
- [ ] T086 Run all public, authenticated, operator, settings interaction, accessibility, responsive, and visual checks live.
- [ ] T087 Verify health, performance, audit, migration, privacy-worker, and evidence integrity.
- [ ] T088 Perform exact teardown and immediate idempotent replay.
- [ ] T089 Verify empty exact-owned provider inventory and no unrelated mutation.
- [ ] T090 Record final evidence, mark tasks complete, and close Feature 103.

## Dependencies

Tasks execute in numeric order unless marked independently safe by the implementation plan. Django changes precede FastAPI changes, which precede React changes. Publication and provider lifecycle operations remain separate from implementation and require their existing guarded authority.
