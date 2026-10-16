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
