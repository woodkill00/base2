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

## Public body capability exposed by representative execution

The real representative run proves normal record values persist, but the public
response's excerpt/body/metadata remain empty because no supported authoring path
writes them. Retain that failure and implement intentional plain-text copy through
existing atomic create/update, not fixture SQL or automatic dynamic-field exposure.

First add canonical validation and versioned snapshot/restore helpers, then mirrored
API contracts and all record-return projections. Extend exactly the existing worker
due-publication/import-update snapshot producers, without accepting public import
input or changing scheduler semantics. Preserve forensic context and existing
revision numbering; audit snapshot diff, retention and data-rights consumers for
format compatibility. Test legacy flat/private-field-name collisions, unsupported
formats, stale/denied saves, public-copy invalidation and safe restore under actual
restricted roles. All new public text stays private until existing publication and
visibility rules authorize it.

Then integrate an explicit public excerpt/body section with existing record editing,
one saved/draft snapshot and one CAS save. Include copy in dirty/discard/unload and
scope-change handling; preserve rejected/stale drafts until explicit reload. History
must show whether public text is recorded, preserved or unsupported before restore.
Keep existing design and text-only rendering, including Unicode-limit equivalence;
no arbitrary HTML or metadata controls. Extend the representative journey to author
explicit public copy (including one actual UI edit), retain distinct private values,
and prove rendered/search text without private-value leakage before restriction.

### Native restore representation repair

All 79 changed objects/expressions are identified against public migration source.
The 73 ACL arrays equal documented built-in defaults; NULL after pg_restore therefore
needs precise kind/owner-aware effective ACL capture, not omission of ACL checking.
All twelve expected/actual expression hashes match six array-cast deparse variants.
Implement security evidence v2 with conservative token-aware literal-array canonical
form, preserve all surrounding policy/constraint clauses and unsupported differences,
and reject v1 for database restoration. Regression-first exact-hash fixtures, hostile
literal/altered clause/privilege negatives, independent review and real native restore
must precede acceptance. No custom media runtime repair, grant repair or role creation.

### Native mobile authoring correction

Keep desktop composition and approved design unchanged. Inspect cumulative mobile
padding in workspace panels, creation form and public-copy fields; reduce only scoped
mobile spacing constraints. Prove actual rendered widths and focused viewport
visibility on390px, retain1440 screenshots, review pixels before acceptance. Re-run
shared component unit/static coverage and existing native workspace/visual suites.

### Scoped pre-existing divider compatibility correction

After7fcbc15's workspace matrix passes with corrected fixtures, treat the known
opaque-gray separator as its own bounded visual correction. Give Records list items
an existing nonzero-specificity white/10 border color, retaining existing divide
geometry. Unit/source regression precedes change; native computed-paint assertion
and unchanged visual baselines verify actual rendering across the existing matrix.

### Forced-color configuration and evidence repair

The c0c2751 passing matrix proves normal-color divider rendering, not necessarily
forced mode: unsupported top-level forcedColors can make a conditional helper take
its normal branch. Correct workspace/media/operations to contextOptions, add a shared
runtime expected-state assertion and source contracts, preserving existing settings
and valid media-library coverage. Retain all genuine workspace HC captures through
soft comparison failure batching with explicit failed summaries; never weaken exit
status or media/operations accepted-artifact guards. No product CSS or baseline edit
until genuine rendering is inspected. Actual native execution is mandatory.

### Genuine HC findings and bounded product repair

At274d05b, actual forced mode is proved active before/after axe; workspace and
operations fail primary-button computed contrast, not merely references. Pixels
show white labels, so do not claim visibly black labels. Add HC-only system palette
semantics with scoped CSSOM/native checks and unchanged normal styles. Repair the
observed boundaryless portaled picker search/status field with HC-only borders;
review any selected-tab shadow fallback separately. No baseline update precedes
functional/axe correctness and actual pixel review.

### Published-head recovery and optional native review preparation

Recover exact published head 93a3ecc and preserve its failed native evidence. Correct
only the picker Status control's locator to its exact combobox role/name, retaining
the required border and all forced-mode, paint, axe and interaction checks. Validate
source contracts, application/individual fixture types and line-reporter collection;
collection must not rewrite the tracked operations runner receipt.

