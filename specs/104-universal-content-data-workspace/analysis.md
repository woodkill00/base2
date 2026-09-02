# Analysis Log: Universal Content and Data Workspace

## Cycle 1 - Product, reuse, and compatibility

Findings:

1. A generic CRUD surface would not cover schema evolution, workflow, versions, review, saved views, media, or generated-site reuse.
2. Separate models for blogs, rentals, products, and listings would duplicate tenant, permission, migration, and UI behavior.
3. Base2 already has module manifests and capability handling; a second preset vocabulary would drift.
4. Existing `/api/items` and Items UI are placeholders but may still be referenced by tests or generated sites.
5. A free-form page builder would enlarge scope and introduce executable presentation risks.

Corrections:

- Defined one canonical structured-content kernel with versioned declarative presets.
- Added schema compatibility preview, immutable versions, workflow, search/views, media, import/export, and generated experiences.
- Required composition of existing module IDs and explicit disabled-capability tests.
- Added a narrow deprecated Items adapter, migration notes, and removal gate.
- Kept arbitrary code, HTML, templates, and page building outside the feature.

Remaining review areas: security of rich data, jobs, uploads, and tenant scoping.

## Cycle 2 - Security, privacy, and data-loss review

Findings:

1. Arbitrary JSON, query operators, relationships, rich text, and render hints could become mass-assignment, injection, XSS, overfetching, or denial-of-service paths.
2. Application-only tenant filters are vulnerable to a missed predicate.
3. Public records could leak private fields or unsafe attachments.
4. File extensions and client MIME values do not establish safe content.
5. Remote media ingestion would add SSRF risk.
6. Fuzzy deduplication could incorrectly merge distinct listings or posts.
7. CSV exports can execute formulas when opened in spreadsheet software.
8. Retried imports, exports, transitions, and schedules could duplicate mutations.
9. Logs, visual fixtures, and job evidence could expose submitted content or private download URLs.

Corrections:

- Added closed field/query/render/workflow vocabularies and explicit complexity bounds.
- Required tenant/site composite keys plus PostgreSQL RLS and deliberate UUID/slug collision tests.
- Added per-field public projection and asset-state/visibility publication gates.
- Added signature verification, quarantine, malware scanning, derivative isolation, hostile fixtures, and safe delivery.
- Excluded arbitrary remote fetch.
- Made exact identifiers authoritative and uncertain similarity matches review-only.
- Added CSV formula neutralization and corresponding hostile tests.
- Added digest-bound idempotency, optimistic versions, transaction ownership, checkpoints, and terminal replay tests.
- Added redacted evidence and repository/artifact/screenshot/export secret scans.

Remaining review areas: migration/restore honesty and complete user/visual behavior.

## Cycle 3 - Migration, reliability, accessibility, and visual review

Findings:

1. Editing published schemas in place would make old versions ambiguous and rollback unsafe.
2. Additive database migrations alone do not prove content-definition migrations, generated-site upgrades, or object-store restore.
3. Green container health does not prove workers, indexing, media processing, imports, or exports complete correctly.
4. Screenshot diffs alone do not prove focus, keyboard, announcements, overflow, targets, image fit, or interaction.
5. Running an unconstrained cross-product on every commit would waste resources and may hide skipped coverage.
6. “100% testing” cannot truthfully promise the absence of unknown future defects.
7. Planning could appear complete while a requirement lacks a real implementation, test, or evidence path.

Corrections:

- Made published definitions and record versions immutable and restoration append-only.
- Added content migration classification, compatibility preview, recovery windows, generated-site upgrade/downgrade, backup manifests, and isolated restore comparison.
- Added dependency/failure injection, restart, replay, terminal-state, and redacted worker evidence.
- Added behavioral assertions paired with screenshots and explicit visual review sidecars.
- Split representative pull-request coverage from expanded release coverage while forbidding silent required skips.
- Defined completeness as total specified traceability, direct critical-branch coverage, and regressions for discovered defects.
- Added a validator for exact requirement count, sequential tasks, completion honesty, traceability columns, boundaries, and unresolved markers.

## Cycle 4 - Task graph and authority review

Findings:

1. The initial task graph did not make the constitutional Django -> FastAPI -> React order mechanically obvious.
2. Media/import/export worker work could be implemented before repository transaction semantics were proven.
3. Compatibility removal could happen before generated-profile migration evidence.
4. Publication, merge, or live provider operations could be mistaken as implied by implementation completion.
5. Numeric performance limits chosen without measurement would be arbitrary.

Corrections:

- Reordered phases so canonical Django blocks SQL/API, which blocks workers/generator and then React.
- Placed worker implementation after API transaction/RLS tests.
- Made Items navigation removal depend on adapter, migration, and profile evidence.
- Separated publication, merge, and live canary into guarded Phase 10 and reiterated they are not pre-approved.
- Added repeatable maximum-workload measurement before numeric limits close.

**Current planning result**: `NO_UNRESOLVED_PLANNING_FINDINGS`

Implementation has not started. T019-T150 remain pending, and further implemented-system analysis is mandatory before publication or live acceptance.

## Cycle 5 - Exact repository-structure reconciliation

Findings:

