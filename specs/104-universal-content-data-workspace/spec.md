# Feature Specification: Universal Content and Data Workspace

**Feature Branch**: `vscode-codex/104-universal-content-data-workspace`
**Created**: 2026-09-02
**Status**: Draft
**Input**: Give every Base2-generated website a secure, configurable, reusable content and data workspace that supports structured records, editorial workflow, search, media attachments, import/export, and generated user and administrator experiences.

## User Scenarios & Testing

### User Story 1 - Model a website's information without custom code (Priority: P1)

An authorized site administrator chooses a supported preset or defines a bounded content type, adds typed fields and validation, previews the resulting schema, and publishes a version that can store tenant-isolated records.

**Independent Test**: Create representative article, property, product, portfolio, documentation, directory, and community types; reject unsafe or incompatible definitions; publish a schema version; and prove records cannot cross tenant or site boundaries.

**Acceptance Scenarios**:

1. **Given** a supported site profile, **When** an administrator selects a content preset, **Then** Base2 creates a versioned draft definition with documented fields and no executable code.
2. **Given** a draft definition, **When** an administrator adds fields, constraints, and relationships, **Then** the preview reports validation and compatibility effects before publication.
3. **Given** two tenants with identical slugs, **When** either queries records, **Then** only its own type, record, asset, view, and history data is visible.

### User Story 2 - Create, review, publish, and recover content (Priority: P1)

An editor creates structured content, saves drafts, submits for review, receives actionable validation, publishes when authorized, archives records, examines version history, and restores an earlier version without losing audit evidence.

**Independent Test**: Exercise every valid and invalid transition, simultaneous edits, scheduled publication, archival, restoration, and relationship constraint with owner, editor, reviewer, viewer, and cross-tenant identities.

### User Story 3 - Find and organize useful records (Priority: P1)

A user searches, filters, sorts, pages, and opens structured records, then saves a private or role-shared view whose behavior remains stable as data changes.

**Independent Test**: Query a seeded multi-tenant data set through API and React at the maximum supported bounds; verify deterministic cursors, filter grammar, ranking, saved-view authorization, empty states, and no cross-tenant leakage.

### User Story 4 - Attach and present media safely (Priority: P1)

An editor uploads images or documents, sees scanning and processing status, supplies accessible metadata, chooses allowed visibility, orders multiple attachments, and uses them in generated record views.

**Independent Test**: Accept supported synthetic fixtures and reject spoofed, oversized, decompression-bomb, executable, path-traversal, SVG-script, and cross-tenant asset attempts; verify quarantine, derivative integrity, access rules, and accessible rendering.

### User Story 5 - Move data in and out without corruption (Priority: P2)

An administrator stages JSON or CSV data, reviews row-level validation and deduplication results, commits a valid import once, and requests bounded exports in documented formats.

**Independent Test**: Dry-run and commit valid, partially invalid, duplicated, replayed, oversized, formula-injection, stale-schema, and interrupted jobs; verify atomicity, resumability, redaction, expiring downloads, and restore equivalence.

### User Story 6 - Reuse the capability across generated sites (Priority: P1)

A Base2 operator enables only the required workspace presets in a site profile. The generator produces compatible Django, API, React, permission, navigation, fixture, and test declarations without creating a second capability vocabulary.

**Independent Test**: Generate every built-in profile and preset combination, validate disabled-capability denial, upgrade an older generated site, and prove deterministic regeneration with no manual edits.

### User Story 7 - Trust what the interface and reports say (Priority: P1)

Users receive visible loading, success, validation, conflict, dependency, permission, empty, partial, and retry states. Operators receive redacted diagnostics and integrity-bound evidence instead of silent success.

**Independent Test**: Inject database, object-store, scanner, worker, index, malformed-response, authorization, migration, and network failures; verify truthful UI states, bounded recovery, audit records, and complete artifacts without secrets.

## Edge Cases

- A field is renamed, constrained, reordered, deprecated, or removed while records and saved views still reference it.
- A relationship targets an archived, deleted, unavailable, or cross-tenant record.
- Two editors update the same record or schema version at the same time.
- A publication time crosses daylight-saving or locale boundaries.
- Search indexing lags behind a committed record or is temporarily unavailable.
- A user loses reviewer or administrator permission while a page is open.
- An import contains mixed encodings, duplicate headings, deeply nested JSON, spreadsheet formulas, unknown columns, or more rows than allowed.
- An upload claims one MIME type but contains another, has a dangerous filename, exceeds pixel/dimension limits, or fails scanning after upload.
- A public record references a private or quarantined attachment.
- A saved view exposes fields the viewer no longer has permission to read.
- A schema migration is interrupted between planning and application.
- Long translated labels, right-to-left text, 200% text, 400% zoom, reduced motion, keyboard-only use, screen readers, touch, and short landscape viewports.

