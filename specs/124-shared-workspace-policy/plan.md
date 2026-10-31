# Feature 124 technical plan

Status: implementation contract frozen after independent boundary review on 2026-10-31;
accepted for scoped local implementation, not runtime/release acceptance.

## Evidence and architecture order

Read constitution/AGENTS and Feature 121. Existing anchors: `api/routes/settings.py`,
`api/repositories/settings.py`, `api/repositories/identity_admin.py`,
`api/security/identity.py`, `django/{common,users,sitecontent}/models.py`,
`api/routes/content_workspace.py`, `api/services/content_workspace_worker.py`,
`api/migrations/sql/005_create_identity_admin_tables.sql` and `008_create_settings_tables.sql`.
Existing notification replacement deletes/inserts without a set version and reads
back after commit. WorkflowDefinition already has review/publish/schedule states and
transitions; scheduled publication currently needs the new policy enforcement seam.
EmailOutbox, TenantNotification, workspace jobs and media outbox are reusable patterns,
not proof that review delivery already exists.

Mandatory sequence: canonical primitives in `django/common/models.py`, Django adapters/
migrations/tests, mirrored FastAPI contracts/repositories/workers/tests, React last.
Do not create a second independent domain definition in raw SQL or generic record JSON.
Existing Django operator Organization/User objects and API public identity tables are
separate realms: do not assume matching UUIDs or silently join them. Define common
scope/value semantics, with explicit adapters for the existing runtime tables.

## Scope keys, authorization and precedence

- `site_id == tenant_id == SITE_MANIFEST.siteId` for this deployment. Verify the exact
  manifest field spelling in implementation; never introduce an in-session selector.
- Runtime `api_identity_organizations.tenant_id` is unique. Resolve organization ID
  from that row and active membership, not a body/query parameter. Policy is keyed
  by site/tenant with the resolved organization association; reject inconsistent mapping.
- Personal notification-set key: `(tenant_id, public_user_id)`; no org inheritance.
- Shared policy key: `tenant_id`, one policy version encompassing both fields, with
  organization association checked server-side. No extra org/site cascade when they
  are one runtime scope. `require_review` is organization-governed; `public_access`
  is site-content scope. Effective permission is intersection of deployment/module
  enablement, shared policy, existing resource permission and active membership.
- Explicit new `workspace-policy.read/write` permissions: active owner/admin read/write,
  editor/viewer safe read only. Existing publish permission remains owner/admin;
  scheduling keeps existing role permissions but cannot evade approval.
- All server/worker/search/export/asset paths enforce the same effective decision.
  A missing organization makes shared mutation unavailable; it must not create an
  organization or grant permissions as a settings side effect.

## Canonical state and API interfaces

Names below are implementation contracts; file placement may follow existing adapters.

1. **NotificationPreferenceSet** common abstract primitive and users adapter. Runtime
   mirror table `api_notification_preference_sets`: UUID primary key `id`, `user_id`
   UUID referencing existing public-auth identity, `tenant_id` bounded existing tenant
   identifier, `schema_version` smallint default/check 1, `version` bigint >=1,
   `created_at/updated_at`; unique `(user_id,tenant_id)`. Django operator and runtime
   public identity adapters preserve their own identity realms, never join by UUID.
   The users wrapper preserves existing AuthUser FK + nullable Organization FK with
   separate conditional uniqueness for global/default and organization scopes;
   backfill each distinct existing Django choice scope at version 1 without changing rows. Existing rows remain normalized choices. Backfill
   a version-1 set for existing rows; absent set is version 0. Lock/CAS the parent and
   replace validated rows in the same transaction, return that transaction's snapshot.
   Concurrent initial insert has one winner and one typed conflict. Maintain required `security/email` and `transactional/email` rows on replacement:
   omitted pair retains its saved value or defaults to immediate. Retain any existing
   security/transactional rows on other channels if omitted, but do not invent new
   channels. Submitted security/transactional disabled is rejected. Optional rows are
   replaced. An empty request retains required rows; header CAS still advances.
   Mandatory classification remains server-derived, not an accepted mutation field.
   Preserve existing optional rows/default semantics, never silently opt users into
   a newly wired consumer: missing product/email means disabled for review delivery. Use the existing product/email control and label its review-notification effect
   test-adapter-only. No new in-app preference, inbox, browser channel or live email
   activation is introduced. The local sink proves delivery, not a live provider.
   `GET /api/settings/notifications` adds `schema_version`, `version` to `preferences`.
   PUT requires `expected_version`; legacy unversioned writes fail with a documented
   422 validation error rather than retain an unsafe bypass. Coordinate API/client rollout;
   old GET consumers tolerate additive fields, old writers must reload/upgrade.
