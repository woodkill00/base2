# Feature 121: Settings capability foundation

Created: 2026-10-30. Status: implementation; release acceptance pending.

## User outcome

Extend, rather than replace, the approved Obsidian/Volcano settings center. People
can find individual settings, understand who a change affects, use existing site
capabilities, and recover safely from unavailable or stale data. Breadth is a
traceable roadmap, not a claim that every site engine is complete.

## Acceptance

- **AC1 Discovery:** Personal categories are distinct from organization administration.
  Administrative links derive from current active tenant membership and permission;
  missing/failed capability data does not reveal fallback administrative controls.
- **AC2 Findability:** Local search matches individual labels, help and synonyms and
  opens durable, keyboard-focusable control links. Only admitted categories appear.
- **AC3 Scope:** Personal preferences explicitly affect this user on this site.
  Site modules are deployment-managed; no unsupported inheritance or activation
  switches are offered. Existing authorized workspace links remain usable.
- **AC4 Integrity:** No edit is enabled from an unknown initial preference value.
  Saving has visible pending/success/error state, preserves a failed draft, prevents
  duplicate submission, and offers explicit reload/discard recovery after conflict.
  Concurrent first saves return a conflict instead of a database failure.
- **AC5 Honest availability:** Site families distinguish enabled module foundations,
  limited operational surfaces, and planned feature engines. Fake payment adapters,
  saved-only notification delivery preferences and unimplemented providers must not
  be described as working production features.
- **AC6 Notifications:** Timestamp-bearing stored notification choices can be saved
  repeatedly without submitting server-managed fields as untrusted mutation keys.
- **AC7 Appearance:** Persisted appearance integrates with the existing theme and
  accessibility mechanisms without changing the approved design. Missing unsaved
  defaults must not overwrite a visitor's existing theme choice.
- **AC8 Assurance:** New authorization, failure, first-write concurrency, deep-link,
  repeated-save and applied-preference cases receive regression tests. Report focused,
  full-gate and visual evidence separately; no claim of flawless operation.

## Non-goals

No production deployment, merge, billing provider, live payment, social graph, CRM
workflow engine, arbitrary settings JSON, organization inheritance, or permission
editor is introduced. Notification delivery-engine integration and notification
optimistic concurrency remain planned unless implemented with dedicated contracts.
