# Plan

## Candidate and budget

Start: main 433068c4dc57499c46b1b0f5d246c7a5ac45b91b, native WSL checkout.
No active cloud resource. Preserve untracked/private files. One focused diagnostic
sweep per batch; maximum one documented diagnostic retry, never blanket retries.
Heavy suites serial. Full release gate after focused/integration/visual evidence
is ready. Live limits and test identities requested before provider actions.

## Batches

1. CI: classify exact Git differences using NUL-delimited paths, validated SHAs
   and immutable base-version policy. Only explicitly allowlisted narrative
   Markdown qualifies. JSON, generated profiles, snapshots, tests, scripts,
   workflows, config and unknown paths require full checks. Missing history or
   malformed input requires full checks or a visible failed prerequisite.
   Preserve existing required check names. Emit decision evidence before skipping
   expensive steps, not a fabricated browser pass. Test rename/delete/mixed paths,
   malicious paths and base-policy tampering. Keep security scanning unchanged.
2. Reliability: inspect preserved Django failure and successful comparison runs;
   bounded reproduction with existing test entrypoints and runtime settings.
   Record interpreter/toolchain and resource state without secrets. Extend fixed
   remote stage evidence where required, including timeout/transfer failures and
   cleanup reporting. Never raise antivirus waits based only on a hypothesis.
3. Integrations: inventory existing OAuth and mail boundaries, deployment secret
   wiring and test identity/redirect prerequisites. Add supported private preflight
   and bounded test operations with Bash/PowerShell parity. Test negative paths
   locally before any real email or OAuth authorization. Owner-only test mailbox
   and dedicated account required; no reusable owner password changes.
4. Coverage: map remaining ledger states to actual test entrypoints and backend
   fixtures; expand capture/comparison cases and inspect fresh differences. Add
   isolated optional-profile backend/lifecycle acceptance without changing the
   default profile. New screenshot references require actual visual review.
5. Release: tasks -> analysis -> fixed/additional tasks -> analysis for each batch;
   coverage impact review, complete gate, hosted CI, approved bounded live run,
   cleanup and final source-bound report. Preserve merge ancestry.

## Trust boundaries

### Persistent DNS (owner update)

Use root domain woodkilldev.com as selected in the owner's Resend dashboard.
The public configuration digital_ocean/config/woodkilldev-resend-dns.json stores
the supplied DKIM and two CNAME records plus initial DMARC. Provider-specific
"Auto" TTL becomes explicit 3600 seconds. DNS names are zone-relative; CNAME
targets are absolute. Do not invent extra SPF records alongside those supplied.
Verify authoritative delegation and complete provider inventory before writes.
Each deployment should ensure this persistent set, not recreate it blindly.
Existing exact records are no-ops; conflicts stop and report; existing DMARC
requires review rather than downgrade. Persistent records never enter droplet
expiry/teardown ownership. Provider receipt IDs and partial progress require a
separate durable journal before automatic mutation is enabled.
The supplied apex MX inbound-smtp.us-east-1.amazonaws.com (priority 10) is NOT
included: receiving is optional and needs separate inbound-routing approval.
No droplet is needed to verify email DNS. The Resend key remains in Vaultwarden;
the DKIM verification key is public DNS data, not a private credential.

### Email provider decision (2026-10-16)

Trial activation uses a private durable operational send-budget ledger, separate
from domain email data: exact expiry, maximum attempts and hashed delivery-key
reservations, synchronized across workers before network access. Reservations
are never refunded after errors; an uncertain or repeated key requires explicit
reconciliation, so no automatic retry can outlive provider idempotency. The ledger
must persist across worker restarts, is never automatically reset, and is mounted
only into the email worker. Missing, corrupt, expired or exhausted budgets fail
closed with a visible typed error. Live trial initialization remains a supported
deployment step, not an application-side auto-create operation.

Owner selected Resend over HTTPS. DigitalOcean blocks SMTP ports, so SMTP is
retained for existing consumers but is not the preview transport. Use the fixed
https://api.resend.com/emails endpoint, verified TLS, no redirects or inherited
proxies, a private sending-only domain-scoped key, and a mandatory exact trial
recipient allowlist. The adapter does not retry internally. Stable outbox keys
map to provider idempotency keys; Resend retains them for 24 hours, so automatic
retry scheduling must stay inside that window or require reconciliation.
Provider acceptance (existing outbox `sent`) does not prove inbox delivery.
Real acceptance requires separate mailbox evidence. Durable trial send caps,
secret wiring and retry scheduling are activation prerequisites, not implied by
unit-test success. No DNS changes or provider account creation are authorized.

References: https://resend.com/docs/api-reference/emails/send-email and
https://resend.com/docs/dashboard/emails/idempotency-keys and
https://docs.digitalocean.com/support/why-is-smtp-blocked/.

PR-controlled filenames/content cannot grant skipped validation or credentials.
No pull_request_target execution of untrusted code. CI permissions stay read-only
unless an existing explicit publication job requires otherwise. External callback
URLs and recipients are exact allowlists. Secrets remain in private references;
screenshots/traces must not retain authorization codes or reset links.

## Integration blockers

Owner confirmed thejunkmailvoid@gmail.com as the test identity and authorized
Base2 account verification/reset emails to that mailbox, not changes to the Google
account itself. Owner approved one Frankfurt droplet, staging certificates,
maximum 60 minutes/USD 0.25 and teardown after testing. This approval is unused.
Do not assume the previous Calendar OAuth grant is a Base2 sign-in credential.
Vaultwarden item references and SMTP/OAuth wiring still need verification.

2026-10-16 prerequisite check: Pi SSH unavailable at all four configured addresses
(192.168.1.169, 192.168.1.168, 192.168.0.169, 192.168.0.168). The metadata-only
vault lookup could not connect; this is not evidence of missing credentials.
Subsequent owner restart resolved reachability: SSH and Vaultwarden are reachable
via 192.168.0.169 using the existing fallback helper. Read-only value-status checks
found missing/placeholders in base2/EMAIL_HOST, base2/EMAIL_HOST_PASSWORD,
base2/GOOGLE_OAUTH_CLIENT_ID and base2/GOOGLE_OAUTH_CLIENT_SECRET. The saved
base2/GOOGLE_OAUTH_REDIRECT_URI does not match the expected Base2 callback and
requires review. Populated username/from/state entries are not provider-verified.
Real integrations remain blocked until valid provider configuration is supplied;
no external email/login or cloud operation was attempted.