2. **WorkspacePolicy** common primitive: scope, schema_version=1, version,
   `require_review: bool`, `public_access: public_allowed|members_only`, timestamps.
   Proposed `GET/PUT /api/settings/workspace-policy`; PUT closed body contains
   expected_version and both typed fields, never caller-controlled tenant/org.
   GET returns values plus safe scope/provenance/permissions. Conflict is 409;
   malformed/unknown fields 422; missing write precondition 422; dependency failure 503, no default
   permissive fallback. Audit and mutation commit atomically.
3. **ReviewApproval** common primitive/adaptor: tenant, record, immutable semantic content revision/fingerprint,
   policy version, reviewer identity and timestamp. Preserve review subject author /
   submitter and invalidate approval on edits; cannot approve own authored/submitted
   revision. Add an explicit approval action/endpoint without treating `in_review` as
   approved. Keep existing workflow compatibility: author submits, authorized independent
   owner/admin approves, existing authorized publish or schedule consumes valid approval.
   The canonical fingerprint includes every publication-affecting field: content_type,
   slug, title, excerpt, body, complete publicly served metadata, values, definition ID
   and schema_version, sitemap_include/search_visible; ordered relationship semantics;
   and complete binding presentation fields (field_key/order/alt_text/caption/credit/
   focal coordinates) plus immutable asset object-version identity and content digest.
   Changing bytes under the same asset ID is a semantic change for all bound subjects.
   Exclude only operational state, row.version, created_at/updated_at/published_at/
   deleted_at, publish_at/schedule_timezone and worker bookkeeping; these remain
   separately authorized lifecycle/schedule inputs, not permission bypasses. Do not
   exclude publicly served metadata as if it were operational bookkeeping. Canonical
   serialization is deterministic and shared across Django/API tests. All writes,
   including native Django edits, restore/import and asset replacement, invalidate
   affected approvals and demote published records under required review atomically.
   State-only schedule/publish transitions carry the approval forward without changing
   the semantic revision; literal mutable row.version alone is not the review identity.
   Approval does not itself publish or broaden permissions. Store schedule authorization
   context and recheck reviewer/publisher/scheduler membership as applicable when due.
   Policy/record updates and approval/publish use policy -> content -> membership lock order and transaction
   snapshot so a policy race cannot publish without the new requirement.
4. **Review notification intent**: atomically enqueue with successful submit-review,
   referencing tenant, record, submitted semantic revision and unique review-submission cycle identity (a later
   return-draft/resubmit creates a new event even with unchanged content), not copied private
   body. Uniqueness includes event, recipient and channel. Reuse/adapt TenantNotification/
   outbox patterns only after verifying their storage and worker compatibility. Public
   APIs never select arbitrary recipients. Required-review recipients are current
   independent owner/admin reviewers; optional-workflow recipients are authorized
   publishers other than the requester. Consumer supports product/email only, local durable test sink;
   no network/email operation. Immediate delivery, suppression and daily UTC digest are
   explicit states; group digest by tenant/recipient/UTC day with frozen membership and a batch ID
   unique effect key. Each intent is assigned/consumed exactly once; arrivals after
   batch closure belong to the next eligible batch, never silently dropped.
   On delivery, recheck content pending review, membership, preference and policy; stale
   events become suppressed. Retry has bounded attempts/backoff and durable terminal
   failure; tests use controlled clock, not sleeps. Do not label unsupported channels live.

## Migration, existing content and concurrency

Migration enumerates existing generated/runtime tenants through supported deployment
inputs and identity/content tables, creates explicit compatibility policies
`require_review=false, public_access=public_allowed`; it must not omit a site merely
because it lacks organization membership. Preserve current publication/notification
state. New tenants and genuinely absent policy use conservative true/members_only;
DB errors never masquerade as absence. Unknown/unsupported schema denies effects.
Document migration output counts and mixed-version rollout: install additive schema,
backfill, deploy enforcing API/workers together, then enable controls. Old workers that
bypass policy cannot remain active once controls are exposed. Rollback cannot restore
old permissive binaries while restrictive policy is active; disable effects and restore
compatible source/schema or require operator-managed rollback. Test backup/restore.

