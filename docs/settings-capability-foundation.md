# Settings: finding controls and understanding scope

Feature 121 extends the existing Obsidian/Volcano Settings Center. It does not
replace its design or implement every engine suggested by the site-family roadmap.

## Find a setting

Open `/settings`, browse categories, or search by a label or synonym (for example,
**night mode**). Individual results link directly to a control such as
`/settings/appearance#theme`, and focus moves to that control after it loads.
Search uses local, static metadata: queries are not sent to a search provider.
Only categories admitted by the API appear. A missing notification family or an
unavailable setting produces an explanation, not a link pretending it is editable.

## Understand who is affected

- **Account:** Profile identity and sign-in/security. These are shared account
  settings, not overrides for one site.
- **Personal:** Preferences and notification choices associated with your user and
  the current generated site. There is no organization inheritance.
- **Organization:** Administration/integration navigation appears only when your
  current active tenant membership grants the existing required permissions.
  Every action still checks permission on the server; hidden links are not security.
- **Site:** `/settings/site-capabilities` lists module foundations enabled in the
  generated runtime manifest. Activation is deployment-managed. Existing content
  and media workspaces are linked only when enabled and authorized. No switch here
  enables providers, payments, CRM automation, social graphs or subscription engines.

This application has one immutable generated `siteId`, also used by the API tenant
header. There is no in-session tenant selector. Switching account identity resets
settings drafts and discovery state; late responses cannot update the new account.

## Save and recover

Preference forms load known values before allowing a write. **Save preferences**
freezes the form while saving. A failed save retains the draft. Another tab's write
causes a conflict, not a silent overwrite; **Discard draft and reload** explicitly
loads the latest version before editing again. The page warns before a full browser
unload with an unsaved preference draft. Browsing settings categories preserves the
draft, but leaving this page through other app navigation is not a durable draft store.

If discovery fails, administrative links stay hidden; use **Retry settings discovery**.
If preferences fail to load, use **Reload preferences**. Network-unavailable state is
not represented as fetched defaults. Discovery/read and preference/notification-save requests have 10-second timeouts.
A timeout or uncertain server failure does not prove the change failed: the draft
is retained, another save is blocked, and explicit reload is required to reconcile
with the stored state. No timed-out write is automatically replayed.

## Appearance

Saved theme, contrast, motion and density are applied through the existing appearance
system after verified sign-in and after an accepted save/reload. Version-zero defaults
do not overwrite a visitor's existing theme choice. The header theme toggle is a
**temporary override** for a signed-in user; use Settings to save an account preference.
Saved system choices follow operating-system changes. Reduced-motion OS preferences
remain a safety floor, even if a saved choice says full motion. Explicit standard
contrast overrides the OS contrast preference; system contrast follows it.

The guest/brand baseline remains visible while an authenticated read is pending;
navigation is not blocked behind that request. No authentication credentials are
stored in browser storage by this feature.

Language changes apply to the existing localized settings UI. Time zone and week
start are stored preferences; consumers outside settings are not all wired to them.
Do not infer a complete scheduling/localization engine from their persistence.

## Notification limitations

Stored notification rows can be edited and repeatedly saved, including after reload.
Only `event_family`, `channel`, and `delivery` are submitted; server timestamps and
mandatory classification are not accepted mutation fields. Required families cannot
be disabled through the existing validated contract.

**Delivery-engine integration is not yet available:** saving these preferences does
not change live message delivery. Notification-set optimistic concurrency is also
not implemented; concurrent notification edits remain last-write-wins. Those are
explicit next-phase tasks, not completed features.

## API compatibility

`GET /api/settings/capabilities` retains `schema_version: 1` and its original category
shape, with additive `scope`, `controls`, `modules`, and `locales` metadata. Organization
and developer categories are now restricted by active membership and permission.
Known UI categories, control anchors and internal workspace paths are allowlisted.
The module registry provides display metadata only: generated `SITE_MANIFEST` remains
the source of truth for enablement and existing APIs enforce all mutations.

Preference storage/model shape is unchanged. First insertion handles a concurrent
unique-key winner as a version conflict, and successful mutations return the exact
snapshot from that transaction. No database migration or provider operation is added.

## Verification limits

See `specs/121-settings-capability-foundation/tasks.md` for the current issue ledger.
Focused unit/contract results, real PostgreSQL integration, restricted-role RLS,
browser assertions and approved visual baselines are separate evidence. A passing
mock-backed test is not proof of production persistence or absence of unknown defects.

Developer settings do not guess a protected API-documentation URL. That access is
configured by deployment; ask an administrator for the approved endpoint. Public
`/docs` content is not mislabeled as API documentation.
