# Implementation Plan: Universal Content and Data Workspace

**Branch**: `vscode-codex/104-universal-content-data-workspace` | **Date**: 2026-09-02 | **Spec**: `spec.md`

## Summary

Replace Base2's placeholder item path with a reusable, tenant-isolated structured-content foundation. Canonical Django definitions and records lead the design, PostgreSQL and FastAPI mirror their semantics, workers handle durable scheduled/import/export/media operations, and React renders schema-driven administrator and user experiences through closed presets. Existing module manifests and media/site-content foundations are composed rather than forked.

## Technical Context

**Language/Version**: Python 3.12, JavaScript/TypeScript, SQL
**Dependencies**: Django, FastAPI, PostgreSQL/RLS, Celery/Redis, React 18, Vite, Playwright, Vitest
**Storage**: PostgreSQL for definitions and records; canonical private/public object storage boundary for media and export artifacts
**Testing**: pytest, Django tests, PostgreSQL integration, Vitest/jest-axe, Playwright, generator matrices, complete gate
**Target**: Containerized Linux, responsive browsers, generated Base2 sites, separately approved ephemeral DigitalOcean preview
**Constraints**: No executable schemas; closed field/filter/renderer vocabularies; bounded workloads; no arbitrary remote fetch; staging-only certificates; separate provider authority

## Constitution Check

- Constitution -> spec -> plan -> tasks -> code: PASS.
- Tests written before or alongside implementation: REQUIRED.
- Django canonical models before FastAPI mirrors before React: REQUIRED.
- Compose topology and supported script entrypoints: REQUIRED.
- PowerShell/Bash operator-script parity: REQUIRED for any new operator command.
- Redacted observable artifacts and fail-fast diagnostics: REQUIRED.
- Staging-only certificates and separate provider lifecycle authority: REQUIRED.

## Existing-system inventory

- `common/models.py` owns shared model primitives; `django/sitecontent/models.py` already owns concrete `ContentRecord`, `ContentRevision`, `MediaAsset`, `MediaVariant`, search, form, redirect, and publication behavior. Feature 104 evolves these entities and adds shared primitives in `common` rather than introducing parallel record or media tables.
- FastAPI already owns `api/routes/site_content.py`, `api/repositories/site_content.py`, tenant admission, audit, identity, privacy, scheduling, and public content/search routes.
- The React application already owns authenticated settings, accessibility, responsive, visual, and generated-profile test infrastructure.
- The module registry already declares blog, catalog, content, documentation, gallery, listing, marketplace, media, portfolio, community, events, forms, commerce, membership, booking, subscription, and support capabilities.
- `/api/items` and the Items UI are placeholders and require an explicit compatibility transition, not an accidental breaking replacement.
- Feature 103 established the closed capability vocabulary and exact generated-profile contract this feature must reuse.

## Architecture

### 1. Canonical definition and record layer

Extend Django's existing `sitecontent.ContentRecord`, `ContentRevision`, `MediaAsset`, and `MediaVariant` foundation and add definitions, fields, workflows, relationships, saved views, bindings, jobs, and audit references in the same canonical app. Shared validators and abstract primitives begin in `common/models.py`. Definitions use closed field kinds and structured presentation hints. Published schemas are immutable; schema evolution creates planned versions with compatibility classification. The current authenticated tenant ID maps exactly to canonical `site_id`; this feature does not introduce a second competing tenant/site identity.

### 2. PostgreSQL and FastAPI mirror

Create ordered SQL migrations with canonical site-scope constraints, row-level security, indexes, bounded JSON validation, and transaction-safe repository operations. Extend the existing site-content repository and public routes, and expose authenticated workspace endpoints under `/api/content/v1` with typed errors, optimistic preconditions, cursor pagination, sparse field selection, allowlisted filters/sorts, idempotency keys, and no mass assignment.

### 3. Durable worker layer

Use the existing worker/queue topology for scheduled publication, indexing, media derivative/scanning state, import validation/commit, and export generation. Jobs use source hashes and idempotency keys, survive restarts, cap retries, and retain truthful terminal outcomes.

### 4. Generated React experiences

Build an authenticated workspace shell and safe generated list/detail renderers. Renderers select from a closed field-component registry. All asynchronous actions surface loading, validation, conflict, permission, dependency, retry, and completion states. Disabled capabilities cannot be navigated to or invoked.

### 5. Preset composition

Add declarative presets for articles, catalogs, rentals/directories, portfolios, documentation, marketplace/listings, events, and community content. Presets reference existing module identifiers and generate deterministic definitions, roles, routes, fixtures, and tests without forking domain models.

## Field and query boundaries

