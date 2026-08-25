# Data Model: Base2 Universal Website Foundation

Persistent application entities begin in Django `common/models.py` or reviewed app adapters. This defines semantics, not final migrations.

## SiteManifest

- Schema version, site ID/slug/name/legal name
- Canonical/redirect/preview domains
- Brand tokens, logos, voice, navigation/footer/social links
- SEO, legal, locales, consent, analytics, contact, media, search
- Module versions/config references and operations/preview policy
- Created/updated time and digest

Invariants: strict schema; unique site/slug/domain; one canonical domain; safe URLs; valid module references; secrets are references, never values.

## ModuleDefinition and ModuleInstallation

Definition: ID/version/compatibility; models/migrations; API/UI routes; navigation; permissions/jobs/settings/health; data lifecycle; provider capabilities/dependencies; digest/source commit.

Installation: site/module/version; desired version; state (`planned|installed|enabled|disabled|upgrade_pending|removal_pending|failed`); config digest; migration; health/failure; actor/timestamps.

Invariants: unique routes/permissions, acyclic dependencies, no implicit provider activation, immutable released migrations.

## ContentRecord and ContentRevision

Tenant/site, stable ID/type/slug/locale, title/summary/structured body, `draft|review|scheduled|published|archived`, publication window, author/editor, access, SEO, canonical URL, revision/digest, redirects and timestamps.

## MediaAsset and MediaVariant

Tenant/site/owner, sanitized name, sniffed MIME, size/dimensions/digest/storage key, scan state, metadata policy, attribution/license; variants carry purpose/dimensions/encoding/size/digest. State: `pending|validated|quarantined|available|deleted`.

## Organization, Membership, Invitation, Role, Permission

Organization owns sites/data. Membership binds users and roles. Invitations are one-time hashed/expiring/revocable. Roles contain stable permissions; server policy denies by default.

## Authenticator, RecoveryCode, Session, ApiCredential

Authenticators cover TOTP/WebAuthn metadata; recovery codes are one-time hashes; sessions expose safe device/revocation state; API credentials store only hash, scope, expiry, owner, use, and revocation.

## AuditEvent

Immutable event/time, actor, tenant/site, action, target, outcome, request/run ID, privacy-filtered source metadata, redacted detail, prior-event digest. Append-only and tenant-authorized.

## FormDefinition, FormSubmission, OutboxMessage

Definition declares schema/consent/retention/notification/abuse policy. Submission stores normalized values/evidence/status/expiry/attachments. Outbox tracks bounded attempts, scheduling, provider class, delivered/dead-letter state.

## SearchDocument

Tenant/site, source/revision, locale/access, searchable fields/facets, publication/index times, digest, tombstone state.

## PreviewLease, ProviderResource, DnsMutation

Lease binds run/site/commit/manifest, owner, state, timestamps/TTL, cost policy, receipt digest. Resources use immutable provider ID/kind/region/tags. DNS mutations retain exact before/after and applied/verified/restored status.

States: `planned -> provisioning -> bootstrapping -> healthy -> observing -> teardown_due -> destroying -> destroyed`; failure retains evidence and permits bounded reconciliation.

## DeploymentEvidence and GateResult

Evidence binds run, commit, manifest, resources, stages, health, tests, costs, redaction, artifacts. Gate results include ID/applicability/status/times/exit/policy/logs/diagnostic.

## GeneratedSiteProvenance

Child repository ID, Base2 source commit, generator/profile/manifest digests, module inventory, transformation plan, generated commit, gate receipt, upgrade channel, compatibility and rollback.

## Lifecycle rule

Every entity declares owner, retention, export, deletion/anonymization, backup, restore, and audit behavior. Module disable preserves data but removes exposure/jobs. Removal requires preview, explicit policy, backup evidence, and destructive authority.