Prepare opt-in operations/media full-matrix CI with immutable exact-head checks,
explicit snapshot-update prohibition, current-source inventory and fresh reporter
provenance. Reject zero supported execution, missing cases/captures and source or
baseline mutation. Keep native failures fatal and actual failed evidence available.
This is evidence collection infrastructure, not visual approval or manifest renewal.
Review actual native captures before proposing reference changes; hold publication
for coordination and do not trigger the complete gate at this stage.

### Bounded workspace visual evidence transfer

Keep the full native workspace artifact and original test failures. Additionally
stage exact HC actual/expected/diff/post-assert PNG filenames into one artifact per
view, with source commit/tree, requested head, run/attempt, original outcome and
member hashes. Cap each view at 30 MiB of unchanged PNG bytes plus at most 64 KiB
of provenance, below the 32 MiB transfer limit. Reject symlinks, oversized input
and reused output; never truncate captures or export traces, videos or fixtures.
Missing captures remain explicit empty inventories, not successful visual evidence.

### Screenshot lifecycle slice (preparation)

Add an offline explicit-inventory PNG importer/validator under scripts/python,
content-addressed diagnostic objects, immutable per-native-artifact run manifests,
and separate technical-review/later-validation records. Preserve existing reference
paths and source-bound acceptance contracts. Inventory all screenshot call sites
and failure-capture configurations; bounded native collection currently covers only
four workspace HC views. No automated repository publication or baseline promotion.
At the initial pre-transfer checkpoint, archive population and workspace reference
changes awaited verified bytes. The completed preparation is recorded below;
cf2a950's original workspace failure remains recorded.


Git-transfer import explicitly distinguishes externally verified ZIP/member
provenance from locally verified Git blob/PNG integrity. Six native manifests retain
30 capture records using 20 new objects plus exact existing Git references. Five
technical-review events and one later targeted-validation event preserve original
failed outcomes. Four reviewed workspace HC replacements are prepared; fresh
native validation and publication remain pending. No original ZIP was rehashed in
this checkout, and no complete visual acceptance is granted.


Retained archive maintenance: backend API CI validates committed manifests/events,
PNG hashes and full decoding, and historical baseline references with full checkout
history and no persisted credentials. Exact native merge-commit object proofs bind
tested source identity to tree-equivalent retained heads, avoiding dependency on
unreferenced merge or transfer commits. Native visual acceptance remains separate.


### Native reduced-motion defect and bounded matrix diagnostics

Frozen head cfc0c4be5d952322fe3af742394e8fe2c45a2a27 passed the standard
437-case browser run 41282645641. Full optional operations run 41283915226
then exposed a real reduced-motion cascade defect: 21 passed, 20 declared skips,
one failure at the exact-zero transition assertion (received 1e-05s). The global
preference selector outranks the operations selector. Increase only the operations
selector specificity inside its existing reduced-motion media query; retain zero
animation/transition duration, normal-motion rules, native assertion and baselines.
The first native failure log and failing-first specificity regression are retained.

Keep the original full matrix artifact unchanged. Add bounded forward diagnostic
packaging after the original upload: exact source/report bytes and an inventory in
one small metadata ZIP, plus PNG-only ZIPs for each declared project. Limit PNG
input to 28 MiB per project and every completed ZIP to 30 MiB, leaving room under
the 32 MiB transfer ceiling for the upload wrapper. Reject symlinks, traversal,
unknown PNG names/project association and output reuse; never truncate bytes.
Empty/missing captures remain explicitly incomplete. Packaging cannot turn native
failure into success, promote references or produce a replacement native receipt.
No historical oversized artifact download is retried.

Bounded metadata contains exact source-before/source-after JSON, the operations
receipt when emitted, stages and a derived diagnostic inventory. Raw playwright.json
remains in the full artifact because its embedded PNG bodies can be large. A PNG
project marked packaged only means available bytes were retained; supported-test
counts and minimum current-capture shortfalls remain visible, and no count grants
complete visual coverage.