- Initial field kinds: short text, long text, structured rich text, integer, decimal, boolean, date, datetime, enum, slug, URL, email, location, reference, references, image, file, and bounded JSON object.
- Client-supplied regular expressions, SQL, templates, scripts, HTML, component names, URLs to fetch, and arbitrary operators are forbidden.
- Filter operators are selected by field kind from a server allowlist. Relationship expansion, full-text fields, sort keys, page size, nesting, and saved-view columns are capped.
- Structured rich text stores a versioned allowlisted document tree and renders through sanitizing components.

## Security and privacy design

- Require authenticated tenant/site context and object action on every repository method and route.
- Reinforce application checks with composite foreign keys and PostgreSQL RLS where supported by the existing architecture.
- Use version and idempotency preconditions for mutations and background jobs.
- Sanitize rich text; escape all other text; apply CSP and safe download headers.
- Verify file signatures, quarantine before use, scan asynchronously, and isolate unsafe originals from the application origin.
- Do not dereference arbitrary remote URLs.
- Redact submitted values from logs; include only IDs, safe categories, counts, hashes, durations, status, and error codes.
- Bind export generation to the requesting principal's authorized projection and use expiring access.
- Neutralize CSV formula cells and use bounded streaming parsers.

## Schema-evolution strategy

1. Save changes to a draft definition version.
2. Compute additive, compatible, backfill-required, lossy, or forbidden classification.
3. Validate every saved view, preset, relationship, renderer, import mapping, and existing record against the candidate.
4. Require deliberate confirmation for backfill or lossy changes.
5. Apply through an idempotent migration job with checkpointed evidence.
6. Switch new writes only after completion; retain the prior version for rollback.
7. Restore by creating a new version; never rewrite immutable history.

## API strategy

- Namespace new authenticated workspace contracts under `/api/content/v1`; retain existing `/api/content`, `/api/search`, and `/api/media` generated public reads during compatibility migration.
- Use opaque cursor tokens bound to tenant, site, type, query digest, order, and expiry.
- Use `If-Match`/expected-version semantics for definitions, records, views, and state transitions.
- Return machine-readable error code, safe message, field issues, correlation ID, and current version where authorized.
- Keep `/api/items` available behind an explicit deprecated compatibility adapter until migration tests and release notes authorize removal.

## Visual and accessibility assurance

- Deterministic synthetic fixtures cover every field kind, workflow state, relationship shape, media state, error state, and preset.
- Pull requests run a representative Chromium matrix; release gates run the expanded browser, viewport, theme, zoom, motion, keyboard, touch, and screen-reader matrix.
- Screenshots are paired with geometry, overflow, focus, target, hierarchy, image-fit, state, and route assertions.
- Baselines are immutable during ordinary tests and require a review sidecar that explains intentional changes.

## Performance and reliability budgets

- Define explicit defaults and maxima for fields per type, records per page, filters, sorts, relationship depth, request body, uploads, derivatives, import rows, export rows, job duration, retries, and artifact retention.
- Query plans for representative maximum workloads must use tenant/site leading indexes and avoid unbounded N+1 expansion.
- Degraded search never broadens authorization or silently substitutes cross-scope results.
- Jobs resume from durable checkpoints or fail terminally with safe diagnostics; retries cannot duplicate writes.

## Delivery phases

1. Specification, inventory, contracts, threat model, traceability, and planning analysis.
2. Failing Django model, constraint, migration, workflow, and compatibility tests.
3. Canonical Django implementation and reversible migration.
4. Failing SQL/RLS/repository/API/worker tests, then FastAPI and worker implementation.
5. Failing generator/preset tests, then deterministic preset compiler changes.
6. Failing React unit/accessibility/interaction tests, then workspace and generated renderers.
7. Import/export, media-boundary, version-history, search, and saved-view completion.
8. Expanded security, migration, restore, performance, accessibility, and visual gates.
9. Implemented-system analysis and corrective-task cycles until no unresolved finding remains.
10. Publication and any live canary only through separate guarded decisions.

## Rollback

- All initial tables and manifest fields are additive; disabled capability defaults preserve existing generated sites.
- `/api/items` remains compatible until the documented adapter migration completes.
- Definitions and records retain schema-version binding, allowing application rollback without reinterpretation.
- Schema rollbacks use prior immutable versions and inverse plans; destructive columns/values are retained through the declared recovery window.
- Job and object-store outputs are exact-owned and content-addressed so rollback can remove only feature-owned artifacts.
- Live canary rollback uses the existing signed lease and exact teardown lifecycle.

## Authority boundaries

Planning and implementation may change repository files and run repository-local tests. Publication, merge, provider credential access, spending, DNS changes, deployment, production certificate issuance, external messaging, and provider teardown remain separate actions under their existing approval controls.