Review enablement does not retroactively unpublish old published revisions. Subsequent
semantic mutations (including edit, revision restore, import update, relationships
and media bindings) to published content under review-required policy move it to draft atomically,
invalidate approval and hide stale projections. Existing scheduled records lacking
valid approval are blocked with actionable status, not silently published. Any policy
version change conservatively invalidates queued approval authorization; user can
reapprove/reconcile. Do not fabricate grandfathered approvals.

Visibility changes apply synchronously at read authorization, not after indexing.
Public allowed means eligible, never forced public. Members-only covers workspace
content and its derived search/public projections, exports and bound asset access;
settings label must say workspace content, not all website/static pages. Inventory
legacy/public route adapters that expose these records and enforce there too. Reject
or filter unauthorized export rows at execution and reauthorize download. Invalidate
or recheck existing asset grants; if a storage URL cannot be revoked/rechecked, do not
expose successful restrictive control until this is resolved. Use private/no-store caching for policy-dependent responses so a later restriction
is not bypassed by shared caches. Extend public-role RLS/read predicates with minimal
policy grants; never switch public reads to an elevated workspace role. Already downloaded data
is outside revocation. Members-only does not disable otherwise authorized member exports. Shared assets do not bypass a restricted binding; define and test
access through independently permitted bindings without granting unrestricted asset IDs.

## UI and discovery

Extend existing registry/shell, not a second catalog. Place publishing policy in Organization and visibility above the existing Site
capabilities module catalog; both use the same versioned policy snapshot and atomic
API. When saving one field preserve the loaded other field; stale snapshot must conflict.
Show organization/site, effective values, version, consequences and explicit Save/Cancel;
site capabilities remain deployment-managed. Notification parser/service carries set
version and preserves current uncertainty guard. Add authorized deep links and disabled/
inherited explanations only for implemented constraints. Preserve drafts on errors;
account identity reset cancels stale responses. Extend discovery parser scope/anchor
allowlists explicitly for organization/site; no arbitrary server URLs. Read-only policy
metadata does not grant write permission or reveal admin navigation. RecordInspector
must consume server-authoritative allowed actions instead of hardcoded draft Publish.
All forms retain saved snapshot: Cancel restores it; 409/uncertain write freezes saves
until explicit Discard draft and reload; 422 retains an editable draft. Warn on full
unload for notification/policy drafts, and guard leaving settings with stay/discard;
a canceled navigation preserves URL/history/focus. Category navigation keeps mounted drafts. Keep all existing appearance/design
contracts, localization, accessible status and responsive behavior.

## Assurance and stopping criteria

TDD maps every AC to model/API/PostgreSQL/browser evidence. Cover CSRF and authentication,
outsider/removed/suspended roles, unknown inputs, CAS and first-insert races, approval/
policy/edit/scheduler races, queue duplicates/restart, lost response, stale search/export/
asset grants, disabled capability and provider boundaries. Use current supported Bash/
PowerShell scripts and assurance runner; no heavy suites sharing builds/DB concurrently.
Maintain >=90% changed-line coverage, existing floors and direct security-critical branch
coverage. Inspect source-bound visuals before any intentional baseline update. Required
full gate at unchanged exact source remains mandatory; pending/blocked is not passed.
Report baseline security/Feature 122 restriction separately; no Expat work in this feature.
No merge, push, deploy or paid resources authorized by this plan. Unexpected identity
mapping ambiguity, unrevocable public asset access or a missing reviewer for required
review blocks that operation with clear recovery, never weakens policy automatically.

## Independent review clarifications

Missing an independent reviewer blocks approval with an explanation to add another
authorized owner/admin through existing administration; never allow self approval
or silently disable review. Read-only effective policy can be provided to active
members without granting the existing administrative category or write permission.

## Asset transport and authorship prerequisites

Initial acceptance is bounded to the current local private encrypted artifact backend.
Code inspection found public media metadata routes, but asset bytes use authenticated
requester-bound grants and no-store responses. The remote S3 adapter does not prove
bucket public-access configuration. Unknown remote transport assurance makes restrictive
policy activation unavailable; do not claim transport confidentiality or alter bucket
ACLs, credentials or network settings in this batch. Existing strict policies fail
closed if a supported storage transport becomes unverified.

