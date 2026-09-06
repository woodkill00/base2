# Media library operations

## Scope and activation

The media library is an optional generated-site capability. `modules/media`
is the closed source of truth for its routes, permissions, jobs, limits, and
storage dependency. A profile that does not enable the module must expose no
Media navigation item and must not register `/api/media/v1`.

Enabling the module does not make stored originals public. New objects enter a
private quarantine workflow and remain unavailable for delivery until byte
inspection, a current malware scan, and safe derivative processing succeed.

## Accepted input

The checked-in policy permits JPEG, PNG, WebP, PDF, MP3, Ogg, MP4, and WebM up
to the profile's configured limit. It rejects active SVG, HTML, archives,
executables, remote URL ingestion, path-like names, bidirectional controls,
type/extension mismatches, invalid checksums, oversized batches, and stale
scanner definitions. Extension and browser-provided content type are hints;
server-side signature inspection decides admission.

Originals are immutable, encrypted, stored outside the webroot, and never
served inline. Browser delivery uses only approved safe derivatives with
`nosniff`, restrictive cache behavior, and a sandboxed content-security policy.
Object keys stay internal and are not serialized by public API responses.

## Runtime roles and tenant isolation

Normal requests use the non-superuser, non-`BYPASSRLS` workspace runtime role.
Workers use a distinct bounded worker role. The migration enables and forces
PostgreSQL row-level security on every new site-owned media table. Runtime
connections set the current tenant; cross-tenant reads and writes fail closed.
The worker may process queued records without accepting a caller-supplied
tenant bypass.

The release gate runs a disposable PostgreSQL 16 instance and proves forward,
reverse, and repeat-forward migration, forced-RLS inventory, bounded role
attributes, runtime tenant visibility, blocked cross-tenant insertion, and the
worker's fixed processing visibility. The container and synthetic credentials
are destroyed after each run.

## Processing and failure handling

Upload sessions are expiring and replay-bound. State transitions and version
updates are explicit; illegal transitions fail without mutation. Jobs have
bounded attempts and stable sanitized error codes. A rejected or failed object
does not receive an inline-safe derivative. A quarantine, scanner, storage, or
processor failure must remain visible as a terminal or retryable state rather
than disappearing from the queue.

Operators should investigate these conditions before retrying:

- `scanner_definitions_stale`: refresh the scanner definitions and verify their
  recorded timestamp before accepting more objects.
- `type_signature_mismatch` or `active_payload_rejected`: retain quarantine
  evidence; do not rename or manually release the source.
- `quota_exceeded` or `batch_limit_exceeded`: reduce the bounded request or
  adjust the versioned profile through review.
- `storage_integrity_failed`: isolate the object version and reconcile its
  digest; never overwrite the original in place.
- `derivative_failed`: inspect the sandboxed processor receipt and retry only
  under its existing bounded idempotency key.

## Retention, recovery, and rollback

Archive and soft delete preserve immutable object versions. Purge requires an
explicit planned state and is blocked by active references or retention holds.
Code rollback disables the capability surface but does not remove stored data.
Schema rollback is tested against synthetic data; production rollback should
use a compatibility-preserving forward migration and a verified backup.

Backup inventories must include the database, encrypted object store, key
identity metadata, and derivative provenance. Restore into an isolated target,
verify database constraints and object digests, then run tenant and delivery
checks before cutover.

## Release assurance

The browser matrix covers compact, high-density phone, landscape touch,
tablet, desktop, ultrawide, large text, 400% zoom, light theme, high contrast,
RTL, and reduced motion. Each run asserts no horizontal overflow, minimum
target size, visible keyboard focus, zero automated accessibility violations,
successful selection, and zero unexpected console or request failures. The
review sidecar binds the exact implementation commit and the twelve reviewed
screenshots.

Screenshots are synthetic and contain no credentials or user media. Publication,
merge, provider allocation, deployment, DNS changes, certificate issuance, and
resource teardown remain separate owner-approved operations.