Passing standard-run retention remains a separate 13-file append-only candidate:
five manifests, five validation events, two PNG objects and one exact merge source
proof. Its eight captures do not establish full matrix acceptance. Optional media
run 41283921639 has 24 supported passes and 12 declared skips across 12 Chromium
projects; no Firefox/WebKit media coverage is claimed and pixel review is pending.

Evidence-only CI scope changes are deferred. The current base-policy comparison
still requires full frontend checks. A future reuse policy must bind executable,
configuration, fixture, toolchain and baseline identities to verified prior native
source, validate every evidence append, reject rewrites/deletions and unknown paths,
and fail closed for missing history. Recording validation must not manufacture a
new native pass. Stacked PR base differences cannot be ignored merely because the
latest commit contains evidence only.

Media review follow-up (not part of this repair): the detail test deliberately holds
the lifecycle response, scrolls to Applying action, captures pending state, then
releases the request and asserts completion text/focus. No top-of-dialog or terminal
state screenshot exists in the searched E2E sources. Supplement the preserved
pending reference with stable top/preview/header/close and completed-state captures.
Also capture the compact picker bottom/actions; investigate the large-text selection
counter splitting and fixed scroll-control overlap with viewport screenshots before
classifying the latter as a product defect. Preserve all current references/history.


### Media supplementary coverage and selection-counter usability (unpublished)

Source starts at published 4e591455b1eb7491b81b53b01c8648a8ef2d2489. Its full
operations and media native matrices passed their supported cases, with declared
skips preserved; this does not grant visual acceptance. Retain the earlier full
media run 41283921639 as diagnostic history: 24 executed passes / 12 declared skips,
Chromium only. Imported PNGs retain externally verified archive provenance and local
Git/SHA256/size/dimension/full-decode verification, separate from future results.

Correct only the media toolbar counter layout: reserve intrinsic unbroken counter
width and let search/status controls wrap responsively. Preserve the surrounding
Obsidian design. Component checks retain polite LTR selection announcements; native
geometry checks require a single counter line and no horizontal overflow, including
the existing large-text and narrow projects. Source contracts fail first on the
old grid/counter rules. Native rendering validation remains pending.

Keep all existing reference files and pending-action comparison assertions unchanged.
Supplement each supported detail case with stable loaded top/header/close/preview
and completed-mutation diagnostic captures. Completion requires the real fixture
response, completed status/version, dismissed confirmation and restored focus.
Supplement picker captures with the bottom item and enabled submit control in view.
These current PNGs are diagnostics, not pre-approved reference targets.

Before the existing full-page normalization, collect first/middle/last-card viewport
PNGs with the real sticky header and floating movement controls. Attach native
geometry, hit-test and control-overlap observations without declaring intersection
alone a product defect. Persist the exact media-viewport-observations.json file and
retain the same bytes as a Playwright attachment. The bounded project ZIP includes
only this explicitly named synthetic geometry schema alongside its three viewport
PNGs; generic JSON, DOM/card text, arbitrary bodies and traces remain excluded.
The file has a 64 KiB limit, exact case/project/test binding, duplicate-key rejection,
finite numeric bounds, fixed control/target enums and no extra fields. Inventory
records its SHA256 and size under the native source/run identity. Missing diagnostics
remain visible; original native failure and report bytes remain unchanged. Expected totals
remain 36 declared / 24 supported / 12 skipped across 12 Chromium projects. Capture
counts increase, but no additional browsers or automatic acceptance are introduced.

The next bounded media repair follows native run 41287894771 on head 173c17ea.
Compact and 400-zoom images confirm horizontal preview clipping; the mobile-only
sizing correction retains visible content, minimum height and strict visibility.
Supplementary scrolling now follows the original comparison to avoid perturbing
floating controls in the light reference state. Hard comparison failures are preserved and rethrown after diagnostic evidence
collection, including when a later diagnostic also fails. No references,
thresholds or accepted manifests are renewed. Fresh native execution and pixel
review remain pending; local source checks are not native layout validation.