## Requirements

### Functional Requirements

- **FR-001**: Base2 MUST provide one versioned content-workspace capability derived from the existing closed site/module manifest.
- **FR-002**: Authorized administrators MUST be able to create bounded draft content types from supported presets or typed fields without executable code, templates, queries, or scripts.
- **FR-003**: Supported field kinds MUST have explicit server-owned schemas, validation, defaults, limits, nullability, indexing eligibility, and presentation hints.
- **FR-004**: Content type names, field keys, record slugs, and preset identifiers MUST use stable normalized identifiers with tenant/site-scoped uniqueness.
- **FR-005**: Draft schema changes MUST expose a deterministic compatibility and migration preview before publication.
- **FR-006**: Published schemas MUST be immutable versions; later changes MUST create a new version with explicit forward, rollback, and restore behavior.
- **FR-007**: Destructive or lossy schema changes MUST require a separate deliberate confirmation and MUST never silently discard stored values.
- **FR-008**: Canonical domain entities MUST begin in Django and be faithfully mirrored in versioned FastAPI and PostgreSQL contracts before React integration.
- **FR-009**: Every type, field, record, version, transition, view, asset binding, import, export, and audit event MUST be isolated by tenant and site at application and database boundaries.
- **FR-010**: Workspace authorization MUST use closed roles and object actions for type administration, creation, editing, review, publication, archival, restoration, viewing, import, export, and audit access.
- **FR-011**: Disabled workspace capabilities or presets MUST expose no working navigation, API mutation, job, or generated route.
- **FR-012**: Records MUST support stable IDs, tenant-scoped slugs, typed values, relationships, lifecycle state, creator/updater, timestamps, and optimistic versions.
- **FR-013**: Record writes MUST validate against the exact published schema version and reject unknown, oversized, stale, or incompatible values.
- **FR-014**: Record mutations MUST require an expected version and return a non-mutating typed conflict instead of overwriting newer work.
- **FR-015**: The workflow MUST support draft, in-review, scheduled, published, archived, and soft-deleted states through an allowlisted transition graph.
- **FR-016**: Publication, schedule, archive, restore, and deletion permissions MUST be enforced server-side at mutation time.
- **FR-017**: Scheduled operations MUST be durable, timezone-safe, replay-safe, idempotent, bounded, observable, and recoverable after worker or host restart.
- **FR-018**: Every accepted mutation and sensitive read MUST produce a redacted append-only audit event linked to actor, tenant, site, object, action, and outcome.
- **FR-019**: Version history MUST preserve immutable snapshots and safe field-level diffs and allow authorized restoration as a new version.
- **FR-020**: Soft deletion MUST preserve integrity and recovery windows; hard deletion MUST be a separate retention-governed process with explicit relationship handling.
- **FR-021**: Relationships MUST enforce allowed type, tenant/site equality, cardinality, deletion policy, and cycle/depth bounds.
- **FR-022**: Listing and detail APIs MUST provide stable cursor pagination, allowlisted sorting, bounded filtering, sparse fields, and deterministic ordering.
- **FR-023**: Search MUST be tenant/site scoped, bounded, injection-safe, permission-aware, and explicit when results are stale, degraded, or unavailable.
- **FR-024**: Saved views MUST store a versioned allowlisted query description, be private by default, and require explicit role-scoped sharing.
- **FR-025**: A saved view MUST be revalidated against current schema and field permissions before every execution.
- **FR-026**: The workspace MUST provide accessible admin list, detail, create, edit, review, history, schema, import, export, and job-status experiences.
- **FR-027**: Generated user-facing list and detail experiences MUST use safe typed renderers and allowlisted presentation metadata, never stored arbitrary HTML or executable components.
- **FR-028**: Rich text MUST use a versioned structured-document allowlist, sanitize every write and render, and forbid scripts, inline event handlers, unsafe embeds, and untrusted remote fetches.
- **FR-029**: All UI mutations MUST display explicit pending, success, validation, conflict, permission, dependency, and retry states without silent fallback.
- **FR-030**: The UI MUST preserve unsaved values across recoverable errors and provide safe refresh/compare behavior for conflicts.
- **FR-031**: Attachments MUST reuse one canonical media capability and content-addressed identity rather than duplicate file stores per module.
- **FR-032**: Uploads MUST use bounded sizes/counts/dimensions, safe filenames, magic-byte verification, allowlisted media types, quarantine, malware scanning, and asynchronous derivative status.
- **FR-033**: Active SVG and other script-capable uploads MUST be sanitized and rendered from safe derivatives or rejected; raw unsafe content MUST never execute in the application origin.
- **FR-034**: The server MUST not fetch arbitrary user-supplied remote URLs; any future remote ingest requires a separately approved SSRF-safe capability.
- **FR-035**: Asset access MUST enforce tenant/site ownership plus private, authenticated, or public visibility through non-guessable, expiring delivery where appropriate.
- **FR-036**: Public records MUST not publish while referencing missing, quarantined, rejected, private, or unauthorized required assets.
- **FR-037**: Images MUST support alt text, caption, credit, focal point, ordering, and responsive derivative metadata.
- **FR-038**: Imports MUST have upload, parse, map, dry-run, review, commit, completed, failed, and cancelled states with durable replay-safe identity.
- **FR-039**: Import parsers MUST bound bytes, rows, columns, nesting, field lengths, encodings, and processing time and MUST produce row/field-level errors without logging submitted content.
- **FR-040**: Import commits MUST be atomic per declared batch policy, idempotent, schema-version bound, and explicit about create, update, skip, and duplicate outcomes.
- **FR-041**: Duplicate detection MUST use exact stable identifiers first and optional normalized candidate signals second; uncertain matches MUST remain reviewable, not automatically merged.
- **FR-042**: CSV handling MUST neutralize spreadsheet formula injection in exported cells and reject or safely preserve dangerous imported values according to documented policy.
- **FR-043**: Exports MUST be permission-filtered, redacted, bounded, asynchronous when large, integrity-bound, encrypted at rest, and available through expiring downloads.
- **FR-044**: JSON and CSV contracts MUST be documented and round-trip tested, including relationships, locales, timestamps, nulls, and schema versions.
- **FR-045**: Presets MUST cover articles/blogs, catalog/products, rentals/directories, portfolios, documentation, listings/marketplaces, events, and community content while composing existing modules.
- **FR-046**: Presets MUST be versioned declarative data, support deterministic generation, and remain removable when unused without deleting shared records or assets.
- **FR-047**: Generator output MUST include models/migrations, API capability declarations, React routes/components, roles, navigation, fixtures, tests, and migration notes appropriate to enabled presets.
- **FR-048**: Existing `/api/items` and demonstration UI behavior MUST receive an explicit compatibility, migration, or deprecation path; placeholder 501 behavior MUST not become an undocumented production contract.
- **FR-049**: Schema, API, generated-site, import, and export changes MUST include forward migration, compatibility, downgrade/rollback, backup, and isolated restore validation.
- **FR-050**: Backup and restore MUST preserve definitions, records, versions, relationships, views, jobs, audit references, asset metadata, and integrity hashes without restoring into a live production target during tests.
- **FR-051**: Tests MUST cover Django, SQL parity, FastAPI, PostgreSQL/RLS, workers, React, contracts, generator/profile matrices, migrations, backup/restore, and full repository gates.
- **FR-052**: Security tests MUST directly exercise tenant crossing, object authorization, CSRF, injection, XSS, unsafe rich text, SSRF boundaries, path traversal, MIME spoofing, malicious archives, replay, concurrency, mass assignment, overfetching, and secret leakage.
- **FR-053**: Accessibility MUST meet WCAG 2.2 AA with keyboard, screen reader, status announcement, focus, target size, contrast, reflow, language, and reduced-motion validation.
- **FR-054**: Visual assurance MUST cover every major route and state on compact phone, DPR3 phone, short landscape, tablet, desktop, ultrawide, 200% text, 400% zoom, light, dark, high contrast, reduced motion, and supported browser engines where deterministic.
- **FR-055**: Visual tests MUST assert geometry, overflow, obscured controls, focus visibility, target size, content hierarchy, image fit, loading stability, and interaction behavior in addition to screenshots.
- **FR-056**: Baseline changes MUST require an explicit human-readable review sidecar and MUST never be silently accepted or regenerated during ordinary tests.
- **FR-057**: All background and dependency failures MUST expose typed, redacted, actionable evidence and MUST never be reported as success.
- **FR-058**: Performance limits MUST bound schema complexity, query cost, page size, relationship expansion, upload processing, import/export work, and generated bundle growth.
- **FR-059**: Every requirement MUST map to at least one implementation task, automated test task, and acceptance/evidence task before implementation begins.
- **FR-060**: Any ephemeral live acceptance MUST use the established orchestrator, exact reviewed source, staging-only certificates, explicit cost and lifetime ceilings, exact teardown, replay-safe cleanup, and empty owned-provider reconciliation.
- **FR-061**: This feature MUST grant no authority to deploy, spend, create provider resources, alter DNS, issue production certificates, send messages, make payments, execute user code, merge pull requests, or delete unrelated data.
- **FR-062**: Implementation MUST proceed test-first in the constitutional order Django, FastAPI, then React, and every reproducible defect MUST create a regression task before correction.

