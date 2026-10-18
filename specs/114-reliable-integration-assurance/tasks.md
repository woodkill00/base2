# Tasks

## Final closeout repair batch

- [x] T077 Preserve the be2618d gate timeout, measure the unchanged 102-case journey matrix once under a bounded diagnostic, and correct only its aggregate gate timeout with a regression preserving the complete command, required status and single attempt. Final exact-source gate remains required.

- [x] T076 Correct the live empty-form assertion to distinguish exactly one configured Google challenge from credential exchange, assert no new POST on empty submit, and add provider-free browser/contract regressions. Preserve the 2e95988 live failures; do not relabel the changed harness as an exact-source live pass.

- [x] T071 Reproduce Gunicorn's default control socket against a non-writable home using the actual API entrypoint, disable the unused control surface, and retain HTTP readiness/shutdown tests without weakening container isolation.
- [x] T072 Review measured pgAdmin startup against the configured health/startup bounds; preserve slow-start evidence and distinguish initialization from runtime failure.
- [ ] T073 Reconcile tasks against exact-source local/CI/live evidence, audit integration notification and security gaps, and explicitly retain unexplained intermittency.
- [x] T074 Verify current local/hosted evidence, merge PR #80 with ancestry preserved, and verify post-merge CI; no additional live trial authorized.
- [x] T075 Bind the selected GIS popup ID token to a server-issued, expiring, one-use browser nonce; test missing/wrong browser, expiry, replay, provider failure, Redis failure, disabled mode and UI recovery. Keep the unused authorization-code path explicitly separate. Fresh human live validation requires renewed approval before merge.

Reconciliation (2026-10-18): T074-T076 are supported by exact candidate
`32fd45adb43d3f5b263c0cc00ae4abb6014760d9`, the 129-check gate
`.artifacts/complete-gate/20261017T031147Z-2910700/result.json`, the 14-pass
live run `base2-full-20261017-035146`, owner Google sign-in confirmation and
verified teardown, and history-preserving PR80 merge `b859e54ae957d6e26b56c4d6a3f884b7a53f516f`.
All ten post-merge workflows passed (20 check-runs); the PR closeout comment
records that evidence. This does not close the remaining integration, visual,
optional-module or unresolved-intermittency tasks; these continue in Feature115.

## Custom-field credential repair

- [x] T057 Add a pure, Base2-only Google credential reader accepting exactly one `value` text/hidden custom field, with managed-Notes fallback and fail-closed conflicts/malformed data (R02,R04).
- [x] T058 Test credential selection, duplicates, placeholders, invalid metadata/types and sanitized errors; use this same reader for private metadata preflight (R02,R04).

## Discovery and analysis

- [x] T001 Read constitution, current source, previous ledger and final evidence (R01,R08).
- [x] T002 Create feature branch, requirements, budget and trust boundaries (R01-R09).
- [x] T003 Inventory integration configuration, optional capabilities and visual gaps (R03-R06).
- [x] T004 Complete initial tasks -> analysis -> additional tasks review (R01-R09).

## CI selection

- [x] T005 Add failing classifier regressions for narrative-only, code, mixed and unknown paths (R07).
- [x] T006 Test exact PR/push comparison ranges, missing history, rename/delete and hostile paths (R07,R08).
- [x] T007 Implement conservative classifier and private/sanitized decision evidence (R07,R08).
- [x] T008 Add supported Bash/PowerShell entrypoints and immutable base-policy invocation (R07).
- [x] T009 Preserve required check names and gate expensive frontend steps only after classification (R07).
- [x] T010 Verify skipped suites are explicit, required artifacts conditional, security checks unchanged (R07).
- [x] T011 Validate both narrative-only and full-code decisions and record measured counts/durations (R08).

## Reliability

- [x] T012 Inspect original Django traceback and compare runtime/toolchain evidence (R01,R02).
- [x] T013 Run bounded reproductions; classify outcome without erasing intermittency (R01).
- [x] T014 Add diagnostic regressions for startup/transfer/timeout and unsafe evidence (R02).
- [x] T015 Implement evidence-backed fixes or explicit unresolved-incident handling (R01,R02).
- [x] T016 Verify cleanup and original failure status survive diagnostics failure (R02).

