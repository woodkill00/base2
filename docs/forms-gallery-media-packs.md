# Forms, gallery, and media packs

The forms pack uses the existing tenant-owned form submission and delivery outbox. It validates bounded input and consent, rate limits by tenant/client, requires CSRF for cookie-authenticated mutation, binds idempotency keys to request digests, expires retained payloads, and exposes delivery failure instead of claiming success. Its email capability is a declaration only; the default adapter remains disabled.

The media pack uses quarantine-first assets. A file is not public until a reviewed scanner receipt and bounded safe variants transition it to validated. Metadata is stripped, executable delivery is not supported, every lookup is tenant-bound, and retention/deletion state is explicit. Its storage capability does not activate a provider or credential.

The gallery pack depends on media and uses `gallery-item` content records. It can reference only media returned by the validated media endpoint. Disabling gallery preserves records and removes its routes/jobs through the lifecycle plan; disabling media prevents gallery from satisfying its dependency health.
