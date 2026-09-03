# Content Workspace API Contract v1

Authenticated workspace base path: `/api/content/v1`. All workspace endpoints require the established authenticated tenant context, which maps exactly to canonical `site_id`. Capability admission, object authorization, CSRF/cookie rules, rate limits, and audit policy apply before business logic. Existing `/api/content`, `/api/search`, and `/api/media` remain the generated public-read compatibility surfaces.

## Capability and definitions

- `GET /api/content/v1/capabilities` returns safe enabled types, presets, actions, field kinds, renderer versions, and server limits.
- `GET /api/content/v1/types` lists authorized definitions with opaque cursor pagination.
- `POST /api/content/v1/types` creates a draft from a preset or typed definition.
- `GET /api/content/v1/types/{type_key}/versions/{version}` reads an authorized definition.
- `POST /api/content/v1/types/{type_key}/versions/{version}/preview` validates and returns compatibility/migration effects without mutation.
- `POST /api/content/v1/types/{type_key}/versions/{version}/publish` requires expected version and deliberate confirmation when classified as backfill-required or lossy.
- `POST /api/content/v1/types/{type_key}/versions/{version}/retire` retires future use without rewriting records.

## Records and workflow

- `GET /api/content/v1/types/{type_key}/records` accepts an allowlisted filter AST, sorts, fields, expansions, limit, and opaque cursor.
- `POST /api/content/v1/types/{type_key}/records` creates a draft against the exact active schema.
- `GET /api/content/v1/types/{type_key}/records/{record_id}` returns authorized fields and current version.
- `PATCH /api/content/v1/types/{type_key}/records/{record_id}` requires `If-Match` or `expected_version` and only schema-declared writable fields.
- `DELETE /api/content/v1/types/{type_key}/records/{record_id}` performs permissioned soft deletion with expected version.
- `POST /api/content/v1/types/{type_key}/records/{record_id}/transitions/{action}` performs one allowlisted state transition and optionally validates a schedule.
- `GET /api/content/v1/types/{type_key}/records/{record_id}/versions` lists safe immutable history.
- `POST /api/content/v1/types/{type_key}/records/{record_id}/versions/{version}/restore` creates a new current version.

## Saved views

- `GET/POST /api/content/v1/types/{type_key}/views`
- `GET/PATCH/DELETE /api/content/v1/types/{type_key}/views/{view_id}`
- `POST /api/content/v1/types/{type_key}/views/{view_id}/execute`

Every execution revalidates schema, fields, operators, scope, and caller permissions. Views are private unless explicit role sharing is authorized.

## Media bindings

- `POST /api/content/v1/assets/uploads` admits metadata and returns a bounded upload grant to the canonical media service.
- `GET /api/content/v1/assets/{asset_id}` returns safe status/metadata only when authorized.
- `POST/DELETE /api/content/v1/types/{type_key}/records/{record_id}/assets/{field_key}` manages bindings with expected record version.

Uploaded objects remain quarantined until verification, scanning, and derivative processing reach an allowed terminal state. There is no remote-URL fetch endpoint.

## Import/export jobs

- `POST /api/content/v1/types/{type_key}/imports` creates a staged job bound to source hash, schema, mapping, policy, and idempotency key.
- `GET /api/content/v1/types/{type_key}/imports/{job_id}` returns safe counters, state, and bounded field/row issues.
- `POST /api/content/v1/types/{type_key}/imports/{job_id}/commit` commits an already validated job once.
- `POST /api/content/v1/types/{type_key}/imports/{job_id}/cancel` cancels only before a terminal commit.
- `POST /api/content/v1/types/{type_key}/exports` creates a permission-bound export job.
- `GET /api/content/v1/types/{type_key}/exports/{job_id}` returns status and integrity metadata.
- `POST /api/content/v1/types/{type_key}/exports/{job_id}/download` creates a short-lived owner-bound delivery grant when complete.

## Public generated reads

Generated profiles MAY expose separate cacheable read-only routes for published records. Those routes return only declared public fields, never drafts/history/audit/private assets, and retain tenant/site/type binding. Public routes cannot accept relationship depth or arbitrary field projection beyond server-declared bounds.

## Request semantics

- JSON bodies reject unknown keys and enforce byte, depth, collection, and scalar limits.
- Mutation replay uses an `Idempotency-Key` bound to principal, scope, operation, and canonical request digest.
- Optimistic mutations use strong entity versions through `If-Match` and response `ETag` where HTTP semantics fit.
- List cursors are opaque, signed, expiring, and bound to tenant, site, type, query digest, ordering, and page limit.
- Dates and times use ISO 8601; persisted timestamps are UTC; scheduled input retains declared IANA timezone for display/audit.
- Decimal values are serialized without binary floating-point loss.

## Typed response and error envelope

Success responses include `data`, safe `meta`, and `correlation_id`. Errors include:

```json
{
  "error": {
    "code": "content_version_conflict",
    "message": "The record changed before this update was saved.",
    "field_issues": [],
    "current_version": 7,
    "retryable": false,
    "correlation_id": "synthetic-safe-id"
  }
}
```

Allowlisted codes include `content_capability_disabled`, `content_not_found`, `content_forbidden`, `content_schema_invalid`, `content_schema_incompatible`, `content_version_conflict`, `content_transition_invalid`, `content_query_invalid`, `content_limit_exceeded`, `content_asset_quarantined`, `content_dependency_unavailable`, `content_job_not_ready`, `content_job_terminal`, `content_idempotency_conflict`, and `content_integrity_failed`.

Not-found and forbidden behavior follows the repository's anti-enumeration policy. Errors never contain submitted values, SQL, stack traces, storage keys, credentials, tokens, private URLs, or cross-tenant existence clues.

## Compatibility

The existing `/api/items` contract remains deprecated behind a narrow adapter until migration evidence is complete. It cannot gain broader workspace authority accidentally. Removal requires release notes, generated-site migration, contract tests, and a separately reviewed breaking-change decision.

## Explicit exclusions

No endpoint accepts executable code, arbitrary HTML, SQL, regular expressions, remote-fetch URLs, provider credentials, deployment instructions, payment actions, or outbound-message commands.
