# Data Model: Universal Content and Data Workspace

All canonical entities begin in Django. Shared primitives begin in `common/models.py`; concrete workspace entities extend the existing `django/sitecontent` app. PostgreSQL/FastAPI mirrors preserve names, types, constraints, lifecycle, and canonical site ownership. The currently authenticated tenant ID maps exactly to `site_id`; Feature 104 does not create a second parallel ownership identifier. UUIDs are server-generated. Timestamps are UTC. Public identifiers never substitute for authorization.

## ContentTypeDefinition

- `id`, canonical `site_id`, stable `type_key`, display name, description.
- `version`, `status` (`draft|migration_pending|published|retired|failed`).
- `preset_id`, `preset_version`, workflow reference, presentation metadata version.
- `previous_definition_id`, compatibility class, migration-plan digest.
- optimistic `lock_version`, creator/updater, created/updated/published timestamps.
- Unique `(tenant_id, site_id, type_key, version)` and one active published pointer.
- Published rows are immutable; changes are copied into a new draft.

## ContentFieldDefinition

- Definition ownership plus stable `field_key`, label, description, field kind, order.
- Required/null/default rules; scalar/list/cardinality limits; uniqueness/index flags.
- Closed validation object and closed presentation-hint object.
- Relationship target type and deletion policy when applicable.
- Visibility/read/write action requirements.
- Unique `(definition_id, field_key)`.

Initial field kinds: `short_text`, `long_text`, `rich_text`, `integer`, `decimal`, `boolean`, `date`, `datetime`, `enum`, `slug`, `url`, `email`, `location`, `reference`, `references`, `image`, `file`, and `json_object`.

## WorkflowDefinition

- Tenant/site/type scope, version, states, initial state, transition declarations.
- Each transition contains stable action, allowed sources, destination, required object action, scheduling eligibility, and validation gates.
- State and transition vocabulary is bounded; no hooks or executable expressions.

## ContentRecord (existing entity, evolved)

- Existing `sitecontent.ContentRecord` is migrated in place; no parallel record table is introduced.
- `id`, canonical `site_id`, `type_key`, active definition/version.
- site-scoped stable `slug`, lifecycle state, current version pointer.
- bounded canonical values object plus indexed scalar projections selected by schema.
- optimistic `lock_version`, creator/updater, created/updated/published/archived/deleted timestamps.
- Soft-deletion and retention metadata; no implicit hard delete.
- Unique live `(tenant_id, site_id, type_key, slug)`.

## ContentRecordVersion (evolves existing ContentRevision)

- Record ownership, monotonically increasing version, exact schema version.
- Immutable canonical values snapshot, lifecycle state, safe diff summary.
- action/reason, actor, correlation, created timestamp, snapshot SHA-256.
- Restoration creates a new version whose provenance names the restored version.

## ContentRelationship

- Tenant/site scope, source record/version/field, target record, order.
- Enforces allowed target type, cardinality, scope equality, uniqueness, and deletion policy.
- Relationship expansion is depth- and count-bounded.

## SavedView

- Owner tenant/site/user, type key, version, title.
- Typed filter AST, allowlisted sort list, selected fields, optional relationship expansions.
- visibility (`private|role_shared`) and allowlisted roles.
- schema version, query digest, optimistic lock version, timestamps.
- Revalidated against current permissions and schema before every use.

## MediaAsset (existing entity) and AssetBinding

Existing `sitecontent.MediaAsset` and `MediaVariant` remain the canonical media-capability entities and are extended where required: content hash, size, detected type, safe filename, dimensions, scan/processing status, visibility, object key, derivative metadata, integrity, retention, canonical site owner, and timestamps.

`AssetBinding` associates a record version and field with one asset plus order, alt text, caption, credit, and focal point. Cross-scope bindings are forbidden. Published required bindings accept only safe terminal asset states.

## ImportJob and ImportRowOutcome

- Job: tenant/site/type, requester, source asset/hash, parser version, schema version, mapping, duplicate policy, atomic policy, idempotency key, status, bounded counters, error code, timestamps.
- States: `uploaded|parsing|mapped|validated|review_required|committing|completed|failed|cancelled`.
- Row outcome: ordinal, source-row hash, proposed action (`create|update|skip|review|reject`), field issues, exact match, candidate IDs, result record/version.
- Raw submitted content is not written to logs or audit messages.

## ExportJob

- Tenant/site/type, requester, frozen authorized projection digest, query digest, format (`json|csv`), schema version, idempotency key, status, counts, encrypted object reference, SHA-256, expiry, error code, timestamps.
- Downloads require current job ownership/authorization and an unexpired delivery grant.

## WorkspaceAuditEvent

- Append-only event ID, tenant/site, actor, safe object type/ID, action, outcome, correlation ID, request/job ID, timestamp, safe count/hash metadata.
- Submitted values, tokens, cookies, credentials, raw files, and private download URLs are excluded.

## ContentPreset

- Repository-owned manifest: stable ID/version, required module IDs, type definitions, field definitions, workflow, roles/actions, presentation hints, routes, fixtures, tests, and migration notes.
- Presets are validated, deterministic, and contain no secrets or executable content.

## Invariants

1. Every mutable row includes canonical `site_id`; authenticated tenant context must equal it, and every reference proves the same scope through composite constraints or equivalent transactional checks.
2. Published schemas and record versions are immutable.
3. Current pointers advance in one transaction with expected-version admission.
4. Unknown field kinds, validation keys, query operators, render hints, workflow states/actions, and job states fail closed.
5. Public delivery never bypasses record state, field visibility, asset visibility, or quarantine state.
6. Job idempotency is unique within tenant/site/operation and binds the request digest.
7. Hard deletion cannot orphan required relationships, immutable audit evidence, or legal retention.
8. JSON object depth, keys, serialized bytes, and value types are bounded.

## Migration and compatibility

- Django migration lands first; ordered API SQL migration mirrors it and is included in executable runner inventory.
- Existing tenants receive no enabled workspace capability unless their site profile opts in.
- Existing Items routes use a deprecated adapter during the compatibility window.
- Definition migration plans classify each field change and retain pre-migration values through the recovery window.
- Backup manifests bind database snapshot, object inventory, schema/preset versions, and hashes; restore tests target an isolated database and object prefix only.