Further native review confirmed low-contrast inherited preview text in light mode
and real floating-control overlap with non-centered card text. The preview gets an
explicit accessible foreground while forced colors remain native. Observation
schema version 2 measures every visible relevant card target (bounded five-card
fixture), retaining version 1 validation and safe geometry-only export. Shared
floating-control placement is an open usability defect; no product placement change
is included in this slice. Fresh native evidence must verify the new assertions.

### Reserved movement-control layout (separate owner-approved shell slice)

Starting source is 2939e45f. The owner approved desktop side gutters and a separate
mobile bottom strip after native evidence confirmed text/action obstruction. Desktop
keeps document scrolling with logical gutters; compact/zoomed layouts use a bounded
content scrollport above the dock. The movement toggle restores the prior document
layout when disabled. Legacy Home/HomeSharedControls remain document-based.

A shared explicit target adapter owns scroll metrics, events, height-based movement,
edge jumps, measured sticky-header anchor offsets and reference-counted locking.
Responsive/toggle transitions preserve a visible content anchor and cancel old
movement timers. Docked buttons preserve their existing appearance and participate
in modal inertness; modal locks follow target changes through context.

Validation covers adapter behavior, nested locks, route controls, focused media and
navigation units, types and migrated native contracts. New native geometry checks
measure all visible relevant content rectangles against actual controls at top,
middle and bottom; centered hit tests alone are insufficient. Mobile full-page
screenshots now represent the bounded shell viewport, not an expanded document:
separate top/middle/footer captures are required to show reachable content. Existing
references remain immutable and may fail for this intentional layout change; no
comparison is bypassed or auto-approved. Cross-device native execution and technical
pixel review remain pending publication review.

Media observation schema version 3 records the content scrollport clipping rectangle
as well as original target/control rectangles; overlap is computed against visible
content intersections. Versions 1 and 2 remain valid historical evidence. Native
post-test top/middle/footer viewport captures supplement bounded mobile full-page
images in media, operations, workspace, settings and Volcano suites. Captures are
not taken through an open modal; such cases do not claim underlying-page coverage.
Media/operations PNGs use the existing bounded project collector. Other suites'
full original artifacts retain supplementary captures; broader bounded retrieval
remains separate collection work. This is not approval of replacement baselines.

Shell revision review adds coordinated document-lock ownership across picker,
GlassModal and navigation drawers; ancestor-inert navigation ignores shortcuts.
History positions are bounded by router entry and restored on the active target.
A pending POP offset survives initially short loading content; content observers
retry for up to five seconds, stop on success or deliberate input, and preserve
unreached offsets without claiming restoration. Cold fragments wait for the actual
compact scrollport. Native Back/Forward, button-close/reopen and cold-fragment
checks are added to existing cases. Real mobile virtual-keyboard/visual-viewport
behavior remains unverified; window resize and JSDOM are not keyboard evidence.

History identity boundary: BrowserRouter's shared `default` key is not an entry
identity. Cold/unkeyed native fragment entries are excluded from custom offset
storage/restoration; their standard history state is never rewritten and native
scroll-restoration policy is preserved. Fragment alignment still follows their
actual URL. Keyed router entries retain bounded loading-aware restoration, with
entry ownership checked before storing offsets or applying pending restoration.
Exact prior-offset restoration for an unkeyed nested-scrollport entry is not
claimed; browser fragment alignment/native restoration remains the fallback.

### Terminal shared-shell repair boundary

The next candidate separates confirmed CSS/interaction defects from unresolved
native observations. Dialog descendants must retain their own scrolling geometry;
operations and records columns must adapt to available content width in rem units.
Only operations screenshot comparisons accumulate through Playwright's native
soft assertion machinery; state readiness, accessibility, forced-color and behavior
checks remain hard. Later hard failures must not erase earlier comparison errors.
Current captures are retained even after mismatch, while reference-byte attachments
are emitted only for successful comparisons. Per-state compact viewport captures
must not overwrite one another or be attributed to a route after navigation away.

Geometry v4 preserves the raw content viewport and control intersections. It adds
an unobscured viewport beneath the sticky header and a separate center-visibility
flag, without reinterpreting historical receipts. Drawer toggles join movement
circles in new observations. A sampled obstruction is not proof of an unreachable
control, and zero sampled intersections are not global visual acceptance.