ContentRecord currently has no author field. Introduce explicit human creator/semantic
editor and review submitter attribution in canonical review state; do not infer authorship
from the last transition actor. Record human requester provenance for imported content,
not the worker identity. Reviewer must differ from known original creator, current accountable semantic
author/editor and review submitter. Import attribution uses the existing job requester.
Backfill only from unambiguous durable create/import provenance. Unresolved legacy
authorship blocks approval of that historical subject, not the record forever: an
authorized human editor can explicitly prepare/save a fresh attributable draft revision
and submit it for independent review. This creates a new review subject naming that
human as accountable semantic author; preserve unknown historical creator as unknown,
never rewrite historical provenance. A no-op state transition alone is not reconciliation;
the editor explicitly adopts the full content snapshot through the fresh-revision action.
Review excludes that adopting editor, submitter and any known original creator. Existing
already-published content follows the compatibility rule until a semantic mutation.
Test unknown-subject rejection and this recovery without a self-review bypass.

## Frozen API envelopes and storage ownership

Policy persistence is the canonical sitecontent WorkspacePolicy adapter/table
`sitecontent_workspacepolicy`, with its common primitive; do not create a second API
policy table. Runtime organization association is a checked UUID reference to the
public identity realm, not a users.Organization FK assumption. Final migration DDL
is owned by the Django implementer and must preserve this semantic contract.

GET `/api/settings/workspace-policy` returns snake_case:
`{schema_version:1, version, require_review, public_access,
scope:{site_id, organization_id}, provenance, permissions:{read,write}, restrictions}`.
`organization_id` is null when no organization is mapped; write then false.
`provenance` is `migrated|explicit|default`; `restrictions` contains closed safe reason
codes, not provider secrets. PUT contains only `expected_version`, `require_review`,
`public_access` and returns that same envelope from its committed snapshot.

Explicit fresh-subject adoption: POST existing content prefix
`/types/{type_key}/records/{record_id}/review-subject` with
`{expected_version: <record version>, adopt_snapshot: true}`. Use snake_case like
existing TransitionRequest; no generic arbitrary client author. Requires active
content write permission, records the server-authenticated human, produces a fresh
attributable draft/review subject and a new record version even when content bytes
are unchanged; it never approves/publishes. Return updated record plus safe subject
status/allowed actions. Stale record/policy state conflicts; frontend refreshes.
This narrow action is legacy-provenance recovery, not a general workflow designer.

## Supporting retention compatibility

The local legacy artifact-retention path uses the existing MediaPurgePlan rather
than holding a policy-wide database lock across a large file-deletion batch.
A worker-authorized, immutable, server-derived exact manifest and committed purge
intent precede external deletion. User-created plans or a purge_planned status
alone cannot authorize execution. Restores, new references/holds and protected
key/version changes are blocked once execution has been committed.

The fixed recovery floor is 30 days, and any explicit later retention_until also
applies. Runtime deletion transitions establish a database-owned deletion clock;
callers cannot backdate it while remaining deleted. Trusted historical migration
provenance is handled explicitly; missing legacy dates are blocked, not invented.
Unmapped organizations likewise require reconciliation before a scoped audit can
be promised.

Acceptance is limited to the built-in local encrypted store and recognized legacy
original/variant keys. Governed object-version and remote storage families remain
unsupported by this path and must be rejected without mutation. This does not
claim a general media-retention implementation or resolved cross-version orphan
cleanup.

External permission, I/O, decryption and hash failures leave a recoverable committed
plan; only a genuine missing file can count as idempotent prior absence. Successful
counts represent newly completed physical purges, not deleted database rows. The
purged asset tombstone and completed immutable plan remain. Actual PostgreSQL
reference/restore races, crash recovery and restricted-role execution are mandatory
before accepting these source changes.

Native Django effect helpers acquire the same transaction advisory lock before
record, definition, relationship or asset row/reference locks. They do not map
operator identities into public API actors. PostgreSQL requires an active atomic
transaction; lock errors propagate. SQLite-only model checks are not lock proofs.
Custom external ORM/raw transactions that explicitly acquire locks must follow
this documented order; database triggers cannot reorder locks already taken by
an arbitrary caller. Guard failures/deadlocks roll back rather than authorize an
effect, and required PostgreSQL tests cover the supported application paths.

## Required review versus optional workflow review

The existing default workflow can pass through in_review even when require_review
is false. Preserve that workflow and its existing publish permissions: a sole
owner does not need an invented independent approval merely to reach publication.
Only required review rejects submission for unknown accountable authorship or zero
eligible independent reviewers, before committing cycle/audit/intent effects.
Optional transitions may proceed with zero notification recipients; they must not
claim anyone was notified. Approval records themselves remain independent; the
optional policy permits publication without requiring such an approval.

