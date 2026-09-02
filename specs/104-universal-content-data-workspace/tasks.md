# Ordered Tasks: Universal Content and Data Workspace

**Input**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/content-api.md`, `traceability.md`, and `analysis.md`
**Rule**: Execute in numeric order unless the plan explicitly proves independence. Tests precede implementation. Django precedes FastAPI, which precedes React. A reproducible defect adds a regression task before correction.

## Phase 1 - Specification, inventory, and refinement

- [x] T001 Create `vscode-codex/104-universal-content-data-workspace` from clean aligned `main`.
- [x] T002 Inventory existing Django, FastAPI, PostgreSQL, worker, React, module, generator, visual, and provider-lifecycle foundations.
- [x] T003 Inventory placeholder `/api/items` and Items UI behavior and require an explicit compatibility path.
- [x] T004 Define seven independently testable user stories, edge cases, boundaries, FR-001..FR-062, and SC-001..SC-011.
- [x] T005 Define constitutional implementation order, architecture, security design, schema evolution, performance boundaries, rollback, and authority limits.
- [x] T006 Define canonical entities, states, ownership, constraints, invariants, and migration compatibility.
- [x] T007 Define `/content/v1` definition, record, workflow, saved-view, asset, import, export, public-read, error, cursor, and idempotency contracts.
- [x] T008 Record decisions and rejected alternatives in `research.md`.
- [x] T009 Define implementation and evidence quickstart through repository entrypoints.
- [x] T010 Build exact requirement-to-implementation/test/evidence traceability.
- [x] T011 Analyze product/preset completeness and identify missing end-user states.
- [x] T012 Analyze tenant, role, object, query, rich-text, upload, import/export, and audit threats.
- [x] T013 Analyze migration, compatibility, data-loss, backup, restore, replay, and worker failure modes.
- [x] T014 Analyze accessibility, responsive, browser, interaction, visual, and artifact-review coverage.
- [x] T015 Analyze generator, module-manifest, legacy Items, and disabled-capability drift.
- [x] T016 Add all corrective requirements and tasks found in cycles T011-T015.
- [x] T017 Repeat the tasks -> analysis -> corrective-tasks cycle until no unresolved planning finding remains.
- [x] T018 Add and run `validate_plan.py` for document presence, sequential tasks, requirement count, boundaries, task/test/evidence traceability, and unresolved-marker rejection.

## Phase 2 - Test-first canonical Django definitions and records

- [x] T019 Add failing Django tests for content type keys, versions, statuses, canonical site uniqueness, and published immutability in `django/tests/test_content_workspace_models.py`.
- [ ] T020 Add failing field-kind, validation-key, bound, default, relationship, and presentation-hint tests.
- [ ] T021 Add failing workflow graph, action-role, schedule, and invalid-transition tests.
- [ ] T022 Add failing record value, slug, optimistic version, lifecycle, soft-delete, and cross-scope tests.
- [ ] T023 Add failing immutable version, snapshot hash, diff, and restore-as-new-version tests.
- [ ] T024 Add failing relationship cardinality, target type, scope, cycle/depth, and deletion-policy tests.
- [ ] T025 Add failing saved-view ownership, query-schema, sharing, and permission-revalidation tests.
- [ ] T026 Add failing media binding, import/export job, idempotency, terminal-state, and audit entity tests.
- [ ] T027 Add failing forward/reverse migration, model-state, constraint, and clean-default tests.
- [x] T028 Implement shared closed enums, limits, validators, and structured-rich-text primitives in `django/common/models.py` and focused helpers.
- [x] T029 Evolve existing `django/sitecontent/models.py` content records/revisions and add canonical definitions, fields, workflows, versions, and relationships without parallel record tables.
- [ ] T030 Evolve existing media entities and add canonical saved views, asset bindings, import/export jobs, row outcomes, and audit references in `django/sitecontent/models.py`.
- [x] T031 Add `django/sitecontent` migration with canonical site ownership constraints, uniqueness, indexes, data migration, and reversible operations.
- [x] T032 Add transactional services for definition preview/publication and record mutation/version creation.
- [ ] T033 Add transactional workflow transition, schedule, archive, restore, and soft-delete services.
- [x] T034 Register read-safe Django admin inspection with no raw secrets, files, submitted content, or expiring URLs.
- [x] T035 Run Django focused and migration suites and repair only after a failing regression exists.
- [ ] T036 Record Django model/migration evidence and update traceability without closing downstream work.

## Phase 3 - Test-first PostgreSQL, repository, and API mirror

- [x] T037 Add failing Django-owned PostgreSQL schema inventory and API semantic parity tests in `api/tests/test_content_migrations.py`; forbid duplicate API workspace tables.
- [ ] T038 Add failing PostgreSQL composite-key, check-constraint, index, transaction, and RLS tenant/site tests.
- [ ] T039 Add failing repository definition draft/preview/publish/retire and expected-version tests.
- [ ] T040 Add failing repository record CRUD/version/transition/restore/soft-delete tests.
- [ ] T041 Add failing relationship, saved-view, asset-binding, audit, and cross-tenant repository tests.
- [ ] T042 Add failing API capability and disabled-route tests.
- [ ] T043 Add failing definition endpoint schema, compatibility, confirmation, concurrency, and error-envelope tests.
- [ ] T044 Add failing record list/detail/create/update/delete/version/restore/transition contract tests.
- [ ] T045 Add failing cursor binding, stable ordering, page cap, sparse-field, filter, sort, expansion, and query-cost tests.
- [ ] T046 Add failing search scope, permission, injection, stale-index, degraded, and unavailable tests.
- [ ] T047 Add failing saved-view private/shared/revalidation and schema-change tests.
- [ ] T048 Add failing idempotency digest, replay, conflict, expiry, and concurrent-request tests.
- [ ] T049 Add failing mass-assignment, overfetching, unknown-key, oversized-body, nesting, decimal, timestamp, and locale tests.
- [ ] T050 Verify the ordered Django migration creates the exact PostgreSQL workspace schema and RLS prerequisites consumed by FastAPI; add no duplicate API migration.
- [ ] T051 Extend `api/repositories/site_content.py` with scoped transactions, authenticated-tenant-to-`site_id` equality, and no unsafe autocommit changes.
- [ ] T052 Implement typed Pydantic definition, field, workflow, record, query, view, job, response, and error schemas.
- [x] T053 Implement capability and definition routes under `api/routes/content_workspace.py` with the `/api/content/v1` contract.
- [ ] T054 Implement record, history, transition, and relationship routes.
- [ ] T055 Implement bounded query compiler, opaque cursor signing/validation, search interface, and saved-view routes.
- [ ] T056 Implement redacted append-only workspace audit calls for mutations and sensitive reads.
- [x] T057 Register OpenAPI contracts and keep public/generated reads distinct from authenticated administration.
- [ ] T058 Run API unit, contract, PostgreSQL, integration, migration, coverage, and negative suites.

## Phase 4 - Durable scheduling, indexing, import, export, and media jobs

- [ ] T059 Add failing worker tests for scheduled publication admission, timezone handling, restart, replay, cancellation, retry exhaustion, and terminal outcomes.
- [x] T060 Add failing indexing tests for committed versions, out-of-order jobs, stale markers, deletion, permission projection, and dependency outage.
- [ ] T061 Add failing media upload-grant, magic-byte, filename, type, size, dimension, count, quarantine, scan, derivative, and integrity tests.
- [ ] T062 Add hostile upload fixtures for MIME spoofing, polyglots, path traversal, active SVG, executable content, archives, and decompression/pixel bombs.
- [ ] T063 Add failing asset visibility, expiring delivery, cross-tenant binding, public/private mismatch, and required-asset publication tests.
- [ ] T064 Add failing JSON/CSV parser bound, encoding, heading, nesting, formula, unknown-field, and content-redaction tests.
- [ ] T065 Add failing import dry-run, mapping, row outcome, exact duplicate, fuzzy candidate, atomic commit, partial policy, replay, and interruption tests.
- [ ] T066 Add failing export authorization snapshot, redaction, formula neutralization, streaming, encryption, integrity, expiry, replay, and interruption tests.
- [x] T067 Implement durable scheduled publication and indexing tasks with bounded checkpoint/retry policy.
- [ ] T068 Extend canonical `sitecontent` media admission, quarantine, scan-state, safe derivative, binding, and access services without a second asset store.
- [ ] T069 Implement bounded streaming JSON/CSV parsing and staged validation outcomes.
- [ ] T070 Implement import review/commit with exact-first deduplication and review-only similarity candidates.
- [ ] T071 Implement permission-bound JSON/CSV exports with encryption, hashes, and expiring delivery.
- [ ] T072 Add worker health/evidence summaries containing only safe IDs, counts, hashes, durations, states, and error codes.
- [ ] T073 Run worker failure injection, restart, concurrency, replay, and secret-output suites.

## Phase 5 - Generator, presets, compatibility, and migrations

- [ ] T074 Add failing manifest tests for the workspace capability, preset versions, dependencies, unknown fields, and disabled defaults.
- [x] T075 Add failing deterministic preset compilation tests for articles, catalog, rentals/directories, portfolio, documentation, marketplace/listings, events, and community.
- [ ] T076 Add failing generated-profile matrix tests for models, migrations, API declarations, roles, routes, navigation, fixtures, tests, and migration notes.
- [ ] T077 Add failing disabled-capability tests across generator output, API, workers, navigation, direct routes, and public reads.
- [x] T078 Add failing `/api/items` compatibility adapter, warning, migration, and no-authority-expansion tests.
- [x] T079 Extend the existing module manifest with one workspace capability and declarative preset registry.
- [x] T080 Implement deterministic preset compiler using existing module IDs and shared canonical entities.
- [ ] T081 Generate bounded fixtures and contract declarations for every built-in profile/preset combination.
- [x] T082 Implement the narrow deprecated Items adapter and documented generated-site migration path.
- [ ] T083 Run generator determinism, clean-regeneration, upgrade/downgrade, disabled-profile, and compatibility matrices.

## Phase 6 - Test-first React workspace and generated views

- [ ] T084 Add failing API-client tests for tenant binding, schemas, errors, aborts, stale responses, cursors, and no browser credential persistence.
- [ ] T085 Add failing workspace shell, navigation, breadcrumb, capability, direct-route denial, and responsive list/detail tests.
- [ ] T086 Add failing definition/preset builder, field editor, compatibility preview, confirmation, and unsaved-change tests.
- [ ] T087 Add failing record list/search/filter/sort/page/saved-view and deterministic-state tests.
- [ ] T088 Add failing record create/edit/validation/conflict/compare/retry and value-preservation tests.
- [ ] T089 Add failing review, schedule, publish, archive, delete, history, diff, and restore journeys.
- [ ] T090 Add failing relationship picker, missing target, cycle, permission, and cross-scope UI tests.
- [ ] T091 Add failing media upload/progress/quarantine/rejection/ordering/alt-text/focal-point/publication-block tests.
- [ ] T092 Add failing import mapping/dry-run/review/duplicate/commit/job-state and export/download/expiry tests.
- [ ] T093 Add failing generated public list/detail renderer tests for every field kind and preset.
- [ ] T094 Add failing loading, empty, partial, malformed, dependency, permission, not-found, conflict, retry, cancelled, and terminal-failure state tests.
- [ ] T095 Add failing keyboard, screen-reader name/role/value, announcement, focus, target, contrast, reflow, reduced-motion, and axe tests.
- [ ] T096 Implement typed content API client and normalized error/job state handling.
- [x] T097 Implement capability-driven workspace shell and adaptive navigation.
- [ ] T098 Implement definition/preset builder and migration preview experiences.
- [ ] T099 Implement record browser, safe query builder, saved views, and stable URL state.
- [ ] T100 Implement typed field editors, validation summary, conflicts, and unsaved-change recovery.
- [ ] T101 Implement workflow, history/diff/restore, relationship, media, import, export, and job-status experiences.
- [ ] T102 Implement closed safe public/admin renderer registries and generated list/detail pages.
- [ ] T103 Remove the demonstration Items navigation only after compatibility parity and migration evidence pass.

## Phase 7 - Data integrity, privacy, and recovery assurance

- [ ] T104 Define measured schema, query, page, relationship, upload, import/export, job, bundle, and retention defaults/maxima from repeatable fixtures.
- [ ] T105 Add maximum-bound query-plan tests proving tenant/site leading indexes and bounded relationship expansion without N+1 growth.
- [ ] T106 Add concurrency tests for schema publication, record mutation, transition, saved-view edit, import commit, and schedule firing.
- [ ] T107 Add backup manifest tests covering definitions, records, versions, relationships, views, jobs, audit references, asset metadata, and object hashes.
- [ ] T108 Add isolated restore tests with exact counts, schema versions, referential integrity, content hashes, and no live-target access.
- [ ] T109 Add retention and hard-deletion tests for active relationships, recovery windows, audit preservation, export expiry, and exact-owned object cleanup.
- [ ] T110 Add privacy/data-rights projection tests proving workspace records enter authorized export/correction/deletion flows without leaking other tenants.
- [ ] T111 Add upgrade and rollback tests from current `main`, empty database, populated fixtures, old generated profile, and interrupted migration checkpoints.
- [ ] T112 Add safe rollback and restore operator support through both Bash and PowerShell entrypoints if a new command is required.
- [ ] T113 Verify shell parity, fixed arguments, path confinement, no arbitrary command/environment injection, and redacted artifacts for T112.
- [ ] T114 Run backup/restore, migration, rollback, retention, privacy, performance, and concurrency gates.
- [ ] T115 Record exact measured limits and operator recovery guidance in repository documentation.
- [ ] T116 Verify no duplicate canonical media, capability, role, audit, job, or tenant vocabulary was introduced.
- [ ] T117 Verify no public route exposes draft, private field, history, audit, owner identity, quarantined asset, or expiring internal URL.
- [ ] T118 Verify cache keys, search documents, cursor payloads, and exported projections bind tenant/site/type/schema/permission digests.
- [ ] T119 Verify every migration and background-job failure remains actionable, redacted, and explicitly non-successful.

## Phase 8 - Security, accessibility, visual, and full gates

- [ ] T120 Run direct tenant-crossing, role/object authorization, CSRF, IDOR, replay, concurrency, and anti-enumeration tests.
- [ ] T121 Run injection, XSS, structured-rich-text, mass-assignment, overfetching, unsafe URL, SSRF-boundary, path, MIME, archive, and CSV-formula tests.
- [ ] T122 Run dependency, static analysis, Semgrep, package audit, license, SBOM, supply-chain, and container/configuration security gates.
- [ ] T123 Run tracked, staged, history, artifact, screenshot, log, export, and fixture secret/private-data scans with zero findings.
- [ ] T124 Add deterministic synthetic visual fixtures for all field kinds, states, jobs, media outcomes, relationships, presets, errors, and long/RTL content.
- [ ] T125 Add representative Chromium route/state screenshots plus geometry, overflow, focus, target, hierarchy, image-fit, stability, and interaction assertions.
- [ ] T126 Add compact phone, DPR3 phone, short landscape, tablet, desktop, ultrawide, 200% text, and 400% zoom coverage.
- [ ] T127 Add light, dark, high contrast, reduced motion, keyboard, touch, Chromium, Firefox, and WebKit coverage where deterministic.
- [ ] T128 Add explicit visual manifest, artifact integrity, dimensions, route/state metadata, contact sheets, and human-readable review sidecar.
- [ ] T129 Prove ordinary tests cannot create/update baselines and unreviewed image drift fails closed.
- [ ] T130 Perform user-centered screenshot review for clarity, discoverability, density, hierarchy, clipping, motion, controls, errors, and mobile usability.
- [ ] T131 Add regression tasks for every reproducible visual/accessibility finding before changing implementation.
- [ ] T132 Repeat visual and accessibility capture/review until zero unresolved findings remain.
- [ ] T133 Run Django, API, PostgreSQL, worker, React, generator, E2E, migration, compatibility, and coverage suites.
- [ ] T134 Enforce at least 90% changed-line coverage and direct coverage of every critical authorization, workflow, migration, and data-loss branch.
- [ ] T135 Run the complete repository gate and repair every reproducible failure through a regression-first corrective task.
- [ ] T136 Require zero skipped required checks, unexplained infrastructure failures, silent degradation, or unresolved traceability gaps.

## Phase 9 - Implemented-system analysis and closeout readiness

- [ ] T137 Re-run product, architecture, security, migration, reliability, accessibility, visual, performance, compatibility, and operational analysis against the implemented system.
- [ ] T138 Add numbered corrective tasks for every new finding and link each to a regression test and evidence result.
- [ ] T139 Repeat implementation -> tests -> analysis -> corrective tasks until `NO_UNRESOLVED_IMPLEMENTATION_FINDINGS` is evidence-backed.
- [ ] T140 Re-run `validate_plan.py`, traceability, diff, documentation, and clean-tree review against the exact feature head.

## Phase 10 - Separate publication and optional live acceptance

- [ ] T141 Commit the exact reviewed feature changes and verify a clean tree without disturbing unrelated files.
- [ ] T142 Push the feature branch and publish a reviewed pull request only under the repository's publication authority.
- [ ] T143 Require every executable CI check green and classify infrastructure-only failures with retained evidence rather than bypassing them.
- [ ] T144 Merge only the exact reviewed head through a separate authorized decision and verify local/remote `main` alignment.
- [ ] T145 Admit an optional exact-main ephemeral canary only through separate provider, cost, lifetime, DNS, and deployment authorization.
- [ ] T146 Use synthetic tenant/accounts/content and staging-only certificates for live acceptance.
- [ ] T147 Run public, authenticated, admin, workflow, import/export, media, accessibility, responsive, visual, migration, worker, evidence, and rollback journeys live.
- [ ] T148 Perform exact-owned teardown and immediate idempotent teardown replay.
- [ ] T149 Verify empty Feature 104 provider inventory, no unrelated mutation, no production certificate, and no retained credential/material leak.
- [ ] T150 Record final evidence and close the feature only when every required task and requirement is complete.

## Implementation corrective tasks

- [x] T151 Replace the nested record-detail complementary landmark with an explicitly named region after the workspace axe regression reproduced `landmark-complementary-is-top-level`; rerun focused accessibility and interaction tests.
- [x] T152 Update the canonical Base2 Obsidian generated-profile assertion after the full affected gate reproduced a stale exact module set that omitted the enabled `content-workspace`; rerun the generator/profile matrix.
- [x] T153 Update the legacy scheduled-content fixture after the complete Django suite reproduced its missing now-required IANA display timezone; rerun the full Django suite before downstream gates.
- [x] T154 Add an encrypted exact-owned private artifact store after implementation analysis found no existing canonical object adapter for workspace media/import/export payloads; prove path confinement, authenticated context, integrity, permissions, replay, conflict, size bounds, and symlink rejection before integration.
- [x] T155 Complete the grant-bound raw media admission path after analysis found metadata-only grants had no content completion contract; add bounded streaming, exact owner/site/asset/hash/size binding, quarantine-only completion, encrypted storage, fail-fast production key validation, and setup/canary secret generation tests.
- [x] T156 Mount one shared private workspace-artifact volume into the read-only API and worker containers after Compose analysis found the new encrypted store was otherwise unwritable and unavailable across processes; pre-create its non-root path in the API image and validate the rendered Compose configuration.

## Dependencies and authority

Tasks are sequential by default. Within a phase, independent failing tests may run in bounded parallel only when they touch distinct files and resource admission permits it. Django canonical work blocks FastAPI mirror work; FastAPI blocks React integration; focused gates block full gates; implementation analysis blocks publication. T142, T144, and T145-T149 are separately governed actions and are not pre-approved by completion of earlier tasks.