Compact timeout/Firefox focus progression need native trace evidence before product
changes; diagnostics alone do not resolve them. The confirmed compact footer/right-toggle overlap is addressed by moving the
existing drawer tabs into side slots of the reserved bottom strip. Circle styling
and full content width remain unchanged; tabs keep their colors, icons and curved
edges with 44-56px targets. Popup content opens above the strip with bounded vertical
scrolling. Desktop and movement-disabled legacy positions are unchanged; protection
in those legacy modes is not newly claimed. All four persistent controls enter
footer intersection checks. Fresh native reachability/pixel validation is pending. No new references, acceptance-manifest renewal, security
runtime work, complete-gate execution or publication belongs to this preparation.

### Native prerequisite and artifact partition repair on 696f7106

Run 41314685335 stopped at 783 passing / 4 failing frontend unit cases, before
standard browsers. The four assertions encode superseded fixed-grid/no-min-width
classes; preserve mobile padding, edit-state transitions and containment checks
while asserting the available-width grid contract. Run the entire frontend unit
suite with its existing coverage floors before another publication.

Operations run 41314740935 preserved its 1 pass / 21 failures / 20 declared skips,
but WebKit diagnostic packaging exceeded the former aggregate project budget.
Keep that original failure and full artifact. Split sorted whole PNG/allowlisted
observation members at 28 MiB payload per part, measure every ZIP at <=30 MiB,
and record each member-to-part identity and ZIP hash/size in inventory schema 2.
A single oversized member remains an explicit error; never truncate it. The
existing 256-capture per-project bound remains. Each part gets its own GitHub
artifact, not a combined multi-part artifact exceeding the retrieval limit.

After successful packaging, emit a fixed-path local composite containing only
pinned upload-artifact steps for validated exact ZIP basenames. No report text
or arbitrary shell becomes action code. Each step uses always() so an upload
failure does not hide later parts; failures remain fatal. Original full artifact
and separate metadata upload remain unchanged. At most 480 parts are uploaded,
leaving headroom beneath GitHub's per-job artifact limit; overflow fails explicitly.
This is transport preparation, not native validation or visual acceptance.

### Follow-up scope after da4d0a72 native validation

Two separately accounted slices: functional scroll/history/focus ownership and
continuous diagnostic capture. Source remains unpublished until independent review.
No local browser or Docker execution; native evidence is required for final fixes.
The continuous collector retains raw overlapping frames and strict synthetic
provenance, validates complete unobscured interval coverage and final reachability,
and preserves legacy evidence. No stitching or automatic baseline promotion.

Continuous evidence implementation scope: the content target is the bounded mobile
scrollport; document-scrolling desktop and controls-disabled layouts retain their
existing full-page evidence and are not claimed continuously swept. Explicit dialog
sweeps include media ready/pending/deleted/restored/picker and operations cancellation
on every supported main-test project, including mobile and WebKit. Up to 64 untouched
viewport frames per state overlap by 25% of visible height. Interval-union, route,
extent, progress and end checks fail incomplete coverage. Per-project transport
permits 16 receipts / 1024 continuous frames separately from the original 256 PNG
budget; unchanged deterministic 28 MiB payload / 30 MiB ZIP partition limits apply.
The shell collector retains its 4096-member and 16-shard ceilings, failing excess
rather than dropping frames. JSON records never approve a comparison reference.

Functional diagnoses: initial closed-menu restoration stole body focus on mount;
restoration now follows only an actual close. A deterministic delayed-scroll POP
regression reproduces losing the final outgoing offset, now captured before router
reconciliation with ordinary late-event ownership checks retained. Native causality
still needs confirmation. Zoom's logged offset 5 was below the unchanged >12 ascend
availability boundary; preserve the >0 toggle-retention check, then explicitly enter
180 before exercising Ascend and the unchanged exact-zero assertion. Original timeout
and late teardown logs remain failed evidence, not proof the action completed.