## Real integrations

- [x] T017 Confirm test identities, private credential references, recipient and live bounds (R03,R04,R09).
- [x] T018 Add secret-safe email/OAuth preflight and missing/invalid prerequisite tests (R03,R04).
- [ ] T019 Validate Resend HTTPS transport, recipient scope, timeout/idempotency and delivery evidence (R03).
- [ ] T020 Validate OAuth callback allowlist, state/nonce/PKCE, replay, denial and session tests (R04).
- [ ] T021 Add bounded real email journeys with cleanup and redacted artifacts (R03).
- [x] T022 Run dedicated-account real OAuth trial with human consent/MFA when required (R04).

## Coverage expansion

- [ ] T023 Inventory representative public/auth/settings/content visual states (R05).
- [ ] T024 Add failing state-entry, geometry, accessibility and reference-comparison tests (R05).
- [ ] T025 Inspect captures across mobile/desktop, keyboard/zoom, RTL and long content (R05).
- [ ] T026 Review intentional added references; preserve existing Volcano references (R05).
- [ ] T027 Add isolated enabled-module real-backend data/lifecycle acceptance (R06).
- [ ] T028 Verify denied roles, duplicates, recovery and exact disposable-data cleanup (R06).
- [ ] T029 Reconcile route/state ledger with actual evidence and remaining exclusions (R05,R06,R08).

## Release

- [x] T065 Reproduce live audit injection failure and use CSP-safe browser instrumentation without bypassCSP or weaker headers; add regression contract.
- [x] T066 Add opt-in fixed Google stylesheet source at the Traefik consumer, not only Nginx; cover both Compose profiles, disabled defaults and hostile overrides.
- [x] T067 Replace the media live fixture's client-side permission claim with a bounded server-provisioned synthetic tenant membership; retain nonmember/forged-client denial tests and never enable public first-owner bootstrap.
- [x] T068 Owner reports the origin already configured: verify client-ID binding and effective referrer policy before requesting console edits; validate localized button readiness, provider errors, popup/session and account-linking behavior independently.
- [x] T070 Fix the opt-in public preview referrer policy without changing private/canary policies; reproduce CSP and origin-header behavior in a real browser with synthetic endpoints.
- [x] T069 Run affected browser/security checks and the exact-source release gate for post-trial repairs before publication; any further paid trial requires new approval.

- [x] T063 Classify pre-bootstrap transport and receipt failures with fixed sanitized stages; cover timeout, nonzero exit and malformed/non-object receipts without logging secrets.
- [x] T064 Revalidate the repaired candidate through required release checks, then obtain renewed bounded-trial approval before any new paid launch; retain original failure and verified cleanup evidence.

- [x] T061 Repair F114-19 integration fixture to use existing worker UPDATE authority and restore its synthetic status; verify actual restricted-role DB execution, no new grants and CI (R02,R03).
- [x] T062 Add outbox integration to the existing disposable PostgreSQL local gate so hosted CI is not its first execution (R02,R03,R08).

- [x] T059 Add required live empty-form auth validation at mobile/desktop in light/dark preferences; assert state entry, field association, layout, menus, accessibility, no auth requests and sanitized screenshots (R04,R05).
- [x] T060 Complete private Google client-ID deployment wiring and restrictive GIS CSP; test provider button readiness separately from human consent and successful session establishment (R04,R09).

- [ ] T030 Repeat analysis and close known blocking task gaps (R01-R09).
- [x] T031 Run focused tests, affected integration, changed-line coverage and reviewed visuals (R01-R08).
- [x] T032 Run complete gate, publish candidate and verify hosted checks (R08).
- [x] T033 Run approved bounded live acceptance including available authorized integrations (R09).
- [x] T034 Tear down owned resources and verify empty inventory and terminal lease (R09).
- [ ] T035 Record exact-source outcome, open risks and measured cost/time evidence (R01,R08,R09).

Blocked prerequisites are not completed tasks. Publication does not imply live acceptance.

## Additional tasks from cycle 3