### Key Entities

- **ContentTypeDefinition**: Tenant/site-owned, versioned description of a record kind and its workflow/presentation policy.
- **ContentFieldDefinition**: Ordered typed field contract belonging to one definition version.
- **ContentRecord**: Stable identity, slug, lifecycle state, schema version, optimistic version, and current typed values.
- **ContentRecordVersion**: Immutable record snapshot plus safe diff metadata and actor/time provenance.
- **ContentRelationship**: Validated directed relation with cardinality and deletion policy.
- **WorkflowDefinition**: Closed transition graph and action-to-role mapping.
- **SavedView**: Versioned, permission-scoped query description with safe filters, sorting, columns, and sharing.
- **AssetBinding**: Ordered association between a record field and canonical media asset plus accessible presentation metadata.
- **ImportJob**: Durable staged ingestion with source hash, schema binding, row outcomes, idempotency, and status.
- **ExportJob**: Durable permission-bound projection with format, integrity, expiry, and status.
- **WorkspaceAuditEvent**: Append-only redacted record of sensitive actions and outcomes.
- **ContentPreset**: Versioned declarative composition of types, fields, workflow, roles, presentation, fixtures, and tests.

## Success Criteria

- **SC-001**: All 62 functional requirements have implementation, automated-test, and evidence mappings with zero unresolved analysis findings.
- **SC-002**: A representative administrator can create a preset-backed content type and publish a valid record without code changes in ten minutes or fewer during moderated acceptance.
- **SC-003**: Every authorization, tenant-crossing, injection, XSS, unsafe-upload, replay, stale-version, and secret-output negative test fails closed.
- **SC-004**: Seeded searches return only authorized tenant/site records with deterministic order and pagination in 100% of test repetitions.
- **SC-005**: Valid JSON and CSV fixtures round-trip without semantic loss, while invalid and ambiguous inputs produce complete reviewable outcomes without partial silent commits.
- **SC-006**: Backup/restore comparison reproduces all required entity counts and integrity hashes in an isolated target.
- **SC-007**: Automated accessibility scans have zero serious or critical findings and manual keyboard/screen-reader scripts complete successfully.
- **SC-008**: Declared viewport/state/browser matrices complete with zero unresolved clipping, overflow, focus, target, hierarchy, or rendering findings.
- **SC-009**: Changed-line coverage is at least 90%, with every security-, authorization-, workflow-, migration-, and data-loss-critical branch directly exercised.
- **SC-010**: Full repository, generated-profile, migration, security, supply-chain, and separately admitted live gates pass with zero unexplained failures.
- **SC-011**: Any live canary teardown leaves zero Feature 104 provider resources and an immediate replay performs zero additional provider actions.

## Explicit Boundaries

- This feature does not implement a free-form page builder, arbitrary theme code, plugins, user scripts, or arbitrary SQL/query execution.
- It does not replace the future production media-library feature; it defines and consumes the safe canonical attachment boundary needed by records.
- It does not send email, direct messages, marketplace inquiries, or other outbound communications.
- It does not implement payments, fulfillment, booking engines, subscription billing, or third-party monitoring.
- It does not deploy a live site, spend money, mutate DNS, issue production certificates, merge a pull request, or destroy unrelated resources without separate established approval.
- “Complete testing” means complete specified traceability and regression coverage for discovered behavior; it cannot guarantee that unknown future defects are impossible.