New review concerns stay explicit: RTL /ar/about and light 200% RTL now get all-four
control focus-outline separation and hit-target checks before any spacing change.
Current workspace images show empty inspector placeholders, not selected-record edit
containment. Historical collector exclusions (84 layout, 1 Volcano, 15 settings) stay
unresolved until their exact member inventory is available; do not infer that every
excluded PNG is a legitimate producer or broaden collection to arbitrary filenames.

Full-unit cross-check preserved two existing POP/hashchange failures introduced by
an unconditional outgoing snapshot. The revised capture refuses to save once an
already observed scroll has lost entry ownership. A genuine delayed outgoing scroll
delivered after key change but before popstate is indistinguishable from an incoming
restoration and conservatively retains the last owned value; that exact ordering is
covered and remains a limitation. Native compact Forward is still unresolved until
fresh CI establishes behavior; static repair is not a blanket restoration guarantee.

### Native review boundary after 14a1441b

All standard and both optional runs are terminal. The three targeted functional
checks passed on this head, without a general guarantee for every browser-history
ordering. Standard browser results remain 423 / 444 passed; full media remains
12 passed, 12 failed, 12 declared skips, and operations 1 passed, 21 failed,
20 declared skips. Reference mismatches remain fatal and unaccepted; the media
security scan still fails its high-severity threshold.

Two further changes are separately reviewable. The bottom dock clears legacy
physical left/right offsets from its grid-positioned circles; in RTL those offsets
shifted circles outward into the drawer's five-pixel focus ring. Existing outlines,
touch dimensions and non-bottom positioning remain unchanged. Native all-four
focused-control proof remains required.

The continuous collector previously preserved a focused Skip overlay while its
interval union measured only target geometry. Reviewed operations landscape frames
[0,274] and [206,480] left content y274–295 occluded in x14–245. Six workspace
mobile/tablet sweeps also retain this flaw. Preserve their original frames/receipts;
exclude these sequences from unobscured-reference eligibility. New schema 2 saves
an original-focus context image, blurs focus for a separately identified content
sweep, checks neutral focus and absence of the visible Skip overlay on each frame,
and restores focus and the exact scroll position. Context images do not contribute
to coverage. Schema 1 stays readable and immutable. Geometric completeness is never
universal occlusion proof: remaining overlays and every intended content band still
require independent pixel review, explicitly recorded as required rather than
approved. Packaging binds all images and allows one extra context image per state
within existing byte/part limits; no reference or threshold is changed.

### Nested reference sequence source contract (pre-publication)

The sequence manifest is a new contract; old references and native failures remain
immutable. Desktop window-scrolled pages retain the existing full-page comparison.
For nested content, the neutral first frame is the overview, followed by the entire
ordered overlapping sequence. The matcher consumes the exact retained PNG buffers.
No image is stitched, edited or synthesized. Existing ratios (including operations
cancellation 0.02) and default threshold 0.2 remain unchanged. Snapshot update mode
must be `none` in the five affected native configurations.

An approved set requires a version 1 manifest and adjacent review record, exact
ordered image hashes, current dependency/configuration/route-state bindings, and
verified source commit/tree ancestry. The record binds the full schedule and image
inventory hashes. This source change creates neither record nor expected image.
Missing or invalid sets produce fatal soft comparison errors so independently ready
later states can still execute. Hard readiness, interaction and coverage failures
remain fatal. An absent expected image has no invented expected/diff role; matching
images have no fabricated diff. Complete comparison transport means all scheduled
comparisons were attempted, not that they matched or were visually accepted.

Geometry derivation version 1 is shared in the producer and independently checked
against the original schema 2 receipt by Python. The existing 1 CSS-pixel derivation
rounding allowance is separate from approval: approved schedules use exact structural
geometry equality, including subpixel values. Route query/fragment identity and
fixture environment are hashed without publishing raw query values. Any schedule,
route/state, dependency or environment change invalidates the complete set. Fixed
synthetic fixtures, disabled animation and neutral focus reduce arbitrary churn;
this does not certify unrelated overlays or unobserved states. Original focused
context remains separate. Desktop full-page comparisons retain their original names.