- [x] T036 Reconcile Google redirect HTTP method, browser callback consumer and configured URL before real-account testing (R04).
- [ ] T037 Verify actual selected Google flow's PKCE/client boundary and add missing security regressions rather than assuming the two OAuth entrypoints are equivalent (R04).
- [x] T038 Add explicitly scoped private Resend/OAuth wiring to the preview entrypoint; default remains disabled and unrelated secrets are not copied (R03,R04,R09).

## Additional tasks from cycle 4

- [x] T039 Implement fixed-endpoint Resend transport with private key files, required trial recipient allowlist, no redirects/proxy inheritance and sanitized errors; retain existing SMTP compatibility (R02,R03).
- [x] T040 Test success, malformed responses, auth/quota failures, timeouts, duplicate keys, denied recipients and disabled defaults without network calls (R03).
- [x] T041 Bound retries to provider idempotency retention and enforce durable trial send limits before activation; distinguish provider acceptance from inbox delivery (R03,R09).
- [x] T042 Confirm verified sending subdomain and sending-only domain-scoped key in Vaultwarden; do not create accounts, change DNS or broaden permissions implicitly (R03,R09).

T042 evidence: domain verification and inbox receipt were confirmed previously;
on 2026-10-17 the owner explicitly confirmed "Sending access, woodkilldev.com only".
This is owner-confirmed permission evidence, not an independent API scope probe.

## Additional tasks from cycle 5 — owner-supplied DNS

- [x] T043 Inspect authoritative zone and saved Resend login metadata privately; owner selected woodkilldev.com (not the earlier proposed subdomain). Confirm sender/key domain match (R03).
- [x] T044 Store owner-supplied public sending DNS records separately from ephemeral droplet DNS; test deterministic missing/matching/conflict plans and preserve stricter existing DMARC (R03,R09).
- [x] T045 Integrate opt-in persistent DNS reconciliation into supported deployment entrypoints before spending, with zone delegation validation, complete paginated inventory, bounded provider requests and verified receipts (R03,R09).
- [x] T046 Test interrupted/ambiguous creates and concurrent reconciliation without duplicate writes; teardown must never delete persistent mail records or existing mail configuration (R03,R09).
- [x] T047 Apply authorized nonconflicting sending records and verify authoritative DNS plus Resend status; receiving MX requires a separate explicit decision after existing inbound routing review (R03,R09).

T047 complete: all four sending records verified in provider inventory and public
DNS; owner confirmed Resend verification and actual inbox receipt. Receiving is
explicitly deferred to a future owner-managed inbox feature; do not add MX.

- [ ] T048 Verify trial budget/key ownership and persistence in actual containers, exact live-lease initialization and refusal to recreate/reset existing budgets (R03,R09).
- [x] T049 Finish failure-code classification and operator notification coverage for provider failures and all send guards; verify no credential, recipient body or reset token leaks (R02,R03).

## Additional tasks from cycle 9

- [x] T050 Reproduce missing frontend/API startup dependency in both Compose profiles; verify API health contract and acyclic dependency graph (R01,R02).
- [x] T051 Gate frontend startup on API health without changing visual sources, proxy/security policy or service authority; validate both resolved configurations (R01,R02).
- [x] T052 Connect email failure observation to the existing operations incident/notification path; cover isolation, deduplication, stale observations and notification delivery failures (R02,R03).
- [x] T053 Reject automatic account linking for provider-unverified email even when the existing local account is verified; verify no account/session mutation (R04).
- [x] T054 Require current Google mailbox authority for automatic collision linking, test third-party verified rejection and signed hosted-domain claim parsing (R04).
- [x] T055 Reconcile Google button CSP/client origin settings with the chosen sign-in flow before activation; do not weaken the site's default policy globally (R04).
- [x] T056 Diagnose F114-17 using equivalent isolated toolchains and preserve the failed exact-source repetition; require valid stability/release evidence before publication (R01,R02,R08).

Sending acceptance update: candidate 6f7f7392 passed the complete gate, 20 hosted
checks and 11 live browser checks. Owner confirmed inbox receipt of the single
reset email. Trial teardown verified; authorization consumed. T017/T018/T038 still
include unfinished OAuth work; do not mark those combined tasks complete.
