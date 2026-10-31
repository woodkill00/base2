# Feature 124: Shared workspace policy

Created: 2026-10-31. Status: approved scope; implementation in progress, integration and release acceptance pending.
Baseline inspected: `0c8e08870ffe72f1329a2c9d2a9dc59278a650a9`.

## User outcome and boundaries

Extend the existing Obsidian/Volcano Settings Center with four working capabilities:
conflict-safe personal notification choices, organization-required publishing review,
site workspace-content visibility, and durable review-request notifications. A saved
control must change actual behavior. This is not completion of all site families.
Use the current site's organization; no tenant selector, arbitrary role designer,
runtime module activation, live email, credentials, spending, merge or deployment.

## Scope and actors

The generated site is the current tenant. There is one runtime organization per
tenant; no cross-site organization hierarchy is introduced. Active owners/admins
may edit the two shared policies and review content; editors may edit/submit and
schedule only when applicable review requirements are satisfied; viewers may read
only content already permitted by existing permissions. Review does not grant a
new role. Suspended/removed/nonmembers cannot use member-only content. Personal
notification choices affect only the current user on the current site.

## Acceptance outcomes

- **AC1 Notification integrity:** Two tabs cannot silently overwrite each other's
  notification set, including simultaneous first saves. Save is atomic and returns
  its own committed values/version. Conflict, timeout and uncertain-write recovery
  preserve drafts and require explicit reconciliation, not automatic mutation replay.
  Mandatory families cannot be disabled or bypassed by omitting rows.
- **AC2 Review policy:** Administrators can require review before publishing workspace
  content. The author cannot approve their own submitted revision. Approval concerns
  exactly the reviewed version; semantic edits, restores, imports, relationship/media changes or policy changes
  invalidate it; state-only schedule/publish transitions do not change the reviewed content. Direct publish,
  scheduling and due publication enforce the same rule. Revoked reviewer permission
  cannot authorize a later scheduled publication. Already published content is not
  silently unpublished solely by enabling review; a subsequent content edit under
  that policy removes it from public publication until reviewed again.
- **AC3 Visibility policy:** Administrators choose whether workspace-managed content
  may be public or requires active site membership. This restriction applies to all
  existing and new workspace records immediately after commit, including direct
  reads, search, export downloads and bound assets. It never broadens existing record,
  role or asset restrictions. Previously downloaded copies cannot be recalled; the
  confirmation states that limit. Restoring public eligibility does not publish drafts.
- **AC4 Review notifications:** A required-review request durably notifies eligible
  independent reviewers through the product/email preference. Optional workflow
  requests may notify authorized publishers other than the requester; a zero-recipient
  optional transition must not claim delivery. Immediate, disabled
  and daily digest choices have observable behavior through a local test adapter only.
  Duplicate work must not duplicate its business effect. Membership, policy and
  content eligibility are checked again before delivery. No enabled live email or
  browser-push claim is made. Other families/channels retain explicit saved-only limits.
- **AC5 Scope and safe defaults:** Shared forms identify the current site/organization,
  effective value, provenance and deployment restrictions. Explicit migrated settings
  preserve existing behavior. Genuinely new sites default to review-required and
  member-only workspace content. An unavailable policy is not treated as permission
  to publish or expose content. Unsupported/disabled modules remain unusable directly.
- **AC6 Recovery and history:** Only successful durable writes are reported saved;
  concurrent policy edits conflict. Safe audit records identify actor, scope and
  versions, never content/secrets. Background failures are visible and retryable within
  bounded policy, with no false delivery success or automatic live-provider fallback.
- **AC7 Usability:** Existing settings routes/design persist. Search/deep links focus
  the actual authorized control within three interactions. Keyboard, phone, light/dark,
  high contrast, loading/error/conflict/locked and Save/Cancel states are covered.
- **AC8 Assurance:** Real persistence, transaction races, restricted-runtime RLS,
  multi-user journeys, migration/restore and exact-source release evidence establish
  these outcomes separately from mock tests. No historical green check is a new pass.

## Concrete journeys

1. Two sessions change product/email choices: first saves, second conflicts, reload
   shows the first result; another tenant/user's choices are unchanged.
2. Editor submits draft; owner/admin other than its author approves that revision;
   publication succeeds. Self approval, stale approval, direct bypass, disabled module,
   role revocation and scheduler bypass fail without leaking content.
3. Administrator restricts public workspace content while a public search result,
   asset link and export are already open: subsequent unauthorized requests are denied or filtered; valid active-member
   exports and asset reads remain subject to their existing permissions.
   An active viewer retains only existing authorized read access.
4. Review submission survives worker restart; disabled delivery suppresses it; digest
   delivers once at the next UTC daily boundary; removed reviewer receives nothing.

