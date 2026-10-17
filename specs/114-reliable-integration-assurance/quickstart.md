# Sending-only preview acceptance

## Selected Google popup flow

The login page obtains a same-origin POST /api/auth/oauth/google/challenge before
rendering Google. The response is no-store, has a 300-second nonce and sets a
host-only HttpOnly, SameSite=Strict cookie (Secure in production). The nonce is
passed to GIS; signed token verification must match it. Atomic Redis GETDEL
consumes the browser binding before identity/session mutation. Failures never
restore it or silently fall back. An expired/failed attempt requires clicking
Retry Google sign-in; there is no automatic repeated login. Redis is required.
No ID token or nonce is saved in browser persistent storage.

This is the GIS popup credential flow, not the separate authorization-code
callback. Client-secret/redirect/state settings are not enabled for this preview;
the unused code flow must not be described as live-tested or PKCE-complete.
Google readiness is distinct from successful human consent and session creation.
After changing the binding flow, a new approved live trial and owner confirmation
are required; the prior de2e9ec Google confirmation is historical evidence only.

Receiving is deferred. Never add an inbound MX record for this trial. Resend
domain verification was confirmed by the owner on 2026-10-16; this is not delivery
evidence. Keep the original Volcano design unchanged.

## Local checks

Run `bash scripts/bash/test-email-container.sh` in the native WSL checkout with
the existing `base2-e2e-isolated-api:latest` image. It mounts the current mail
source read-only, uses synthetic fixtures and disables container networking.
It checks first send, restart/duplicate rejection and corrupt-ledger rejection.
It is not a full-stack or external-delivery test. The PowerShell companion is
for PowerShell on the Linux operator runtime; the Python harness requires Linux.

## Persistent DNS

Use the existing `digital_ocean/scripts/bash/full-preview.sh mail-dns` entrypoint
(PowerShell companion also dispatches the same CLI). Supply `--config
digital_ocean/config/woodkilldev-resend-dns.json`, the existing private
`--credential-file`, and a private `--state-root` outside preview lease storage.
Default mode plans only; `--apply` requires authorized DNS changes. The four
sending records persist across teardown. Conflicts, incomplete inventory,
ambiguous writes and previously committed drift require reconciliation, never
blind replacement or deletion. Preserve journal files. A successful provider
readback is not proof of global DNS propagation or Resend verification.

## Explicit mail trial

The full-preview launch CLI accepts an optional `--mail-trial-file`. Without it,
the existing synthetic-email behavior remains unchanged. This is a private,
owner-only regular JSON file with exactly these fields:

- `domain`: `woodkilldev.com`
- `apiKey`: resolved privately from Vaultwarden `base2/RESEND_API_KEY` login password
- `fromAddress`: the item's validated sender address on `woodkilldev.com`
- `recipient`: `thejunkmailvoid@gmail.com`
- `expiresAt`: Unix timestamp, in the future and no more than one hour away
- `maxAttempts`: integer from 1 through 5

Do not paste the JSON into chat, commit it or include it in deployment archives.
Create it only when the approved exact-source preview is ready. The launcher
validates it and ensures persistent DNS before provisioning. SSH handoff is
separate from source; the remote bootstrap creates private worker-owned key and
budget files and consumes the input. An existing budget directory is an error,
not permission to reset it. Trial expiry must remain within the approved preview
lease, and no send may be scheduled after teardown.

Each request consumes a durable reservation before transport. Failures are not
refunded; duplicate/uncertain sends require reconciliation. Provider acceptance
is stored as `sent`, but actual mailbox receipt must be verified separately.
Record sanitized message identifiers/statuses only, not tokens, message bodies,
reset URLs or credentials. Live verification/reset journeys require the complete
release checks and the existing one-droplet/60-minute/USD0.25 approval. Teardown
must leave persistent mail DNS untouched. Google OAuth is a separate prerequisite.

## Email failure observation

The existing minute-based email replay task now publishes a deployment-scoped,
180-second Redis observation. Only the email worker reads the outbox, using a
two-second statement timeout. Unresolved failed/dead-letter messages or queued,
retrying or sending messages older than ten minutes require attention. No
recipient, body, subject, token, count or message identity enters the observation.

The operations email probe rejects stale (over 120 seconds), malformed or
wrong-deployment observations. A healthy transport still requires the existing
signed delivery receipt; it does not prove inbox receipt. Existing operations
incident correlation and explicitly configured notification delivery handle the
closed status codes. This does not implicitly enable Discord credentials or
grant the operations worker access to the email outbox. Observation/publication
failures remain failed tasks, not silent passes. A dead letter must be explicitly
reconciled; neither a later successful send nor a retry clears it.

## Google account-link compatibility

Automatic linking to an existing email account now requires provider verification
and current Google authority (Gmail or a verified hosted-domain claim). A verified
local account alone, or a Google-verified third-party mailbox without a hosted
domain, is not sufficient. Such users can still use their existing password;
automatic linking is rejected without changing their account. A separate
authenticated account-link challenge remains future work, not an implicit bypass.
Already-linked provider subjects continue using their stable subject association.
