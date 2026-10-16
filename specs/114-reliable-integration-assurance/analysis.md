# Analysis and issue ledger

## Cycle 9 — post-trial reliability batch

Start candidate 6f7f7392ecb0b814ff64058756869cb969e71be1; clean native WSL
checkout. Both required local validation and all 20 hosted checks passed. Trial
base2-full-20261016-041421 passed eight route probes and 11 browser tests. Exactly
one reset request was accepted by Resend and the owner confirmed inbox receipt.
The droplet and six ephemeral DNS records were removed; four sending records
remain, no MX was added, and the temporary credential handoff was removed.
Evidence: PR #80 live acceptance comments and the private trial evidence directory.
The one approved live trial is consumed; do not provision another implicitly.

F114-14 (medium, product startup contract): frontend Nginx restarted while API
DNS did not yet exist, then recovered. Both local and development Compose files
lack a frontend dependency although its static proxy requires api:5001. Add a
healthy API dependency in both profiles, test health availability and graph
acyclicity, and validate resolved Compose configs. Preserve the original failure;
later live success does not erase it. No visual source or baseline changes needed.

F114-15 (medium, integration gap): an existing operations incident/Discord pipeline
exists, but email.delivery consumes a separately signed receipt rather than the
live outbox failure state. T049 must integrate sanitized outcomes with this path,
preserving worker least privilege, tenant boundaries, deduplication and visible
notification failures; logging alone does not complete notification acceptance.

Batch budget: focused regression sweep first, serial local integration next,
one complete gate only after the combined candidate is ready. Zero paid runs or
new live sends. Google credentials remain a prerequisite pending owner response.
Analysis adds T050-T052; no known planning gap remains for the startup sub-batch.

Adjacent OAuth review found F114-16 (high, account-link trust boundary): an
unlinked Google identity with email_verified=false could pass collision admission
solely because the existing local account was verified. Existing local verification
is not proof the provider identity owns that mailbox. Add a regression and require
provider-verified email before automatic linking. Existing already-linked subject
lookup remains unchanged. Live OAuth stays disabled pending credentials and
callback/PKCE reconciliation; the fix does not claim that broader review complete.

Focused outcome: missing dependency regressions failed in both profiles before
the fix; 12 startup/adjacent tests and both resolved Compose configs then passed.
Initial example-config validation correctly rejected its placeholder project
name; supplying a synthetic explicit project resolved this fixture prerequisite.
The email observer regression first failed collection before implementation.
Combined focused mail/startup suites passed 127 tests plus two subtests, adjacent
operations contracts passed 32 tests, and the new observer achieved 100% measured
line coverage with a 95% focused floor. Added real worker-role DB regression to
the integration suite; it is not claimed passed until that suite runs.
OAuth collision regression reproduced the verified-local bypass; both local
verification states now reject. Combined OAuth/observer/operations checks passed
69 tests. No UI source or visual reference changed; no new preview or email sent.

Notification activation remains separate: this batch wires durable-outbox
observation to existing incident correlation; it does not silently enable external
webhooks or claim live Discord delivery. Full candidate validation follows after
the current edits are committed and the source-bound manifest is regenerated.

## Cycle 8 — terminal task outcome

Candidate c6dadfa passed the complete local gate, including 95.1% changed-line
coverage; its hosted checks were still finishing when adjacent operational review
found F114-13. A provider rejection was persisted as dead_letter but returned from
the worker function normally, causing a misleading successful Celery task. Added
a regression and explicit sanitized terminal exception after fenced persistence.
This correction requires new exact-source validation; the c6dadfa pass is retained
as historical evidence, not reused as proof of the corrected candidate. No live
email or paid preview was started. External notification routing is still a
separate open T049 concern; task failures and outbox evidence are now explicit.

## Cycle 7 — owner verification and container/deployment boundaries

Owner confirmed Resend domain Verified on 2026-10-16. Added safe provider failure
classification and optional exact-recipient private mail-trial handoff through
the existing full-preview launcher. Input is checked before provisioning and
again before transfer/activation; runtime cap is at most five requests within
one hour. Missing option preserves synthetic delivery. Persistent sending DNS
reconciliation runs before a mail-enabled launch, outside ephemeral DNS leases.

Synthetic isolated container acceptance passed first-send, fresh-container
duplicate rejection and corrupt-ledger rejection with zero external requests.
Uses existing image dependencies plus current read-only mail source, not a fresh
full-stack build. Focused preview/handoff tests passed 45 checks. Initial private
input symlink test exposed a raw OSError; normalized it to a safe RuntimeError
and the 11 handoff checks passed. DNS CLI tests cover failure redaction and write
limits. Coverage review exposed untested entrypoint branches; additional tests
brought the four new core modules to 96% line coverage (87 focused tests, 0.67s).
The initial exploratory coverage run was not release evidence; no gate threshold
or configuration was changed. Required release floors still apply unchanged.

Live application email, complete release gate, notification routing, final
container topology, exact-lease expiry binding and cleanup evidence are still
open. Do not equate unit/container passes with finished live acceptance.