## Explicit deferrals and release boundary

No general inheritance engine, arbitrary workflow scripts, individual audience/group
builder, multi-organization administration, live adapters or complete CRM/social/commerce
engines. Broader work remains ordered in `backlog.md`. Required baseline security
acceptance remains blocked independently of this implementation; stopped Feature 122
Expat repair must not be resumed, delegated or bypassed here. Draft PR 89 is unchanged.

## Bounded recovery security acceptance

A whole-database recovery must retain source ownership, access grants and revocations,
row security and trusted function boundaries before any restored runtime action or
successful readiness receipt. Existing target roles must match explicitly approved
same-name source roles, including inherited and assumable authority. Recovery must
never create or repair roles or invent missing privileges. Older backups without
authenticated security evidence remain available for offline extraction only; they
cannot claim database recovery acceptance. Unknown or escalated roles and security
drift fail closed without modifying the original source database.

## Sign-out navigation consistency

After local authentication state is cleared, both shared and Volcano layouts settle
on Sign in. A delayed successful server logout must not replace the protected-route
Sign in redirect with Home. Preserve server-failure retry guidance, ordinary public
navigation, and cleared account-scoped appearance/settings state. This is an explicit
resolution of conflicting existing navigation contracts, not permission to weaken
the native sign-out isolation test or change the approved visual design.

## Public-pack type-key compatibility

Workspace users can create and version the exact public family types `blog-post`,
`doc-page`, and `portfolio-item` through the supported schema workflow, without
renaming them or bypassing validation. Existing underscore type names remain valid.
Type names stay lowercase, ASCII, letter-led and 2–63 characters; hyphens separate
nonempty segments and cannot precede an underscore. Field and preset identifiers
retain their stricter existing format. Unsafe names fail closed. This compatibility
does not enable a disabled pack or alter roles, review, visibility or immutable schemas.

Native field and preset validation must reject trailing newlines, matching the
already-strict API contract. This closes an anchor inconsistency without permitting
hyphens in those identifiers or rewriting previously stored rows.

## Supported-pack search navigation and representative profiles

Published `blog-post`, `doc-page`, and `portfolio-item` search results must lead to
the existing `/blog/{slug}`, `/docs/{slug}` and `/portfolio/{slug}` pages. Correct
existing automatically generated legacy paths without changing search-document
identity, source timestamps, content revisions or approvals. Preserve deliberate
custom paths outside the exact old generated-path pattern; never weaken current
tenant, state, visibility, tombstone or stale-write checks to repair a URL.

Representative live acceptance uses only `base2-obsidian` and `journey-reference`
through an explicit runner-side allowlist, with consistent selected profile in
frontend, migrations, API, fixture and workers. Runtime fixtures remain disposable,
owner-guarded and profile-bound; browsers cannot choose arbitrary tenants. The
existing base2 Bash/PowerShell matrix remains, with one journey-reference Bash
entry. Prove actual supported pack creation/review/publication, search-link navigation
and visibility revocation in that profile. Do not claim generic page rendering,
all-family maturity, disabled-profile runtime proof or representative PowerShell
coverage that has not actually run.

## Explicit public text authoring

Managed workspace records need an intentional public-text authoring path, not
automatic promotion of private dynamic values. Add optional `publicContent` with
required `excerpt` and `body` strings to normal record create/update. Limits are
2,000 and 20,000 Unicode code points respectively, matching bounded plain-text
semantics. Reject null, unknown keys, nonstrings and NUL; do not trim or interpret
HTML. Omitted create copy is empty; omitted update copy is preserved; an explicit
empty pair clears it. All authenticated record responses include the persisted pair.
Public endpoints/search continue to use only existing explicit public fields under
current state, review, membership and site-visibility gates.

Save values and public copy atomically under the existing version precondition and
lock order. Public-copy edits participate in current semantic approval invalidation;
no new roles, grants, metadata authoring, automatic private-field projection or generic
renderer is permitted. Canonical native validation precedes the mirrored API path.

New revision snapshots use the collision-safe `snapshotFormat: workspace-record-v1`
envelope with values, publicContent and existing forensic record context. Preserve
revision numbering and the persisted state captured by each existing producer;
context is historical evidence, never restoration authority. Restoration changes
only supported values/public copy, never historical state, title, slug, metadata or
flags. Recognized legacy full snapshots restore their explicit copy; legacy flat
values snapshots preserve current public copy. Unknown/malformed formats fail closed.
Expose history restore coverage and actual restoration result so the UI can explain
legacy partial restoration before the user confirms it. Existing identity-history
pseudonymization, legal holds and record retention boundaries remain intact; this
feature does not claim generic erasure of free-form personal content.