Required-review notification audiences exclude the authors and submitter. Optional
workflow notifications may target currently authorized publishers other than the
requester. Delivery rechecks the current applicable rule and suppresses recipients
that become ineligible after a policy change. There is no automatic audience
backfill. Existing pending records explain missing required reviewers truthfully;
adding an eligible member permits ordinary review, while requesting a new notice
requires the supported explicit resubmission flow. UI status copy must distinguish
optional workflow review from mandatory independent approval.

## Disposable real-service acceptance extension

The existing `e2e/docker-compose.e2e.yml` and isolated Bash/PowerShell runners are
the acceptance path; no deployed preview, public test API, tenant selector or
production authentication bypass is introduced. Frontend, API, content worker and
beat share the generated `base2-obsidian` profile. One-shot setup owns the fresh
disposable database; runtime requests and content jobs retain their restricted
roles. Artifact bytes use the existing encrypted local store, and notification
business effects are local database receipts only, never live email.

The test boundary is deliberately mixed and must be reported precisely:

- Actual rendered browser interactions cover password login and two notification
  settings tabs, including version conflict, explicit reconciliation and reload.
- Other policy, record, approval, role, public/search, export and asset journeys use
  authenticated Playwright API request contexts after real login. They exercise
  the actual API/database, not route mocks, but are **not UI-click coverage** of
  those controls. CSRF-protected cookie refresh is checked separately; existing
  bearer-authenticated API contracts are not replaced by a test-only session.
- Immediate review delivery after restarting the content worker and due-publication
  denial use the actual broker/worker/beat schedule. Execution is fenced until
  reviewer revocation commits, rather than relying on a timing race.
- Opt-out, digest and replay checks stop beat and the queue consumer, then invoke
  the production consumer in fresh restricted worker containers with an explicit
  bounded UTC clock. They independently verify next UTC midnight, no delivery just
  before it and one durable effect after replay. These are **controlled-clock service
  proofs**, not additional evidence of beat execution.
- The same viewer's asset/export grants succeed before a fixed fixture-driven
  suspension, then fail while still unexpired. Only the existing owner-only setup
  service may change that predetermined synthetic viewer after validating fixture
  ownership and taking the production effect lock. Runtime containers receive no
  owner credentials. This proves access reauthorization, **not a user-facing
  suspension flow**; no arbitrary actor/site/SQL input or HTTP control is added.

Loopback HTTP, non-Secure test cookies and Nginx are explicitly scoped differences,
not production Traefik/TLS acceptance. The synthetic pre-ready PNG exercises real
storage/access checks but does not prove media inspection or scanning. A single
base2-obsidian run cannot close representative publishing/docs/portfolio coverage,
migration/restore/race obligations or the complete release gate.

CI schedules separate Ubuntu Bash and PowerShell jobs with distinct retained
success/failure artifacts. The required live-journey descriptor brings the complete
manifest to **133 checks**; registering it is not execution, and no CI workflow
currently invokes that entire gate. Shell selection is closed to the matching
supported runner. The one inherited Bash-only operations UI invocation becomes an
equivalent direct Node invocation; all other 131 prior descriptors remain unchanged.

At the 2026-10-31 integration checkpoint, remote
`e6deb5864ea9f38bad25d6261b756d35cefe1e81` has 8 of 10 workflows passing and all
433 synthetic browser tests green. Those results do not cover the pending backend
repair or this new live-service stack. Source/static review is complete; execution
of the new journeys and PowerShell runtime parity remains pending CI. The next
published batch must retain success artifacts as well as first-failure evidence.

## Bounded recovery security manifest (2026-10-31)

Production backup now binds a version-1 HMAC-authenticated security.json to the dump
SHA-256 inside the existing encrypted database/object bundle. Catalog evidence includes
schema/table/sequence/column/default/function ACLs (including explicit PUBLIC revokes),
object ownership, database owner, RLS enabled/FORCE flags and complete policy expressions.
Capture the catalog from the dump's exported snapshot and compare fresh security state
after capture. Preserve pg_dump ownership and privileges. Explicit configuration names
the trusted migration/definer/database owner, restricted runtime roles, and same-name
map of every non-predefined cluster role. Capture nonsecret role attributes, membership
edges with INHERIT/SET options and effective transitive MEMBER/USAGE authority; no
passwords, CREATE/ALTER ROLE, membership changes or repair GRANTs are transported.

