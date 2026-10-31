# Plan

## Scope and environment

Candidate starts at main `ada05a0`. Owner authorized a separate cloud checkout and
a draft PR in lieu of native WSL on 2026-10-30; no merge/deployment authority.
Repository constitution and existing release gates remain in force. Docker is not
available locally. Run supported repository entrypoints where prerequisites exist;
record blocked Compose/database/browser stages, never replace them with mock proof.

## Architecture

1. Reuse canonical existing Django preference/notification models: this slice adds
   no domain entity, persistent field or schema migration. Implement API semantics
   before React integration, preserving Django → FastAPI → React ordering.
2. Add a closed server-side settings registry. Runtime module enablement comes only
   from `SITE_MANIFEST`; role projection comes from current tenant membership and
   existing `is_allowed`. Categories, personal control descriptors and module cards
   extend the existing v1 capability response additively. Existing action endpoints
   remain authoritative and recheck permissions.
3. Keep SettingsCenter's layout/components. Consume trusted, closed category/path
   allowlists, scope and control metadata. Fail closed on capability failure.
4. Use stable category/control fragment links and effect-based focus after loading.
   Search uses only static metadata and stays inside this application.
5. Correct preference first-insert race with unique-conflict-safe insertion; return
   exact write snapshot in the same transaction, not a later racing GET. Keep the
   version precondition and user/tenant predicates.
6. Prevent writes before preference load, serialize notification payload fields,
   freeze saving forms, preserve failed drafts, provide explicit reload/discard.
7. The appearance subsystem provides theme/application adapters; SettingsCenter calls
   its shared apply function only for accepted persisted reads and successful saves.
8. The security repair covers the tenant-scoped audit query and regression tests.

## Compatibility and rollback

Capability fields are additive; category admission is deliberately stricter. Existing
personal endpoints and persisted rows remain compatible. No destructive migration.
Rollback UI/API together; database values are unchanged. No new provider calls.

## Test plan and budget

First add API and React regressions. Run focused checks in one batch after edits,
then coverage, lint/build and affected browser checks as dependencies permit. Do
not run heavy suites concurrently or modify their inputs while they run. Full
Compose and visual-release gates remain required before release; screenshot
baselines must not be renewed without inspected captures and authorized review.
