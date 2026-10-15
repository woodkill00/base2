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

Await owner test mailbox/Google identity and Vaultwarden item names; do not assume
the previously authorized Calendar OAuth grant is a Base2 sign-in credential.
Await fresh bounded preview approval; earlier trial approvals were consumed.