1. Base2 already has concrete `sitecontent.ContentRecord`, `ContentRevision`, `MediaAsset`, `MediaVariant`, search documents, public routes, and a PostgreSQL repository. The initial wording could be read as permission to create duplicate record and asset systems.
2. The current tenant middleware maps authenticated tenant context to canonical `site_id`; adding both `tenant_id` and `site_id` now would create competing ownership identities.
3. The draft API base omitted Base2's established `/api` prefix and did not explicitly retain existing `/api/content`, `/api/search`, and `/api/media` public reads.
4. One Django test path targeted a nonexistent `django/common/tests` directory.
5. Two traceability ranges used inconsistent two-digit end labels.

Corrections:

- Required in-place evolution of the existing `sitecontent` records, revisions, media entities, repository, and routes; shared primitives still begin in `common/models.py` as required by the constitution.
- Defined authenticated tenant equality to canonical `site_id` and prohibited a second parallel ownership identifier in this feature.
- Corrected the authenticated base to `/api/content/v1` and retained existing generated public-read surfaces during migration.
- Corrected test and implementation destinations to real repository paths.
- Normalized all task ranges to three-digit identifiers.

**Final planning result after repository reconciliation**: `NO_UNRESOLVED_PLANNING_FINDINGS`

Implementation remains unstarted. T019-T150 remain pending, and publication, merge, or live-provider work remains separately governed.

## Cycle 6 - Physical schema ownership review

Finding:

1. Base2's API test bootstrap explicitly declares that Django owns the database schema. The original Phase 3 wording could have caused an API SQL migration to create a second copy of workspace tables or conflict with Django's migration state.

Correction:

- Kept the Django `sitecontent` migration as the sole physical schema owner. FastAPI will consume those exact tables, and API parity tests will verify PostgreSQL constraints, indexes, RLS prerequisites, and migration inventory while expressly forbidding duplicate `api_content_*` domain tables.

**Cycle result**: `NO_UNRESOLVED_SCHEMA_OWNERSHIP_FINDINGS`

## Cycle 7 - Implemented-system evidence reconciliation

Implementation is active on the private feature branch. Django remains the sole physical schema
owner, including PostgreSQL row-level security policies, while FastAPI consumes that schema and
React consumes the authenticated API. Corrective tasks are appended contiguously after T150 so
each reproduced implementation defect retains a regression and evidence path. Publication,
merge, deployment, DNS, certificates, provider resources, and live acceptance remain unperformed
and separately governed.

**Current implementation status**: `IMPLEMENTATION_ACTIVE_NOT_PUBLISHED`

## Cycle 8 - Exact-head database isolation review

Finding:

1. The exact-head complete gate passed, but the workspace RLS check remained a static migration inventory. The deployed compose contracts still supplied the table-owning PostgreSQL role to FastAPI and Celery. PostgreSQL owners bypass ordinary RLS, so this could not truthfully satisfy the planned second tenant boundary or T038 even though repository predicates and transaction-local tenant binding were present.

Correction:

- Added T193 to split migration ownership from API/worker runtime, provision a least-privilege no-`BYPASSRLS` role, grant it only the workspace access it needs, and prove real cross-tenant behavior against PostgreSQL including pool reset and rollback paths.

Evidence:

- The disposable PostgreSQL acceptance passed twice with synthetic credentials and exact-owned teardown.
- The exact-head complete gate at `e2f94d8b5635d94f92c3ab464377918e6ab050ef` passed all 80 required checks with no failure; changed-line coverage was 90.84%.

**Cycle result**: `IMPLEMENTATION_FINDING_T193_CLOSED`

## Cycle 9 - Remaining acceptance-depth review

Findings:

1. Repository and bound-limit tests exist, but the disposable PostgreSQL evidence does not yet prove tenant-leading execution plans, fixed-query relationship expansion, or all planned two-connection conflict classes.
2. Export expiry exists, while complete workspace retention, exact-owned media cleanup, and integration into the existing privacy/data-rights flow are not yet evidenced.
3. Migration round trips cover the current workspace schema, but the planned current-main/populated/prior-profile/interruption matrix and runtime-role grant rollback are incomplete.
4. Component accessibility and global Base2 visual matrices pass, but there is no dedicated workspace screenshot corpus covering every planned state, viewport, input mode, theme, engine, manifest, and review sidecar.

Corrections:

- Added T194-T197 as contiguous corrective tasks. T105-T132 and implemented-system closeout remain open until these deeper acceptance contracts pass.

**Cycle result**: `IMPLEMENTATION_FINDINGS_T194_T197_OPEN`

T194 progress: the disposable PostgreSQL matrix now retains an actual planner
assertion showing tenant/type access through `sitecontent_type_version_uq`, and
the relationship repository is regression-tested to return 25 expansions with
one bounded `LIMIT 200` query. T105 is closed; the multi-connection mutation
matrix remains open under T106/T194.

T194 closeout: the disposable PostgreSQL matrix now launches two physical
least-privilege runtime-role sessions through a bounded barrier for each of six
critical collision classes. Definition publication, record mutation, workflow
transition, saved-view edit, import commit, and due-schedule firing each produce
exactly one affected-row winner and one zero-row loser. The disposable database
is destroyed even on failure, and the static contract locks the race classes,
physical barrier, and winner/loser assertion into the required gate.

**Cycle result**: `IMPLEMENTATION_FINDING_T194_CLOSED_T195_T197_OPEN`