## Cycle 6 — sending activation safeguards and live DNS

Implemented a private durable send-budget ledger (at most 20 reservations and
24-hour expiry), nonblocking cross-worker lock, hashed delivery identities and
fail-closed handling of duplicates, exhausted/expired/malformed/unsafe state.
Reservations precede transport and are never refunded automatically. Runtime
Resend selection now reads only a bounded private regular key file; production
settings accept Resend with explicit recipient and private-file requirements.
Both Compose profiles expose the key and persistent writable budget only to the
email worker. No automatic ledger creation or production activation was added.

F114-12 found during adjacent review: configuration validation after claiming an
outbox row could strand it. Validation now precedes claim. Budget guard errors
settle fenced rows to dead_letter, emit only allowlisted diagnostic codes and
raise a visible worker failure. Regression tests cover secret-like exception
content and no-claim on invalid configuration.

Added journaled persistent DNS reconciliation through the existing full-preview
mail-dns subcommand (available via existing Bash/PowerShell wrappers). Uses the
shared domain lock, full-inventory admission, intent-before-write journal,
readback verification and no update/delete operations. Incomplete pagination is
explicitly blocked, not silently processed; pagination support remains open.
Uncertain creates block replay; committed missing records require reconciliation.

Live authorized sending-DNS operation on 2026-10-16 created the four supplied
records in DigitalOcean. Provider readback is ready with no conflicts. Recursive
NS observation matched DigitalOcean; DKIM and rsend were visible immediately,
send and DMARC had not propagated in that initial observation. No MX added, no
droplet provisioned, and no email sent. Persistent journal lives under the private
operator state root ~/.local/state/base2-mail-dns, separate from droplet leases.
Owner has been asked to verify the domain in Resend; provider acceptance is pending.

Latest focused batch: 250 passed, 2 deselected by suite configuration (1.08s).
Includes mail transport/budget/configuration/outbox and persistent/preview DNS.
Full release gate, changed-line coverage, container integration, automated launch
handoff, webhook/delivery evidence and live user journeys remain outstanding.
Google credential placeholders remain a separate known prerequisite blocker.

## Cycle 5 — persistent email DNS

Follow-up: owner explicitly deferred receiving to a future separately scoped
self-managed inbox feature. No MX records or receiving activation in Feature114.
Live Pi metadata inspection confirmed exactly the expected Resend login item
format, populated re_ key, root-domain sender and approved test recipient; values
were not emitted or copied locally. Provider permissions/validity remain unverified.
Google client ID/secret still contain missing/placeholders; callback needs review.

The pure persistent-DNS planner initially failed collection before implementation;
after implementation its 11 cases plus adjacent DNS/email suites passed 61 tests
in 0.20 seconds. It normalizes provider names/CNAME targets, treats matching rows
as no-ops, rejects duplicates/conflicts and blocks the entire create batch on
conflict. Existing stronger DMARC is not overwritten. This completes only T044:
authoritative lookup, durable provider writes, integration, live verification and
teardown evidence remain open. No full gate or paid resource was started.

Owner reports saving base2/RESEND_API_KEY and supplies root-domain DNS for
woodkilldev.com. Secret readiness is reported, not yet independently verified.
Owner authorizes incorporating sending records into provisioning. The receiving
apex MX is held pending inbound-routing clarification: sending does not require
rerouting incoming domain mail. Existing stricter DMARC must not be weakened.
F114-11: preview DNS receipts own ephemeral A/AAAA records and teardown removes
owned records. Email records require a separate persistent lifecycle, not inclusion
in that lease. Add T043-T047 for delegation, pagination, conflict detection,
interrupted create recovery, teardown preservation and external verification.
Missing local dig/host/nslookup prevents that diagnostic route; this is not a DNS
failure. No provider write or live readiness claim has been made.

## Cycle 4 — Resend selection

Owner approved Resend HTTPS. F114-09 remains an external prerequisite: verified
sending domain and sending-only scoped key are not yet available. SMTP placeholder
repair is superseded for this trial, not mistaken for working configuration.
F114-10: provider idempotency expires after 24 hours; attempt counts alone do not
bound elapsed retry age. T041 must cover durable caps and old/uncertain sends
before activation. T039/T040 cover the isolated transport first. No provider call,
DNS change or live deployment is part of this local batch. Budget: focused mail
tests first, no full gate until integration/visual work is ready.

Transport-only batch: new tests first failed because the module was absent.
After implementation, 39 focused Resend and existing transactional-email tests
passed. Ruff formatting/lint and diff whitespace checks passed. The adapter is
intentionally NOT registered in runtime configuration: secret-file wiring,
durable send caps and retry-age controls remain T039/T041 activation blockers.
All transport failures currently require reconciliation; no implicit retry or
redirect is performed. API acceptance retains the existing `sent` meaning and
does not prove inbox delivery. No full release gate, live send or paid deployment
was run for this batch. Feature-level completion is not claimed.