Before database restore, authenticate manifest/dump and compare existing target role
security and database owner. pg_restore uses --exit-on-error --single-transaction,
without --no-owner or --no-privileges. Compare postrestore catalogs before any runtime
function/query or success receipt. Unknown/unmapped/renamed roles, unsafe runtime
attributes, trusted-owner mismatch, missing legacy manifest and security drift deny
acceptance. Offline extraction remains explicitly unverified. Same-version PostgreSQL
and same existing role topology are the conservative compatibility boundary; no role
migration engine is introduced. Unit negatives precede implementation; disposable CI
source-to-target restore establishes real catalog and restricted-runtime behavior.

Review hardening: runtime roles use direct grants and may not have any effective
nonself MEMBER/USAGE authority, including predefined PostgreSQL roles. Target preflight
requires PostgreSQL15+ standard public-schema owner/ACL, not source-specific runtime
schema grants (those are restored transactionally). Function definition digests,
trigger enabled/definitions and constraint validation/definitions augment ACL/RLS
parity. Quoted SQL identifiers prevent ambiguous object identity. Uncaptured foreign
object/large-object/subscription authority, event triggers, nonbaseline extensions,
custom languages and user aggregates are explicitly unsupported and fail closed.

Final closed-catalog review also rejects parameter ACL grants, publications, user-schema
collations/operators/opclasses/opfamilies/conversions/text-search objects and all stored
role/database settings. Source and target encoding/locale/provider/ICU/collation-version
semantics must match, and internal constraint triggers must be ordinarily enabled.
These are compatibility failures, never authority to mutate the source into acceptance.

## Delayed sign-out navigation repair

Retain the first 390px native failure at candidate a4c60ab. Reproduce with the real
AuthProvider, ProtectedRoute and Navigation while holding the logout response: the
null-user guard reaches Sign in before the successful handler previously navigated
to Home. Align the terminal target with the existing Volcano Sign in behavior and
retain failure/retry state. Test delayed success, failed server response and account
preference cleanup, then rerun the unchanged native isolation journey with explicit
request/response evidence. No style or screenshot reference changes are involved.

## Bounded public-pack type-key compatibility

Separate canonical type-key validation from field/preset identifiers. Use an
ASCII letter-led 2–63 character expression with underscore-compatible segments
and single hyphens followed by ASCII alphanumerics; anchor the entire input to
reject newlines, Unicode, traversal, separators and SQL syntax. Preserve all
previous valid underscore keys. Apply it to definition keys and relationship
target types, then mirror in API create/route guards and React without normalizing
public hyphens into underscores. Add a Django validator-state migration only;
no data rewrite, SQL identifier interpolation or permission change. Trace imports,
exports, storage, worker and public projections; field mapping/projection keys
remain strict. Test canonical creation/reference validation and migration state
first, API create/routes and negatives second, UI exact-key submission last.
Generated manifest gates remain authoritative; mock checks are not real profile
journey acceptance. Browser and production-topology acceptance remain separately
blocked until the existing native prerequisites are available.

The old native field/preset RegexValidator dollar anchor also admits a final
newline. Tighten only CONTENT_IDENTIFIER_PATTERN to strict \A/\Z anchors;
retain its ASCII language and serialize all four affected fields in the same
additive 0042 validator-state migration. Full-clean regressions reproduce preset
and field acceptance before correction. Existing rows are not rewritten; a later
validated edit to a malformed stored identifier fails closed. Operations patterns
and SQL/readiness capabilities remain unchanged.

## Supported-pack projection and generated-profile acceptance

Introduce a closed mapping for the three existing public pack types to the actual
frontend route prefixes. Test the mapping against module/PublicRoutes contracts.
Existing source timestamps alone do not schedule changed projection URLs: add a
bounded idempotent projection repair for exact legacy generated paths at the current
source version, preserving stale-write protection, tenant joins, document IDs and
all content/approval state. Prove already indexed and operator-custom-path cases;
no wildcard route or unreviewed generic renderer is introduced.

Parameterize the existing isolated runner with an allowlisted `E2E_SITE_PROFILE`,
validated before any Compose action and propagated consistently. Keep base2's two
shell runs; add journey-reference Bash with distinct artifacts. Reuse normal
login/settings/API paths to publish one record for each exact family type, follow
its real returned search link, then restrict access and prove public search/direct
page denial while authorized workspace access remains. Preserve actual disabled
module/profile guard contracts separately. Source contract collection is not live
profile proof; retain successful screenshots and response/status evidence for review.