Budget preflight is deliberately fail-closed. Each state has at most 64 segments,
28 MiB per PNG, 96 MiB aggregate including original frames/context plus actual,
expected and diff copies, and a 256 KiB comparison receipt. Known original/actual/
expected sizes are checked before matching; diff bytes are charged as produced.
Comparison work has a 20-second ceiling; existing native test timeouts remain the
outer limit and are not increased. Hitting a bound is incomplete evidence and a
failure, never silent truncation or permission to reduce coverage.

The configured comparison opportunities are 55 standard states (24 nested workspace
views, 22 named mobile routes, three mobile contact cases, five HC media
dialog states and one HC operations cancellation), 35 optional media states (five
nested libraries, 24 detail lifecycle states, six pickers), and 23 optional operations
states (four nested main states, five compact recovery states and 14 cancellation
dialogs). These are opportunities, not executed/accepted counts: a failed hard
prerequisite can prevent later states, and actual scroll targets determine applicability.
At the 96 MiB state ceiling those are 5280 / 3360 / 2208 MiB, before unrelated legacy
diagnostics. Collection preflights the entire produced inventory before splitting;
the job payload cap is 6 GiB, at most 480 parts (leaving room below the 500-artifact
job ceiling for original artifacts). Maximum state ceilings are not promised to fit
simultaneously with every legacy diagnostic: saturation fails explicitly.

Shell parts hold at most 28 MiB payload, 2048 members, 300-byte relative paths and
512 KiB metadata; these bounds leave wrapper overhead below 32 MiB. Optional matrix
ZIPs retain their explicit 30 MiB encoded limit. No arbitrary JSON/HTML/video/trace
collection is added. The original full artifacts and original test exit status remain.
Journey comparison collection is restricted to the two known contact/search names;
known producer attachment exclusions disclose only bounded relative names, while
unknown exclusions remain counts. The old 84 layout / one Volcano / 15 settings
excluded PNGs cannot be identified retroactively from count-only receipts. New
producer receipts resolve only safely recognized names and do not claim all exclusions
are covered. Expected images remain subject to independent native pixel approval.

The dependency binding includes rendering configurations (Vite/Tailwind/PostCSS),
HTML, package manifests/lock, public assets including PNGs/fonts, fixture support
and orchestration source; approved snapshot directories are excluded to avoid
self-reference. Runtime identity includes actual browser version, platform/architecture,
kernel, Node/runner image versions, and hashes of the installed font files reported
by Fontconfig. A changed renderer/toolchain requires renewed inspection rather than
silently reusing an old approval. Missing or unsafe font inventory fails closed;
no font installation or system repair is performed by this collector.

Read-only enforcement also checks Playwright's resolved configuration in a shared
global setup, before any legacy comparison can execute; CLI aliases cannot bypass
it. PNG allocation bounds are checked before decoding, including a complete chunk
walk rejecting duplicate IHDR and interlaced streams. Native Playwright sequence
captures are non-interlaced. These restrictions do not rewrite any image bytes.

The source-v2 review corrections keep legacy picker mismatches fatal through
Playwright's deferred error reporting, allowing independently ready sequence and
reuse checks to run. Operations removes its temporary legacy header style before
asserting authored sticky positioning and collecting sequences. Named-route sets
use a stable route/test digest, so all 44 route/width identities have distinct
reference namespaces. Registered compact states and existing approved targets
fail on missing, ambiguous or wrong target kinds; only intentional document/off
modes without an applicable approved set skip collection. Attempted failure states
are captured before rethrowing their original error.

Bounded transport validates each producer before aggregation. Invalid producers
and capacity overflow leave explicit incomplete/error metadata while independently
valid parts remain retrievable. Rejected producer names and contents are omitted;
packaging still exits unsuccessfully. These partial parts cannot establish complete
coverage or reference acceptance. The deferred diagnostic archive and its closed
support-object registry are separately reviewed work, outside this source candidate.

The original Volcano preview home is explicitly registered as a document-scrolling
fixture at both declared widths; its existing home/drawer/palette comparisons remain
unchanged. It is not a nested-sequence opportunity. Any unexpected nested target,
dialog or approved nested set in that registered document fixture remains fatal.
