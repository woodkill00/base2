# Research and Decisions: Universal Content and Data Workspace

## Local foundation reviewed

- Base2's constitution and Django -> FastAPI -> React build order.
- Existing site profiles, module manifests, capability registry, generator, settings platform, site-content API, audit, privacy, scheduling, worker, visual, and DigitalOcean lifecycle contracts.
- Existing placeholder `/api/items` surface and demonstration Items UI.
- Feature 103's typed capability, optimistic concurrency, authenticated visual, failure-reporting, migration, and live-acceptance patterns.

## Decisions

### D1 - One structured-content kernel, many presets

Use one canonical definition/record/version/workflow engine. Blogs, products, rentals, directories, portfolios, documentation, marketplace listings, events, and community posts are declarative presets that compose existing module IDs. Separate per-feature databases would multiply security, migration, import/export, and UI drift.

### D2 - Closed schemas, not user code

Definitions select typed fields, validation rules, transition actions, and safe render hints from server-owned registries. They cannot include Python, JavaScript, SQL, regular expressions, arbitrary HTML, templates, shell, component imports, or remote URLs to fetch.

### D3 - Immutable published schemas

A published definition is never edited in place. Changes create a candidate version and deterministic migration assessment. This keeps historic records interpretable and makes rollback and restore evidence honest.

### D4 - Stable record identity plus immutable history

`ContentRecord` owns the stable identity and current pointer. Every accepted change creates a `ContentRecordVersion`. Restoration creates a new version rather than rewriting history.

### D5 - Workflow as an allowlisted state machine

Transitions are declared from a closed state/action vocabulary and checked against current role, current state, expected version, schedule rules, and current permissions at execution time.

### D6 - Safe query description

Filters, sorts, columns, and relationship expansions use a typed AST whose operators are derived from field kinds. Opaque cursors bind query digest and scope. There is no free-form query language.

### D7 - Database and application tenant enforcement

All keys and relationships carry tenant/site scope. Repository admission always establishes scope, and PostgreSQL constraints/RLS provide a second boundary. Tests deliberately reuse UUIDs and slugs across tenants to expose missing predicates.

### D8 - Canonical media boundary

Records bind to canonical content-addressed assets. Uploads are quarantined until signature validation, scanning, metadata processing, and safe derivative generation complete. Unsafe originals are never rendered in the application origin. Remote URL ingestion is excluded.

### D9 - Review-first imports

Imports stage immutable source metadata, bounded parsed rows, mappings, and outcomes before commit. Exact identifiers may update when explicitly selected. Similarity signals create review candidates and never auto-merge uncertain records.

### D10 - Export the authorized projection

Export jobs freeze the requester's permitted field projection and scope at admission, recheck job ownership for download, encrypt stored output, neutralize spreadsheet formulas, and expire delivery access.

### D11 - Reuse the manifest vocabulary

The workspace and presets extend the established module/capability manifest. The API and React client consume generated safe metadata rather than maintaining parallel feature-name lists.

### D12 - Explicit placeholder migration

The current Items endpoints and UI are treated as a documented deprecated demonstration surface. A compatibility adapter and release notes precede removal; new workspace behavior is not hidden behind an unchanged placeholder contract.

### D13 - Behavioral visual assurance

Screenshots are evidence, not the whole test. Every captured journey also asserts route/state identity, geometry, overflow, focus, target size, image fit, loading stability, announcements, and major interactions. Ordinary tests cannot rewrite baselines.

### D14 - Honest completeness

The feature targets 100% requirement-to-implementation/test/evidence traceability, direct critical-branch coverage, and regression tests for every discovered defect. It does not claim to eliminate unknowable future defects.

## Rejected alternatives

- **Arbitrary JSON blobs**: easy initially, but weak validation, indexing, migrations, and security.
- **Dynamic database tables per content type**: costly migrations and operational complexity for generated sites.
- **Entity-attribute-value rows for every scalar**: poor query clarity and performance; bounded typed JSON with indexed projections is simpler while definitions remain canonical.
- **Client-only authorization/filtering**: cannot protect direct API or database access.
- **Automatic fuzzy duplicate merging**: can destroy distinct listings or records; uncertain candidates require review.
- **Raw SVG/HTML rendering**: expands XSS and origin-trust risk.
- **Synchronous large imports/exports**: vulnerable to timeouts, partial work, and replay duplication.
- **Building a new module registry**: would drift from generator and settings capabilities.
- **Always-on live preview**: conflicts with Base2's bounded-cost ephemeral provider lifecycle.

## Open implementation measurements

Exact numeric defaults for field count, query complexity, upload dimensions, import/export rows, retention, and performance budgets must be established from repeatable local maximum-workload tests before their implementation tasks close. The API exposes limits so clients never guess them.
