# Community and support packs

Community submissions require an authenticated public-account principal and a tenant-bound request. Text is normalized, bounded, rejected for active-content patterns, scored deterministically for abuse, stored as non-searchable draft content, and always enters `pending` moderation. Only explicit reviewed moderation transitions can publish it. Notification messages contain opaque record IDs and event codes, never post bodies or account details.

Support reuses the durable form/outbox pipeline with additional processing consent and a forced private/retention classification. Idempotency, CSRF, rate limiting, expiry, delivery status, and dead-letter behavior remain inherited from that pipeline. Email is declared but disabled until separately configured.
