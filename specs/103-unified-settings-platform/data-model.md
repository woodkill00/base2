# Data Model

## UserPreferenceSet

One row per user and optional organization: UUID, schema version, optimistic version, theme (`system|light|dark`), contrast (`system|standard|high`), motion (`system|full|reduced`), density (`comfortable|compact`), configured locale, IANA timezone, week start (`system|monday|sunday|saturday`), and timestamps.

## NotificationPreference

One row per owner/context/event family/channel: UUID, allowlisted event family, channel (`email|in_app|browser`), delivery (`immediate|digest|disabled`), server-derived mandatory classification, and timestamps. Mandatory families reject disabled delivery.

## SettingsCapability

Static safe metadata derived from validated manifest and server implementation: IDs, versions, routes, labels, dependencies, and enabled state. It contains no secrets or provider configuration.

## SecurityEventView

Redacted owner projection: event ID, allowlisted category/action, timestamp, coarse device information, and recognition status.

## Compatibility

Existing users receive defaults without row creation. First mutation creates the set. Existing profile/session/privacy endpoints remain compatible. Unknown future schema versions fail closed.
