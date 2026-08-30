# Settings API Contract v1

- `GET /settings/capabilities`: safe enabled categories, routes, versions, and dependencies.
- `GET /settings/preferences`: effective typed preferences, supported values, schema version, and optimistic version.
- `PUT /settings/preferences`: complete v1 values plus `expected_version`; unknown values return 422 and stale versions return non-mutating 409.
- `GET/PUT /settings/notifications`: allowlisted delivery choices; mandatory delivery cannot be disabled.
- `GET /settings/security-events`: bounded redacted owner-only events.

Existing `/users/me`, `/auth/sessions`, `/identity/*`, `/privacy/*`, and authorized `/identity/admin/*` contracts are integrated rather than duplicated.

Feature 103 adds `/privacy/deactivate` as a durable recent-authenticated operation with exact `DEACTIVATE` confirmation. Its worker refuses to deactivate a final organization owner, revokes active refresh tokens, suspends memberships, and preserves account data. Permanent deletion remains a separate exact-`DELETE` operation.

Common typed errors: `recent_reauthentication_required`, `csrf_failed`, `not_found`, `settings_version_conflict`, `settings_value_invalid`, and `settings_dependency_unavailable`.