## Pi recovery and credential preflight

F114-08 reachability resolved after owner restarted Pi: TCP/22 and Vaultwarden
lookup succeeded at 192.168.0.169 through configured fallback. Secret values were
not emitted or transferred to workstation storage. Narrow field-status inspection
used the existing project-vault secure-note format; note presence alone was not
counted as a usable credential.

F114-09 (owner/provider prerequisite): EMAIL_HOST, EMAIL_HOST_PASSWORD,
GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET under base2/ contain missing
or placeholder values. GOOGLE_OAUTH_REDIRECT_URI differs from the intended Base2
callback and needs explicit configuration review. Username/from/state entries
are populated but not authenticated or delivery-verified. T017 remains open for
valid configuration; dependent external checks remain blocked, not passed.
Sanitized evidence: `.artifacts/feature114-vault-preflight.json`.
No Base2 reset emails, Google-account resets, provider logins or paid resources.

## 2026-10-16 prerequisite update

F114-08 (unavailable prerequisite): metadata-only Vaultwarden lookup failed at
SSH connection, before vault access. Independent bounded TCP/22 probes confirmed
all four configured Pi addresses unavailable from WSL. Do not classify credentials
as absent, attempt login retries or provision a paid environment to investigate.
Owner has approved the exact recipient and one bounded preview; private item
references remain unverified. T017 and dependent external checks remain blocked.
No email, Google account mutation, provider operation or credential value output.
Diagnostic helper: ignored `.artifacts/feature114-pi-reachability.sh`.

## Cycle 1 — discovery

- F114-01: repeated full frontend CI for narrative-only closeout. Reproduction:
  PR #79 changed only feature documentation but ran the full browser matrix.
  Fix boundary: allowlisted narrative Markdown only, not all specs files (JSON
  coverage inventory and executable validators are test inputs). T005-T011.
- F114-02: earlier Django ModelBase TypeError remains unexplained. Original
  Feature113 gate 20261015T054038Z-558679 failed; isolated diagnostic and later
  full gates passed. No evidence yet supports a product-code patch. T012-T016.
- F114-03: first live bootstrap failed before useful diagnostics were retained.
  Feature113 now persists allowlisted stage/reason metadata. Next trial showed
  two updater health timeouts then recovery with fresh definitions; this does
  not establish the original root cause. T012-T016, preserve incident history.
- F114-04: real email/OAuth tests require approved recipient, dedicated account,
  correct credential type and callback configuration. Calendar OAuth must not
  be reused as sign-in credentials. T017-T022 remain blocked pending discovery
  and owner input, not mocked into acceptance.

## Cycle 3 — first implementation and integration prerequisite review

CI classifier initially failed its new tests because implementation was absent.
After implementation, 26 classifier/workflow tests plus 19 adjacent CI policy
tests passed (45 total, 6.67 seconds). CI policy, shell parity and diff checks
also passed. Evidence: `.artifacts/feature114-ci-adjacent-final.log`.
Selection is based on immutable base policy; only exact allowlisted narrative
Markdown, regular nonexecutable added/modified files and complete comparison
qualify. JSON coverage inventory, unknown paths, deleted/renamed files and policy
changes still require full validation. Required frontend job remains present;
security scanning is unchanged. Hosted behavior and release acceptance pending.

Original Django traceback fails inside ModelBase while unpacking attrs.items()
when rendering historical RedirectRule. One bounded current reproduction with
sysmon coverage, PYTHONHASHSEED=0 and PYTHONMALLOC=malloc passed. Evidence:
`.artifacts/feature114-migration-diagnostic.log`. Classification remains
unexplained intermittent runtime failure, not fixed. No dependency change or
ordinary-error retry was introduced to hide it.

F114-06: configured Google redirect is /api/oauth/google/callback, but the inspected
route accepts POST JSON, while no matching frontend callback consumer was found.
The separate Google credential endpoint is a different flow; real-account testing
must first reconcile this mismatch. No code_verifier/code_challenge was found in
the inspected authorization-code path. Add T036/T037; provider validation is
blocked until flow selection, callback configuration and test identity are known.

F114-07: full-preview environment renderer has no explicit SMTP/OAuth secret
handoff for these tests. Add T038, with disabled-by-default behavior and exact
private references, not blanket .env or vault copying. Await owner inputs before
selecting the real integration configuration or sending external messages.

- F114-05: current visual inventory contains capture-only and representative
  coverage; optional modules were isolated UI fixtures, not live enabled packs.
  T023-T029 must distinguish backend, UI and live layers explicitly.

## Cycle 2 — task refinement

Added explicit immutable-base policy, rename/delete, incomplete-history and
classifier-tamper cases to T006/T008; conditional artifact handling and visible
required check to T010; no automatic claim of savings to T011; prerequisite
authorization and privacy protections to T017-T022. Full release/security checks
must not be removed by narrative-only optimization. No provider operation is
allowed before T017 and local/hosted readiness. Initial planning is ready for
bounded implementation; integration prerequisites remain genuine open blockers.
