# Analysis and issue ledger

## Validation blocker — 1982f1e stability failure

F114-17 (high release blocker, unexplained intermittent runtime failure): exact
source repetitions failed on privacy-runtime repetition six, after five passes.
194 tests passed and one settings-validation test raised TypeError inside
Pydantic EnvSettingsSource while unpacking model_fields.items(): cannot unpack
non-iterable EnvSettingsSource object. This is not an ordinary settings assertion
or evidence that the prohibited database hostname was accepted. No cause or
hardware fault is established. Preserve alongside F114-02, not marked fixed.

Evidence: `.artifacts/feature-106-repetitions/failures/1982f1ef1c96e193c0ec731d0fa06adb56d1242d/4af440e5d60d7c34c71a1407d3273a65f0c48cb235583690afe24b0bc315d3e1/`.
One bounded isolated diagnostic rerun of the affected parametrized test passed
63 cases. The full repetition suite was not retried; the required full gate did
not start for this candidate. Native runtime is Python 3.12.3; the existing
network-isolated container reports Python 3.12.14 and pytest 9.1.1. Current WSL
resources were approximately 29 GB available RAM and 867 GB free disk; these
current readings do not rule out an earlier transient. Next diagnostic should
compare equivalent isolated toolchains, not retry until green or weaken gates.

No cloud resources or new email sends were used. Local code commits 96c0414 and
1982f1e are retained. Publication/merge remain blocked on valid release evidence;
Google credentials and the remaining activation/coverage tasks also remain open.

## Cycle 10 — Google authority refinement before release

Google's server verification guidance explicitly warns that email_verified alone
is not current mailbox authority for third-party email addresses without an hd
claim (https://developers.google.com/identity/gsi/web/guides/verify-google-id-token).
Refined F114-16 to also reject those automatic collisions. Only verified Gmail or
verified identities carrying a validated hosted-domain claim can auto-link; other
existing users retain password sign-in and need a separate linking challenge.
No provider identity token, refresh token or password is stored by this change.

The first 96c0414 repetition run completed, but its full gate was intentionally
interrupted early with SIGINT after discovery of this additional issue. It is not
pass evidence. All test processes terminated before editing. Two new collision
regressions failed before the correction; 30 OAuth/identity/MFA tests passed after
repair. Existing linked subject lookup is unchanged. New credential inputs,
browser CSP/Google client configuration and authorization-code callback/PKCE
remain activation blockers; no live Google sign-in is claimed.

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

## Custom-field review (T057-T058)

Pre-release checkpoint: added local empty signup/login browser regressions at
390/1440px. All four passed in 5.5s, checking actual errors, field associations,
enabled recovery controls, no auth POST and no horizontal overflow. These local
tests explicitly use unavailable-service fixtures, not live acceptance.
Private Google input module focused coverage: 14 cases, 100% lines (95% floor).
Next is a complete-gate diagnostic for this checkpoint; F114-17 remains open and
passing unrelated tests must not clear it. No provider resource has been created.

Continuation checkpoint: Google client-ID opt-in now flows through launch CLI,
private file preflight, fixed remote destination, renderer, frontend build and API
Compose environment. Client secret/redirect are absent from the API environment,
keeping the unfinished code flow unavailable. Default disabled behavior retained;
56 focused deployment tests pass. Provider and end-to-end acceptance are pending.

Diagnostic correction: catalog mounted read-only and image user-site dependencies
made visible to isolated child Python through ephemeral tmpfs site-packages.
Archive-mode link copying first failed on timestamp preservation; ordinary
recursive symbolic links corrected that harness error. Python 3.12.14 then passed
all 195 privacy-runtime cases in 1.08s. One comparison run does not resolve F114-17.

Local Volcano selection passed seven browser cases in 12.5s: login/signup at
390/1440px, signup light preference/zoom, and both original visual references.
Evidence: `.artifacts/layout-109/run-1792136353068/`. Inspected mobile signup and
desktop login captures: preserved dark shell/red tabs, readable controls, no
visible clipping. Google-enabled and new error-state captures remain pending.

2026-10-16 continuation: original F114-17 evidence preserved. A no-network,
read-only, 1-CPU/1GB comparison container produced 190 passes and five harness
failures: three missing shared probe-catalog accesses and two isolated child
interpreters unable to import user-site Pydantic. This is not equivalent release
evidence or a fix for F114-17. No test assertion was weakened or ignored.
Google CSP build adapter now preserves the exact disabled policy and selectively
adds fixed documented GIS endpoints for valid client IDs. Three focused tests
pass. Image contract initially rejected the intentional build-stage change;
updated contract requires both the renderer and its copied output and rejects
missing steps. No full image build/browser acceptance claimed yet.

Live expansion review: existing live inventory covers route shells and owner
login/logout but does not enter empty signup/login error states. Add T059 as
required cases, not optional screenshots. T060 must keep provider readiness
distinct from a real human-consented sign-in. No mock Google token may qualify
as live success. New paid bounds requested; no cloud activity before readiness.
F114-17 still blocks release; tests added here do not erase that failure.

Implementation checkpoint: required live inventory now includes mobile/desktop
empty signup/login validation, both preference modes, field-error associations,
menu/layout checks, main-region axe checks and screenshots with no submitted data.
The acceptance contract rejects omitted cases. ESLint has zero errors and three
existing declaration warnings; TypeScript passes. Browser execution and visual
inspection are still pending, so T059 remains open. Captures alone do not prove
pixel equivalence; approved home/menu references remain separate required checks.
No preview has been provisioned and no Google sign-in success is claimed.

F114-18: the preflight assumed managed Notes, so a saved custom-field credential
was reported missing. The first save overwrote `key` metadata; owner was asked to
restore `key` and move the value to `value`, and reports this is done.
Analysis -> additional tasks: reject duplicate `value` and `key` fields, boolean/
linked field types, conflicting Notes, unsupported item names and malformed input;
keep exception text fixed and metadata-only reports. Reanalysis: bounded parser
and preflight change has no known planning gap; actual provider acceptance and
preview wiring remain separate unfinished tasks. Existing F114-17 remains open.

Outcome: the private preflight using the new parser confirmed the saved client ID
is readable from `value` with restored key metadata, without printing its value.
Client secret remains missing; it is not needed for the existing GIS ID-token
popup. Provider validity and deployment wiring are not claimed. Added a required
release-gate entry for the synthetic parser tests. No full gate or cloud run was
performed. System Python lacked coverage; existing `.venv-api` supplies coverage
without installing packages. Focused coverage evidence: `.artifacts/f114-vault.coverage`.
