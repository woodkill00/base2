# Shared workspace settings and review

Feature 124 extends the existing Settings Center. It does not enable additional
modules, change the site's design, activate a mail provider or complete every site
family. Integration and release acceptance must be checked for the deployed version.

## Find the controls

Sign in and open **Settings**. Search for a setting, or use:

- `/settings/notifications`: your notification choices on this site.
- `/settings/organization#workspace-publishing-review`: the publishing-review rule.
- `/settings/site-capabilities#workspace-content-visibility`: workspace content visibility.

The shared controls require enabled accounts/content-workspace capabilities and an
active organization membership. Owners and administrators can save policy changes.
Other active members can see authorized effective policy information without gaining
write permission. A missing or unauthorized control is not replaced with a working-looking
switch. Module activation remains deployment-managed, and there is no tenant selector.

## Save, cancel and recover

Notification choices and shared policy use versioned, atomic saves. Another tab or
administrator cannot silently overwrite a stale version. A conflict keeps your draft,
blocks repeated saves and offers an explicit discard/reload action. A timeout does
not prove that the server rejected the write: reload before trying again. Writes
are never automatically replayed.

Ordinary Cancel restores that form's saved snapshot. Organization and Site cards
share one policy version, but saving one card does not also commit another card's
unsaved field. Switching Settings categories retains ordinary drafts. Leaving
Settings offers Stay or Discard and leave; full browser unload uses its native warning.
Discarding a local draft does not cancel a request already sent. Authentication
recovery and account replacement remain available and do not retain old-account data.
The separate MFA/recovery-secret flow is not covered by this ordinary-draft contract.

## Publishing review

With required review enabled, authors submit a draft and a different authorized
owner/administrator approves its exact review subject. Approval alone does not publish.
Use the server-provided Publish or Schedule action afterward. Changes to publication
content, relationships, media or policy invalidate the relevant authorization; an
old approval cannot authorize a fresh submission of identical content.

Existing published revisions are not retroactively unpublished merely by enabling
the rule. Editing published content under that rule moves it back to draft. Scheduled
work rechecks policy and current authorization when it runs; a stale approval or
revoked permission cannot publish silently.

If no eligible independent reviewer exists, required-review submission fails with
recovery guidance. Add another authorized owner/administrator through existing
organization administration, then resubmit. Do not grant yourself approval by
relabeling authorship. Historical content with unknown attribution requires explicit
accountable draft adoption before required review; history is not rewritten.

When review is disabled, the existing workflow and publish permissions still apply.
Its in-review stage can be optional, including for a sole owner; the application does
not invent an independent approval requirement. Turning review off does not grant
new publishing roles. Only server-provided actions are displayed.

## Workspace content visibility

**Members only** restricts managed workspace records and their managed access paths.
Authorization is checked on direct reads, search, exports/downloads and bound assets,
not just by hiding navigation. Existing resource restrictions remain in force and
valid authorized member exports are not disabled indiscriminately.
Public-content endpoints remain public-only and hide restricted workspace content;
authorized members use the existing authenticated workspace views. This batch does
not add a member-facing paywall or automatically upgrade public routes into one.

**Public allowed** only permits records that are otherwise eligible to be public. It
does not publish drafts, expose private assets or override resource permissions.
These controls do not change static website pages, external internet links or copies
already downloaded. Restrictive activation is unavailable where required storage
privacy assurance is missing; this implementation does not certify a remote bucket.

## Notification behavior and limits

The complete preference set has one version. Required security/transactional choices
cannot be removed by omitting their rows or selecting Off. Missing optional product
email preference is treated as disabled, not automatic consent.

Review/workflow requests use **product / email** preferences, but delivery in this
feature is exclusively a durable **local test receipt**. No real email, browser push
or external provider is activated. Immediate, Off and daily UTC digest affect that
consumer. Duplicate work does not create another receipt; revoked access, stale
review subjects or changed preferences can suppress delivery. A closed digest with
all entries suppressed is not a delivered digest.

Required-review recipients must be independent reviewers. Optional-workflow
recipients may be authorized publishers other than the requester. The consumer
rechecks the current policy at delivery and never automatically adds new recipients
to an old request. An optional zero-recipient transition does not claim delivery.
Other notification families/channels remain saved preferences unless separately wired.

## Operator rollout and verification

Apply additive Django/API migrations and deploy compatible API/workers/UI together
through the repository's supported operational entrypoints. Old unversioned notification
writers are rejected rather than allowed to bypass concurrency checks. Backfills
preserve evidence-backed existing sites; a configured but empty new site retains the
conservative review-required/member-only default. Do not roll back to permissive
workers while restrictive policy is active.

Required evidence includes real PostgreSQL migration/RLS/concurrency tests, actual
multi-user browser flows and source-bound visual/accessibility review. SQLite and
mocked unit tests do not establish those results. Existing unrelated release blockers
remain blockers; a draft PR is not deployment approval.

The new-table privacy/retention helpers preserve scoped authorization and audit.
Local legacy physical purge uses a committed immutable plan and exact artifact keys
before deletion. Unsupported remote/governed histories, missing deletion evidence or
organization scope remain explicit blocked cases. Purged tombstones and execution
proof remain; this is not a general personal-data-erasure certification. See the
Feature 124 plan for the precise storage, rollback and retention boundaries.

### Current acceptance status and evidence boundaries

At the 2026-10-31 checkpoint, remote source
`e6deb5864ea9f38bad25d6261b756d35cefe1e81` has 8 of 10 workflows passing and all
433 synthetic browser tests green. The backend repair and new disposable
real-service journeys are still pending their next CI execution. These numbers are
not a complete-release pass or proof that the new live stack has run.

The new acceptance suite reuses the isolated repository runners and tests one
shared `base2-obsidian` site against actual API/PostgreSQL services:

- Login and notification two-tab conflict/reload use rendered browser interactions.
  Review, visibility, role, export and asset checks use authenticated API request
  contexts after real login; they are not UI-click coverage of those controls.
- Actual worker/beat execution is checked separately from deterministic UTC digest
  tests. The latter stop the queue consumer and run the production consumer in
  fresh restricted containers with a bounded test clock; they do not prove that
  beat executed at a simulated midnight.
- A viewer's own valid asset/export grants are checked before and after a fixed
  trusted fixture suspension, while still unexpired. This is a fixture-driven state
  change to one synthetic actor, not a user-facing suspension feature. Owner
  credentials remain confined to the one-shot setup service.
- Local HTTP/non-Secure cookies are not production TLS acceptance. A synthetic
  pre-ready asset exercises encrypted storage and access controls, not scanning.
  Notification receipts remain local-only; no real email is sent.

Separate Bash and PowerShell Ubuntu CI jobs retain success and failure artifacts;
their new runtime results remain pending. Adding the required journey to the
**133-check complete-gate manifest** does not execute that gate, and CI does not
currently invoke the entire gate. Representative publishing/docs/portfolio profile
coverage, migration/restore/race evidence, visual approval and independent release
blockers remain separate obligations. No deployment or TLS bypass is authorized by
this acceptance work.
