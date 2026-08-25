# Operations observability

Base2 telemetry uses bounded event kinds, stable diagnostic codes, and caller-supplied correlation IDs. Secret-shaped keys and values are redacted recursively before an event or diagnostic bundle is serialized. Diagnostic bundles contain only the exact source commit, boot identity, bounded events, health, queue depth, adapter state, and an integrity digest.

The private alert ledger emits once when an incident begins and once when it recovers; repeated observations are idempotent. It is atomically replaced with owner-only permissions. Corrupt or unsafe state fails closed. This local telemetry contract grants no notification-provider, credential, deployment, or service-control authority.
