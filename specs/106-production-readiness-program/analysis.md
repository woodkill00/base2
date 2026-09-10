# Analysis record

## Scope and method

The specification, plan, tasks, and traceability table were reviewed as one
closed program. Each cycle compared user outcomes, requirements, task coverage,
dependency ordering, architecture, security, privacy, accessibility, operations,
cost, rollback, evidence honesty, and authority boundaries. Findings were added
to the artifacts rather than silently accepted.

The original cycles were pre-implementation analysis. Implementation evidence
is now recorded below. The analysis can establish zero unresolved local planning
gaps in the declared scope; it cannot prove that finite testing eliminates
unknown defects or substitute for pending independent, hosted, or provider proof.

## Cycle 1 — Scope completeness

The initial roadmap covered releases, monitoring, data, edge, identity, product
features, and quality, but treated several cross-cutting needs only as prose.
The artifacts were corrected to add explicit requirements and tasks for:

- telemetry privacy, cardinality, retention, and deletion;
- honest unavailable and degraded dependency states;
- production credential authority and break-glass recovery;
- background job leases, idempotency, dead letters, schedules, and DST;
- email delivery, bounce, suppression, notification preferences, and quiet time;
- disabled-capability absence rather than navigation-only disablement;
- exact production activation as a separately approved post-feature operation.

Result: every declared product and operational domain has an owned workstream,
negative boundary, evidence task, and traceability entry.

## Cycle 2 — Dependency and migration analysis

The workstreams were checked for circular or unsafe dependencies. Product-level
automation originally could have depended on jobs, policy, storage, or telemetry
before those contracts were stable. The order was repaired so that:

1. closed schemas and invariants precede implementation;
2. operations and immutable release evidence precede production activation;
3. database isolation and recovery precede tenant/product expansion;
4. edge and secret contracts precede integrations and commerce;
5. durable jobs and notifications precede editorial, forms, and webhooks;
6. tenant lifecycle and policy precede cross-module search and builders;
7. complete integrated assurance follows all release trains.

Expand/migrate/contract sequencing, mixed-version proof, delayed destructive
contraction, data-preserving capability disable, and previous-compatible-release
rollback are now explicit. No task requires reversing an unsafe migration.

## Cycle 3 — Security, privacy, and authority analysis

The plan was attacked for tenant escape, confused-deputy behavior, credential
leakage, stale approval, provider overreach, cache disclosure, monitoring data
leakage, webhook replay, hostile input, and administrative exposure. Corrections
include:

- forced PostgreSQL tenant isolation plus two-tenant proof at every layer;
- separate bounded global discovery and tenant-bound mutation transactions;
- JIT secret references, rotation, revocation, expiry, and no-leak testing;
- exact typed approval scopes for every protected operation;
- staging-only routine certificate work and explicit production prohibition;
- private-by-default admin, pgAdmin, Traefik, diagnostics, metrics, and schemas;
- cache and CDN isolation for authenticated and tenant-sensitive data;
- fixed typed recovery actions instead of arbitrary commands;
- constrained components/modules rather than executable page/plugin content;
- fake-provider-first commerce and synthetic-data-only canary testing.

No repository task grants publication, merge, deployment, spending, DNS,
credential, destructive-data, production-certificate, or provider authority.

## Cycle 4 — Reliability, testability, and observable failure analysis

Every stateful domain was checked for retry, replay, concurrency, crash,
interruption, stale state, provider outage, clock shift, partial result, and
silent failure. The task graph now requires:

- deployment checkpoints, leases, replay-safe resume, and traffic halt;
- monitor and alert self-observation without an alert storm;
- durable job attempts, leases, fairness, backoff, dead letters, and safe replay;
- schedule lateness, missed-run, catch-up, timezone, overlap, and DST semantics;
- backup corruption, wrong-key, stale, cross-tenant, and live-target rejection;
- domain takeover, DNS delay, certificate, cache, proxy, and abuse fault tests;
- exact-source visual and interaction evidence, not screenshots without identity;
- production-like local acceptance before separately approved provider work;
- explicit failure states rather than incomplete operations reported as success.

Every required behavior is observable through a test, invariant, evidence
receipt, reviewed visual, or a combination appropriate to the boundary.

## Cycle 5 — Cost, usability, closeout, and residual-risk analysis

The final pass checked whether a technically correct platform could still be
unusable, too expensive, impossible to operate, or falsely declared complete.
Corrections include:

- representative user roles, datasets, capacity profiles, and user journeys;
- keyboard, screen-reader, zoom, motion, contrast, RTL, responsive, browser,
  interaction, and reviewed visual matrices;
- cost forecasts, finite resource ceilings, automatic ephemeral expiry, exact
  teardown, and empty provider inventory evidence;
- fresh-machine and recovered-WSL golden-path tests with Bash/PowerShell parity;
- data inventories, user rights, consent, vendor, regional, and accessibility
  controls without unsupported certification claims;
- two exact-head complete gates, repeated critical tests, and independent code,
  security, UX/accessibility, data, and operations review;
- mandatory re-entry to the task-analysis cycle for any canary finding;
- a rule that elapsed time alone cannot close evidence work.

Result: the current specification set has zero unresolved planning gaps within
its declared scope. Implementation may expose new facts; each becomes a new
ordered task and another analysis cycle before completion.

## Requirement and task accounting

## Cycle 6 — Explicit infrastructure and compatibility contracts

A final assumption audit found six controls that were partially represented by
tests or prose but not independently enforceable. The specification and task
graph were corrected to require:

- encryption in transit and at rest with explicit key lifecycle and recovery;
- service-network segmentation and bounded egress with SSRF, metadata, DNS
  rebinding, lateral-movement, and exfiltration proof;
- locale, timezone, translation, pluralization, direction, and fallback behavior;
- public API/event versioning, compatibility, deprecation, and consumer evidence;
- typed, expiring, observable, reversible feature flags with residue checks;
- machine-verified protected branches, required checks, owners, workflow
  permissions, dependency updates, and release signing.

Each is now a numbered requirement, mapped to implementation tasks and explicit
adversarial or user-facing evidence. This closes the last implicit-contract gap
found by the pre-implementation analysis.

## Requirement and task accounting

- Functional requirements: 78, sequentially identified FR-001 through FR-078.
- Ordered tasks: 160, sequentially identified B001 through B160.
- Current independently sustained completion frontier after review: B023.
- Current pending tasks: 137 (B024-B160). Earlier local helper-level evidence did
  not sustain the integration claims for those tasks and has been withdrawn.
- Publication, merge, canary, teardown, and production activation remain
  distinct exact-scope decisions and cannot be inherited from this planning work.

## Implementation cycle 1 — Executable production baseline

The first implementation train added a closed machine-readable inventory of
environments, services, route surfaces, modules, generated profiles, workflows,
data stores, trust boundaries, protected actions, resource defaults, release
fields, and capability-absence surfaces. Repository module, profile, or workflow
drift now fails the readiness contract instead of silently aging the inventory.

The first negative suite exposed generic diagnostics for missing protected
actions and capability surfaces. Validation was corrected to report the exact
closed-contract violation. Sixteen readiness tests plus the complete-gate graph
tests pass. The Feature 106 planning and production-readiness validators are now
required nodes in the repository complete gate. Current-state documentation was
reconciled with the exact 2026-09-08 baseline; no credential, provider, release,
or deployment operation was performed.

## Implementation cycle 2 — Native operations and real isolation

The native operations train added tenant-owned service, health, synthetic,
objective, incident, timeline, and alert-delivery records; tenant-bound API and
repository operations; private role-gated UI; and closed probe, incident,
objective, alert, collection, and retention contracts. Eleven deterministic
browser profiles now enforce accessibility, keyboard focus, responsive reflow,
contrast, theme, direction, motion, request, console, and overflow behavior.
Every capture and relevant source file is SHA-256 bound into the reviewed visual
manifest.

The first integrated gate found two real issues: newly added surfaces were not
yet locked and changed-line coverage was 86.72%, below the required 90% floor.
Repository, client, UI-failure, and hostile-contract tests closed the coverage
gap, and the surface lock was regenerated. Disposable PostgreSQL acceptance then
found that forced RLS policies existed but the new tables lacked least-privilege
role grants. Migration 0019 now grants tenant-scoped CRUD only to the application
role and read-only discovery to the worker, with symmetric revocation. The real
container proof verifies all seven tables are force-RLS, all 28 policies exist,
role bypass is disabled, cross-tenant reads and inserts fail, and composite
cross-tenant links fail. A fault matrix also proves visible monitor, dependency,
clock, stale, flapping, queue, alert-provider, restart, deduplication, and expiry
behavior without storms.

The second complete gate ran 98 checks and every runnable product, browser,
database, security, edge, deployment, recovery, and supply-chain check passed.
Its sole failure was a stale hash caused when the pre-commit formatter rewrote
the complete-gate configuration after the surface lock was generated; the lock
was regenerated after formatting and now validates at the exact current head.
No external provider, credential, publication, merge, DNS, certificate, or live
deployment action occurred.

## Implementation cycle 3 — Release, data, edge, and workflow closure

The release train added immutable exact-source manifests, build-once artifact
promotion, checkpoint journals, replay-safe leases, health-gated canary states,
exact compatible rollback, independent HMAC approval keys, and typed expiring
feature flags. Production remains explicitly rejected by the local executor.

Data readiness now validates TLS verify-full transport, encrypted storage key
references, fixed pool and timeout budgets, least-privilege roles, expand /
migrate / contract compatibility metadata, destructive approval boundaries,
honest PITR fallback, isolated restore targets, six-surface reconciliation,
retention, and legal holds. Edge readiness adds replay-safe domain claims,
canonical redirects, staging-only certificates, cache isolation, private
administration, trusted-proxy limits, default-deny service networks and egress,
and SSRF/metadata/DNS-rebinding defenses. Credential, job, schedule, email, and
notification contracts cover metadata-only inventory, rotation, bounded
break-glass, leases, dead letters, DST, quiet time, and mandatory security
delivery.

## Implementation cycle 4 — Tenant and universal platform closure

Tenant lifecycle and quota contracts cover provisioning through separately
approved deletion, data-preserving suspension/archive, transfer/export,
replay-safe reservations, reconciliation, forecasts, denial reasons, and
tenant-private remediation. Identity recovery cannot remove existing factors,
session revocation requires token rotation, policy resolution defaults to deny
across all nine enforcement surfaces, and settings changes are scope-, revision-,
and recent-auth-aware.

The universal layer adds authorization-filtered tenant search, bounded cursors,
editorial review/conflict/rollback, HMAC-bound expiring previews with private
no-store caching, reference-aware media deletion, locale/SEO/privacy/navigation
contracts, and exact disabled-capability absence. The extension layer adds a
closed non-executable page schema, bounded nesting, versioned theme migration,
all thirteen archetypes, scoped expiring integration grants, fresh signed
replay-safe webhooks, versioned API compatibility, and fake-provider-only
commerce transitions.

One focused test exposed a real ordering bug: unauthorized forced deletion of
referenced media returned a blocked status before evaluating the missing
approval. The approval check now runs first and the regression is covered.

Manual final-diff review found two additional hostile-input gaps. Builder nodes
could use dangerous property names such as `dangerouslySetInnerHTML`, `style`,
event handlers, or HTML data URLs without matching the original value-only
scanner. Webhook duplicate detection also ran before signature verification,
allowing a forged replay identifier to receive a duplicate classification.
Builder keys and URL schemes are now closed, and every webhook—including an
exact replay—must pass freshness, key, identity, and signature verification
before deduplication. Focused negative tests cover both findings.

## Implementation cycle 5 — Integrated assurance and repeatability

Performance assurance defines twelve finite budgets, small/medium/large data
models, five actor profiles, hysteresis-based scaling, safe degradation,
four-hour/USD 5 ephemeral ceilings, exact ownership, staging certificates,
eleven fault classes, nine governance inventories, measured recovery evidence,
and Bash/PowerShell golden-path parity. Existing supply-chain, dependency,
workflow, environment, generated-child, provider-admission, and owned-teardown
gates remain required.

The first expanded complete gate failed closed because data and edge contract
nodes invoked system Python, where project pytest is intentionally absent. Both
nodes now use the managed API runtime. The entire repaired dependency chain
passed 38 focused tests. Two subsequent complete gates passed all 106 required
checks with no skips at the identical clean implementation commit
`0073399c9c637ab91d79fe704b42643b677bda4b`:

- `.artifacts/complete-gate/20260908T001951Z/result.json`
- `.artifacts/complete-gate/20260908T003120Z/result.json`

The complete matrix includes API/Django/PostgreSQL, frontend, Playwright visual,
accessibility, identity, tenant, data-rights, content, search/SEO, privacy/i18n,
transactional email, media, module, deployment, recovery, performance,
provider-admission, secret, supply-chain, and generated-child checks. A broad
advisory Ruff scan found 182 pre-existing style findings in older script and
test files outside the required API lint surface. They do not invalidate the
required gates, but are retained as non-blocking cleanup debt rather than being
silently reformatted in this feature.

No new planning task was required after the local integration cycle. B146-B160
remain honestly pending: fresh independent review, final exact-diff review,
separately authorized publication and hosted checks, separately authorized
provider canary and teardown, canary-driven re-analysis, activation runbook and
closeout. No provider, credential, publication, DNS, certificate, deployment,
or destructive action was performed.

## Honest residual boundary

Provider outages, upstream defects, new vulnerabilities, browser changes,
operator mistakes, credential compromise, unmodeled workload, and unknown
defects remain possible. The design reduces these risks through least authority,
isolation, monitoring, rollback, recovery drills, evidence, and bounded failure;
it does not call them impossible. Actual production use also requires concrete
service objectives, capacity measurements, legal review where applicable, and
separately approved environment-specific activation.

## Implementation repair cycle 7 — connected operations views

B024 and B025 were rebuilt against the tenant-scoped PostgreSQL repository and
FastAPI boundary. The private UI now renders the current site/fleet summary,
release identities, latest service evidence, objectives, synthetic runs,
incidents, ownership, timestamps, and an on-demand incident timeline. Incident
mutation is absent for read-only users and remains permission plus explicit
recent-auth gated server-side. Repository mutations commit; incident retention
uses resolution time.

Focused API/repository tests passed 11 checks and frontend service/component
tests passed 9 checks. The source-bound browser run passed 26 checks across
responsive/touch, large text, 400%-equivalent reflow, light, high contrast, RTL,
reduced motion, Chromium, Firefox, and WebKit projects, including safe loading,
empty, failure, timeline, and acknowledgement interactions. B026 remains pending
because deterministic fault helpers are not a substitute for a connected runtime
collector, durable alert dispatcher, and restart/outage drill.

## Independent review cycle 6 — completion reset and repair plan

Fresh code, security, UX/accessibility, data, and operations reviews rejected the
earlier B024-B145 completion claims. The common finding was that deterministic
helper contracts and focused tests had been mistaken for connected runtime,
persistence, multi-browser, provider-adapter, and recovery evidence. Task status
was therefore reset to the last contiguous independently sustained task, B023.

The first repair set now removes unsafe default release health, binds release
replay to the complete signed candidate and environment, authenticates ephemeral
plans and deletion approvals, reports partial teardown as pending, rejects active
builder URLs, commits Operations mutations, requires the principal's explicit
recent-auth state, authenticates alert and receipt integrity with separate HMAC
keys, bounds preview lifetime, enforces probe adapter deadlines, and retains
incidents from resolution time rather than initial creation time. At that review
point B024 onward was reset pending until each named runtime and evidence
boundary could be met; the following repair cycle records that closure.

## Implementation repair cycle 8 — connected delivery and truthful evidence

Independent review findings were converted into runtime repairs rather than
accepted as residual implementation debt. Operations incidents are now scoped by
tenant and environment and serialized on first creation. Alert delivery uses an
atomic expiring claim token, stable Discord nonce, bounded retry, and separately
scoped payload and receipt keys. Monitoring and scheduler state comes from fresh
runtime heartbeats; DNS, certificate, backup, and restore state accepts only
fresh source/artifact-bound HMAC receipts. Missing evidence remains degraded.

Durable schedules now claim atomically and materialize fixed allowlisted jobs.
Jobs carry generation and lease tokens, reject stale settlement, dead-letter
exhausted work, and expose queue/schedule/alert state in the private Operations
Center. Production alert delivery is disabled by default and, when enabled,
requires three distinct secret files and a strict Discord HTTPS webhook adapter.
No credential value enters repository state or evidence.

Release approvals and health receipts now bind exact source commit, artifact
digest, environment, operation identity, freshness, and expiry. A lost response
reconciles the same operation identity instead of repeating mutation. Explicit
database URLs are normalized to the configured TLS policy. Object reads and
deletes require the owning tenant, and custom object endpoints reject private,
metadata, loopback, and DNS-rebinding results. Domain verification requires a
fresh signed independently scoped observation. Destructive tenant transitions
bind revision, expiry, and a consumed replay nonce.

The migration adds model-level and database-level state invariants and narrows
worker grants. Real disposable PostgreSQL forward/rollback, forced-RLS, role,
mixed-version, encrypted backup, target-absence, isolated restore, and
six-surface reconciliation checks pass. Restore paths derive ownership,
permissions, and emptiness from the actual filesystem or PostgreSQL catalog;
caller assertions are not accepted. The database setting is named honestly as
an idle-transaction timeout because PostgreSQL 16 does not provide a total
multi-statement transaction wall-clock setting.

The private Operations Center no longer renders unavailable data as zero, adds
explicit empty and recent-auth recovery states, announces and focuses incident
timelines, returns trigger focus, surfaces runtime delivery state, and provides
English, German, Arabic RTL, and deterministic fallback behavior. The exact
visual matrix passes 26 browser checks and its integrity manifest covers 15
responsive, zoom, contrast, motion, RTL, empty, failure, Chromium, Firefox, and
WebKit captures. One complete 106-node integration gate passed after the visual
manifest was regenerated; final identical-head repetition and fresh independent
review remain required before publication.

## Implementation repair cycle 9 — exact-head closure and honest review boundary

The full API suite, all 239 frontend component tests, the 90-test Django suite,
changed-surface lint, API type checking, compose rendering, real PostgreSQL
migration/RLS exercises, encrypted isolated restore, and the 26-case Operations
browser matrix passed. The broad Django run exposed one backend-specific migration
statement (`NOW()`) that failed under SQLite; it was replaced by a historical-model
`RunPython` repair and the entire suite then passed. The first complete-gate attempt
also correctly rejected obsolete homepage baselines after the supported locale
count changed from one to three. Expected, actual, and diff images were inspected,
the three-locale baselines were approved, and the regenerated visual harness passed.
The next gate caught an old route-set assertion that omitted the newly governed
Operations route; the contract now requires that route and its focused suite passes.

Two subsequent clean runs passed every one of the 106 required checks at identical
source `faefe88e2631ca41db8c90b3e3e6657362f441a9` with no skip or failure:

- `.artifacts/complete-gate/20260908T103450Z/result.json`
- `.artifacts/complete-gate/20260908T104503Z/result.json`

This completes B145 and demonstrates that the repair candidate is repeatable under
the repository's local production-readiness policy. It does not convert automation
into independent human review. B146 therefore remains pending until fresh code,
security, UX/accessibility, data, and operations reviewers evaluate the repaired
exact source and every critical, high, and medium finding is closed. Publication,
hosted checks, merge, provider canary, provider teardown, and actual production
activation likewise retain their explicit approval and evidence boundaries.

## Independent review cycle 10 — exact-head rejection and corrective expansion

Fresh independent data, UX/accessibility, and combined code/security/operations
reviews examined published draft PR #55 at exact clean head
`fba2fd3ee386a8d5104c3e9b76bea4e237e301c4`. Hosted checks were green, but the
reviews correctly rejected production readiness. They found one critical, ten
distinct high, and several medium findings after overlapping reports were
deduplicated. The draft remains unmerged and no provider, DNS, certificate,
credential, deployment, or destructive action has been performed.

The release-blocking gaps include a Celery database role regression and broader
credential bypass, absent production email delivery and durable replay, monitoring
fan-out that can outgrow its freshness window, unsafe scheduler idempotency and
capacity behavior, incomplete timezone/DST and long-lease semantics, an upgrade
constraint that does not normalize every historically accepted row, helper-only
tenant lifecycle and production backup paths, non-causal release health evidence,
and disconnected automatic ephemeral expiry. The object-storage validation also
has a DNS-resolution race between preflight and connection.

The UX review found that the accepted RTL capture contradicted the current Arabic
source assertion and still contained substantial untranslated shell, settings,
state, and severity text. It also found missing panel-local freshness, an
unconfirmed dead-letter cancellation action, and evidence that did not yet prove
the stated keyboard, touch, motion, degraded, recent-auth, read-only, browser, and
assistive-technology behaviors.

Tasks B161-B176 convert every finding into explicit implementation, regression,
evidence, exact-head gate, and repeated independent-review work. The ancestor-bound
B145 evidence is retained as historical evidence only; after any repair changes the
head, B175 requires two new complete gates at the new exact clean commit. No prior
publication approval or hosted result may be reused for a changed head.

## Independent review cycle 11 — repaired exact-head rejection

Candidate `a10393f5555075d0ae6b52a2c96b1806d91833b9` passed all 107 complete-gate
checks twice and the critical state-machine suite ten consecutive times. Fresh
independent code/security, data/operations, and UX/accessibility review still
rejected a production-readiness claim. The reviews found zero critical findings,
but exposed six distinct high findings plus overlapping high and medium findings
that automation had not detected.

Root causes include lifecycle metadata disconnected from serving and deletion,
historical cross-tenant worker grants and excessive secret co-location, split and
undeployable S3 paths, production-disabled authentication mail, monitoring capacity
that contradicts freshness SLAs, backup receipt/schema/snapshot inconsistencies,
impossible database-plus-object recovery acceptance, incomplete lifecycle and mail
fencing, caller-time schedule claims, and misleading database saturation evidence.
UX review also found mixed-language accessible labels, incomplete Settings
localization, duplicate page-level headings, missing German execution, and visual
assertions not bound tightly enough to runner and scenario evidence.

Tasks B177-B194 deduplicate every critical/high/medium finding and include the two
low findings affecting least privilege and bounded backup inventory. The two green
gates remain historical evidence only. A changed candidate must again pass two
complete gates and fresh independent review with zero critical, high, or medium
findings before publication can be requested.

## Analysis cycle 12 — review repairs and test-discovered hardening

The cycle-11 findings were implemented without extending provider, publication,
merge, deployment, DNS, certificate, credential, or destructive authority. The
repair connects lifecycle admission to production serving and background work,
uses an accepted two-phase member ownership transfer, revokes historical worker
grants, splits runtime/content/email worker duties and secret mounts, wires the
pinned storage factory through synchronous and asynchronous paths, requires a
production email transport, fences mail claims and job leases, bounds monitoring
capacity, stages immutable backup bytes, validates the live migration ledger,
quarantines invalid owned backup evidence, and aligns recovery receipts.

The UI repair localizes the declared English, German, and Arabic shell, Settings,
and Operations surfaces; preserves one page-level heading; and binds 35 visual
captures to an actual-run receipt covering 42 browser scenarios. Expanded tests
caught two additional issues before publication: a legacy accessible-name
compatibility regression and nondeterministic cancellation/screenshot assertions.
The accessible default was restored while localized callers remain explicit; the
confirmation action now verifies visible enabled state and uses deterministic
activation, and state screenshots use the same bounded 2% anti-alias tolerance as
the primary captures. The RTL flow then passed three consecutive repetitions and
the entire matrix passed 42/42. Full API, Django, frontend unit, lint, type, Compose,
surface-drift, and exact-source visual checks are green. Tasks remain unchecked in
the ordered ledger until the earlier review/publication/canary checkpoints permit
contiguous completion; implementation evidence does not silently satisfy those
separate approvals.

## Analysis cycle 13 — failed-candidate gate and worker authority correction

The first cycle-12 candidate was rejected by its own complete gate before any
publication update. The gate found three concrete defects: the visual-evidence
contract retained an obsolete capture count, notification success exposed a
button label instead of completed-state copy, and the PostgreSQL lifecycle
backfill referenced a nonexistent membership primary key. Focused regressions now
cover the 35-capture manifest, localized notification completion, and the real
membership schema. The PostgreSQL run then exposed a deeper issue: narrowing the
historical shared worker role removed content/media discovery required by the
content queue.

The authority model is therefore four distinct database identities rather than a
shared compromise: tenant-bound request/API access, narrowly global content/media
discovery with tenant-fenced mutation, operations/runtime tables plus quota and
durable-job access, and select/update-only email outbox delivery. Bootstrap,
migrations, Compose, setup, E2E fixtures, and disposable PostgreSQL acceptance all
carry independent credentials. The acceptance now proves forward migration,
rollback, reapply, role denial, RLS isolation, media discovery, quota/job behavior,
and email read/update with content, operations, and insert denial. Tasks B195-B199
capture these test-discovered obligations. The rejected candidate and its gate are
historical evidence only; a new clean head still requires two complete gates and
fresh independent review.

## Analysis cycle 14 — gate-one catalog and changed-line coverage rejection

Complete gate 1 rejected candidate `d0bd6665e3d1fe1e78090774da18f561c1cb0c0a`.
The migration catalog described the non-data-destructive worker permission change
as a destructive contract phase while explicitly declaring it non-destructive,
and its test still expected schema 27 instead of the live schema 29. The catalog
now classifies the permission transition as a migrate phase and the contract
requires schema 29. The changed-line gate also measured 89.28% against the fixed
90% floor. Focused email tests now exercise private secret-file validation, SMTP
adapter construction and invalid configuration, and successful and empty fenced
outbox claims. Tasks B200-B201 preserve both gate-discovered obligations. The
failed candidate remains rejected; a new exact head must restart both complete
gates and independent review.

## Analysis cycle 15 — independent UX, data, and operations rejection

Candidate `6b154f74c31e63b73b2775987140440fd8ac80b8` passed 107 complete-gate
checks twice and ten repetitions of its critical state-machine suites. Fresh
independent UX/accessibility, data, and operations review nevertheless rejected
publication readiness with zero critical findings but multiple high and medium
gaps. The green gates remain historical evidence only; they cannot authorize a
changed source head.

The deduplicated findings were incomplete account/settings localization and
immediate locale application, missing Operations enum translations, Compose
environment/TLS bypasses, incomplete worker startup and observation, excessive
runtime SMTP configuration, missing content-worker grants, historical
cross-tenant mutation policies, disconnected lifecycle admission and ownership,
unsupported terminal deletion claims, overwritable and race-prone S3 objects,
S3 backup absence, shared worker/queue observations, interruption-sensitive
email contraction, a mutable cross-surface backup window, unbounded quarantine,
and readiness evidence that did not require the newest API migration.

Tasks B202-B213 convert every finding into implementation and exact regression
evidence. The repair uses no provider, DNS, certificate, credential,
publication, merge, deployment, or destructive authority. Production S3 is
explicitly unavailable until versioned S3 backup/restore exists; deletion remains
in the recoverable `deleting` state until a future reconciler can prove every
declared surface terminal. Those fail-closed boundaries are intentional and are
not presented as completed capabilities. A new exact clean commit must pass two
complete gates and fresh independent review with zero critical, high, or medium
findings before publication approval may be requested.

The first broad API run in cycle 15 also found one brittle test that required a
single-line `SELECT` spelling and failed after the formatter correctly wrapped
the readiness query. B214 replaces that textual accident with whitespace-
normalized SQL-shape validation and explicit assertions for the exact Django 30
and API 11 ledgers. The product behavior was correct; the failed suite remains
recorded and the broad API run must pass again.

## Analysis cycle 16 — exact-head complete-gate rejection

Complete gate 1 rejected candidate `794176c3e80f73d30613af844790535614032e45`
before publication. The gate exposed four independently actionable gaps: the
pinned S3 client did not yet satisfy the bucket-readiness protocol or carry
conditional-write and exact-version semantics through its real transport; the
surface-drift lock remained bound to ancestor configuration and route sources;
the Operations visual manifest remained bound to ancestor source hashes; and the
account browser journey still queried the legacy hyphenated notification label
after the accessible copy became human-readable. Tasks B215-B218 bind each
repair to focused proof. The rejected run is historical evidence only. Visual
evidence must come from a newly executed browser matrix, not a source-hash-only
manifest rewrite, and the repaired clean head must restart both complete gates
from zero.

The replacement candidate `3b0e5a5dacf76e3143801624a9ea0e15489b6775`
cleared every complete-gate check except the immutable changed-line coverage
policy: 4,149 of 4,644 executable changed lines were covered (89.34%) against a
fixed 90% floor. B219 adds direct behavioral coverage for bounded internal HTTP
probes, timing caps, worker and queue evidence, closed Celery route validation,
production lifecycle admission, Redis dispatch reservation, capacity failure,
and broker-enqueue cleanup. The floor is not reduced, rounded, or bypassed; both
complete gates restart again on the next clean exact head.

## Analysis cycle 17 — fresh independent review rejection

Candidate `d9ba9511c7d99252529a24b794c2ab84335870d3` passed all 107 complete-gate
checks twice, including a 90.74% changed-line result, and 67 critical isolation
and state-machine tests ten consecutive times. Fresh UX, data, and operations
review nevertheless rejected publication. Across the three lanes the maximum
counts were zero critical, five deduplicated high, eleven medium, and two low
findings. The automated evidence is therefore historical and insufficient.

The highest-risk findings are a post-contract email insert missing its mandatory
delivery key, crash-strandable data-rights work, a shared content/data-rights role
with unrestricted global identity mutation, and backup/restore evidence that does
not reconcile database references to captured object bytes. Operational findings
cover global session collateral, mixed-time exports, incomplete migration reverse,
concurrent migration races, contradictory production database TLS, helper-only
ephemeral expiry, fail-open deployment health, and non-atomic fan-out capacity.
UX findings cover a silent passkey control, inert and incorrectly controlled
sidebars, stale-language feedback, and an untranslated running state. Two low
findings require honest visual skip receipts and consistent production API-doc
defaults. Tasks B220-B239 bind every correction and require new real PostgreSQL,
fault, visual, and complete-gate evidence before review can be repeated.

## Analysis cycle 18 — integrated acceptance corrections

The cycle-17 repairs passed their lane-specific suites, but integrated acceptance
found two concrete compatibility gaps before a candidate commit. The disposable
PostgreSQL runner had not generated or passed credentials for the newly isolated
data-rights role, so bootstrap correctly failed closed. The authenticated shell
also had older callers and test doubles that still supplied string sidebar items;
requiring only typed objects would have turned those controls inert and changed
their accessible name. Tasks B240-B242 preserve these findings and their proof.

The acceptance runner now carries the dedicated role through bootstrap, migration,
workspace, and media checks, and the complete disposable PostgreSQL forward,
reverse, concurrency, and isolation sequence passes. AppShell normalizes legacy
strings into real links while typed callers retain exact routes, and the complete
68-file/258-test frontend suite passes. The Operations browser matrix was then
executed again from the integrated sources across Chromium layouts, German,
Arabic/RTL, reduced motion, Firefox, and WebKit; 22 asserted scenarios passed and
20 unsupported combinations were recorded explicitly as skips. Its 35 captures,
runner receipt, visual manifest, and the 109-file surface-drift inventory were
regenerated and validated. B239 remains open until one clean exact head passes two
complete gates, ten critical-suite repetitions, and fresh independent review with
zero critical, high, or medium findings.

## Analysis cycle 19 — exact-candidate gate rejection

Complete gate 1 rejected candidate `9f9701e59a7227a33b0eab6eb2e145e0ada9a045`
with two deterministic obligations. The authentication rate-limit test began only
milliseconds before a real minute boundary, so its fifth request entered a new
production fixed window and the sixth request correctly remained below the new
bucket limit. B243 freezes test time inside one window without changing production
limiting behavior. The Operations manifest was generated before pre-commit
normalized its source files, leaving the committed source hashes stale even though
the browser run itself passed. B244 requires capture and evidence generation after
normalization and before the replacement candidate is committed. The failed gate
is historical evidence only; both complete gates restart from zero on the next
exact head.

## Analysis cycle 20 — independent review rejects the twice-green head

Candidate `3d173dc0ba0271c0dd448da79be37642df012bea` passed all 107
complete-gate checks twice and 67 critical isolation/state-machine tests ten
times, but fresh exact-head review still rejected publication. UX returned
C0/H0/M2/L1, data returned C0/H2/M2/L0, and operations returned C0/H5/M3/L1.
The automated evidence remains valuable historical proof of implemented
contracts, but cannot establish readiness for contracts it did not contain.

The release-blocking gaps are direct self-selectable data-rights database access,
tenant-local privacy requests causing global identity destruction, an ABA window
between relational and object backup snapshots, incomplete subject-data coverage,
an escapable modal drawer, receipts synthesized from test names rather than actual
attachments, missing shell/style invalidation sources, absent current-route
orientation, omitted canary secret generation, Django database TLS bypass,
deployment success without a resolved target or exact checked-out commit,
helper-only generic expiry, suppressed rollback failures, a schema/docs exposure
bypass, and a broker-only Celery Beat health claim. The external-database topology
also retains an unnecessary bundled PostgreSQL dependency. Tasks B245-B262 bind
each finding to implementation, hostile proof, new exact-head gates, and another
independent review. No provider, DNS, certificate, credential, publication,
merge, deployment, or destructive action was performed by this review cycle.

## Analysis cycle 21 — integrated security and evidence corrections

Cycle-20 implementation exposed additional defects only when its security and
runtime contracts were exercised together. The disposable real-PostgreSQL run
found that claim renewal, terminal settlement, claim propagation, and
cross-role RLS reads needed fixed non-disclosing database guards. Backup review
showed that pre/post fences alone do not bind pg_dump to the object-reference
ledger, so production now requires one exported repeatable-read snapshot for
both. Subject coverage was expanded and versioned rather than inferred from a
partial table list.

The generic-expiry helper was promoted to a durable bounded registry and
hardened scheduled scanner with one fixed exact-owned adapter. Production
Compose and rollback assertions were tightened around the external database
topology and exact commit. Finally, the cross-browser run rejected a Firefox
network-idle wait even though the user-visible page was ready; B268 replaces
that transport heuristic with explicit UI readiness before regenerating
current-run evidence. Tasks B263-B269 retain these integrated discoveries as
ordered proof obligations. No provider, DNS, certificate, credential,
publication, merge, deployment, or destructive action was performed.

## Analysis cycle 22 — broad diagnostic gate corrections

The intentionally non-authoritative dirty-tree diagnostic gate rejected two
local checks before exact-head evidence began. Ruff identified one nested claim
context that violated the repository's structural rule. The coverage policy
also showed that the new drawer behavior had correct focused assertions but had
not exercised every empty and keyboard branch required by the unchanged
critical-glass floor. B270-B271 close those gaps directly. API lint now passes,
the complete 261-test frontend suite passes, critical glass is 100% for lines,
statements, functions, and branches, and changed-line coverage remains above
the fixed 90% floor. The diagnostic gate remains historical only because its
source label preceded the clean repaired commit.

## Analysis cycle 23 — deterministic sticky-header capture

The post-coverage visual rerun rejected one compact reauthentication capture.
Expected, actual, and diff inspection showed identical page data with the sticky
application header rendered at a different click-induced scroll offset. This was
not accepted as a new baseline or dismissed as noise. B272 requires the capture
helper to normalize scroll position before every comparison, regenerate only
from that deterministic contract, and pass an immediate no-update rerun. This
keeps the screenshot evidence sensitive to real layout drift without allowing
the test runner's prior interaction position to create false failures.

## Analysis cycle 24 — exact hash navigation correction

Fresh UX review of the twice-green candidate found one medium functional gap:
legacy four-item Content Workspace links changed the URL hash but not the tab,
while route orientation compared only the pathname and could mark all four
links current. B273 makes the tab a pure function of the router location and
binds each sidebar current state to the full pathname plus hash. B274 closes the
review's low test-quality finding by wrapping the keyboard-triggered router
transition in React's async test boundary. The green gates remain historical;
both exact-head gates and all independent reviews must restart after this repair.

## Analysis cycle 25 — data and operations review rejection

The fresh data and operations reviews rejected exact head `89098c90` despite
two complete-gate passes. Data review returned C0/H3/M2/L0: broad direct DML
remained outside the fixed-procedure contract, RLS hid other-tenant memberships
from tenant-only closure, durable replay could not discover queued work, subject
exports exposed an index rather than complete registered values, and the backup
ending comparison remained inside the original snapshot. Operations review
returned C0/H1/M3/L1: the expiry timer lacked a stable checkout context,
registration could poison scanner capacity, rollback status/evidence was not
propagated through PowerShell, the documented expected-commit example could
include an unparsed comment, and production workers still inherited a bundled
database dependency.

Tasks B275-B284 bind every finding to a least-authority implementation and a
real failure-path proof. The prior green gates remain historical only. No
publication, merge, provider, DNS, certificate, deployment, credential, or
destructive action is authorized or performed by this repair cycle.

## Analysis cycle 26 — fixed privacy authority and observable backup fence

Implementation of B275-B284 removed direct privacy-worker DML, routed queue
discovery, claims, subject actions, and settlement through fixed unexpired-lease
procedures, and restricted workspace reads to the claimed subject. Disposable
PostgreSQL now proves same-tenant unrelated rows are invisible, direct mutation
is denied, expired settlement fails, replay discovery succeeds, and tenant-only
deletion preserves an active identity in a second tenant. Value-level subject
rows and safe identity authenticator, credential, and audit metadata are included
without credential material; schema introspection rejects a stale inventory.

The first real live-ledger concurrency drill also found that psycopg does not
accept a `servicefile` connection keyword. B285 records the additional gap. The
backup connector now parses one private bounded service section through a closed
libpq-key allowlist, opens a genuinely separate connection, and observes a
concurrent committed ledger change that the exported snapshot cannot see. The
generic-expiry scanner isolates malformed and crashing plans, capacity fails at
registration, its systemd unit has a stable checkout, rollback failures propagate
with evidence, inline expected-commit comments parse safely, and production worker
startup no longer brings up bundled PostgreSQL. Browser hash navigation and the
Operations visual evidence were regenerated from the repaired sources. No external
or destructive operation was performed.

## Analysis cycle 27 — newly published transitive dependency advisory

The first exact-head complete gate passed 106 of 107 checks and rejected only
the production dependency audit. During the run, npm began reporting the new
high-severity GHSA-2883-xcg3-v3hh CPU-exhaustion advisory in transitive
`js-yaml` 4.3.1 through `@redocly/openapi-core`. B286 records the live supply-
chain discovery. A lockfile-only resolution selects the non-vulnerable compatible
dependency graph, a clean install resolves `js-yaml` 4.3.2, and the full npm audit
reports zero vulnerabilities. The failed gate remains historical and both exact-
head passes restart from zero after the dependency commit.

## Analysis cycle 28 — bounded mobile raster stability

The second exact-head gate rejected one mobile command-menu capture after the
first gate had passed the same source and baseline. Expected and actual images
differed by one pixel out of the complete rendered menu; all 49 other executed
visual assertions passed, including the menu's structure, reachability, motion,
scroll, SVG, responsive, and accessibility behavior. B287 records this observed
cross-run GPU raster edge rather than accepting a changed baseline. The exact
menu capture now permits at most two changed pixels, materially tighter than the
existing 20-pixel utility-menu bound, while every functional and geometric check
remains exact. A materially shifted or restyled menu still fails. Both clean
exact-head gates restart after this test-contract correction.

## Analysis cycle 29 — independent review rejects the twice-green head

Exact commit `2e889434ca416418f4c86baef7e6275d090e2a25` passed all 107
complete-gate checks twice, 66 privacy/tenant/runtime isolation tests ten times,
and 61 backup/expiry/capacity/deployment tests ten times. Fresh independent
review nevertheless rejected release readiness with one critical, five
deduplicated high, and five medium findings. Automated success is therefore
historical evidence only and cannot authorize publication or deployment.

The critical deployment path copied the complete production environment and a
fully interpolated Compose model into a recursively collected evidence tree.
Additional blockers cover disabled SSH host verification, database-owner
credentials in the public API, successful expiry service exits after provider
failure, stale Beat evidence, race-prone expiry capacity, global privacy queue
enumeration, implicit global-account destruction from a tenant-only request, an
endpoint-only backup fence that cannot detect a true A-to-B-to-A cycle, manually
duplicated subject inventories, and router/sidebar state divergence. Tasks
B288-B298 turn every finding into an implementation and negative proof. No
publication, merge, deployment, provider, DNS, certificate, credential, or
destructive operation was performed.

## Analysis cycle 30 — integrated least-authority acceptance corrections

The B288-B298 implementation passed its focused deployment, expiry, backup,
privacy, runtime-heartbeat, and navigation suites. Disposable PostgreSQL then
found three integration gaps before release: the legacy content role retained a
historical operation-table grant, expected policy counts still described the old
dispatcher design, and the API compatibility migration ledger could overwrite
the expanded global-action constraint on a fresh database. The repair explicitly
revokes legacy operation-table privileges, updates the fixed policy contract, and
adds ordered API migration 013 so Django and API schema ownership converge.

The same acceptance now proves that the data-rights worker cannot enumerate the
queue or read request ciphertext before an exact dispatcher handoff, expired
claims receive a new bounded dispatch token, tenant deletion preserves the global
identity and other membership, and separately confirmed global deletion closes
all memberships and anonymizes/deactivates the account. It also proves the public
API role is non-owner/non-elevated, cannot create schema objects or read workspace
tables, and that the registry exactly matches every recognized subject-reference
column. The production and preview migration commands temporarily inject owner
credentials only into the bounded migration process; the network-facing API keeps
its separate least-privilege login. Real forward, reverse, concurrency, media-RLS,
and A-to-B-to-A generation-fence acceptance is green. Complete gates and fresh
independent review still must restart on the resulting exact commit.

## Analysis cycle 31 — first repaired-head complete-gate rejection

The first complete gate on `218b289` rejected before it could become release
evidence. PostgreSQL-only trigger DDL in migration 0032 was represented as an
unconditional `RunSQL`, so SQLite test databases attempted to parse PL/pgSQL.
Intentional environment and privacy-route changes also invalidated the exact
surface lock, while the sidebar source change invalidated the committed
Operations visual manifest. Tasks B299-B301 record these integration findings.

Migration 0032 now uses vendor-guarded reversible `RunPython` operations: SQLite
performs a deterministic no-op and PostgreSQL retains the already-proven trigger
creation and reversal. The route/config lock was regenerated only after source
normalization and passes its hostile mutation tests. The complete 42-case
Operations browser matrix ran against a production build across responsive,
localization, contrast, reduced-motion, Firefox, and WebKit profiles; 22
applicable cases passed and 20 profile-inapplicable state repetitions skipped by
contract. Its current-run receipt and 35 exact captures now bind the regenerated
manifest. The rejected gate remains historical and the required two passes
restart from zero on the next clean commit.

## Analysis cycle 32 — fresh review rejects the twice-green repaired head

Exact commit `2c73b1432c779f4b2b6bf14280baf21d1a21cb38` passed all 107
complete-gate checks twice and passed both critical privacy/runtime and
backup/deployment suites ten consecutive times. Fresh independent UX, data, and
operations review nevertheless rejected release readiness with two critical,
four high, four medium, and two low findings. Those automated passes are now
historical evidence only; no publication or deployment is authorized from this
head.

The review found that deployment exception paths could still retain interpolated
Compose output without a final secret gate, and that Python orchestration still
accepted unknown SSH hosts before uploading the production environment. It also
found process startup preceding role bootstrap and migrations, rollback claiming
completion without schema or endpoint proof, and expiry failures lacking a
durable notification consumer. Data review found blanket API schema DML grants,
missing generation triggers for two media-reference branches, oversized artifact
scanning being skipped, and global privacy scope derived only from current
memberships. UX review found an uncanonicalized workspace hash that removed
current-route orientation and incomplete keyboard tab semantics; one email
service description remained stale. Tasks B302-B313 capture every deduplicated
finding and its required negative proof. The current head remains local and
rejected while these corrections proceed.

## Analysis cycle 33 — migration dependency order exposed by fresh PostgreSQL

The first disposable PostgreSQL run after B307 correctly failed closed because
Django migration 0032 now verifies every explicitly granted API table, while the
acceptance and production sequences still created the API schema after Django.
Older cross-schema migrations had relied on those tables without expressing the
ordering contract. B314 records the integration gap. Every affected sequence now
bootstraps roles, runs the API owner migration, and only then runs Django's
cross-schema least-authority migrations before starting request or worker
processes. The repaired disposable run passed mixed-version, workspace RLS,
reverse/forward role migration, and media forward/reverse acceptance, including
the new cross-tenant DML, migration-ledger, queue, orphaned-subject, and media ABA
proofs.

## Analysis cycle 34 — first exact-head gate rejection

Complete gate 1 on `f81dcdc88bc46950fac832b2cca22b45e226433c`
rejected two checks and made the remaining dependent checks not runnable. The
service-health contract searched for a removed legacy comment and still expected
workers in the pre-migration startup command, while the corrected graph
intentionally starts only Redis before migrations. Changed-line coverage reached
89.67% against the mandatory 90% floor because exact SSH trust logic remained
inside an import-side-effectful orchestration program that cannot be safely unit
executed. B315-B316 record both gaps.

The service contract now asserts the real role-bootstrap, API migration, Django
migration, request-service startup, and mandatory worker ordering. Exact SSH
trust admission is isolated in a side-effect-free module with direct negative
tests for missing, directory, and symlinked inventories plus positive proof that
Paramiko loads only the supplied host inventory, retains RejectPolicy, and emits
strict OpenSSH options. Gate 1 remains rejected historical evidence; both exact-
head passes restart after a new commit.

## Analysis cycle 35 — second exact-head gate rejection

Complete gate 1 on `0068626a6113a1de908cd0572e3f890bb625b5c4`
rejected the media-library contract and changed-line coverage. The API virtual
environment reported locked PyYAML 6.0.3 but contained an internally mixed
installation: its scanner called the legacy six-field constructor while its
installed `SimpleKey` required the current seventh field. A forced no-cache
reconciliation from the exact lock restored a coherent wheel, and real Compose
YAML parsing plus the previously failing media isolation test passed. The lock
itself did not change.

Changed-line coverage improved from the prior rejected head but remained 0.04
percentage points below its mandatory floor. The missing directly relevant
branches were the recursive deployment-artifact scanner's comment/filter,
symlink rejection, and CLI pass/reject paths. B317-B318 record both failures and
their deterministic proofs. This rejected run remains historical only; both
complete gates restart from zero on a new exact commit.

## Analysis cycle 36 — independent review rejects the twice-green head

Exact commit `7905e36cb02f785d7cf2e683027137be301d9f76` passed all 107
complete-gate checks twice plus ten consecutive privacy/runtime and ten
consecutive backup/deployment repetitions. Independent UX review returned
C0/H0/M0/L0, but operations returned C1/H2/M1/L0 and data returned
C0/H1/M2/L0. The candidate is rejected and none of that automated evidence
authorizes publication.

Operations found that the PowerShell wrapper invoked a generic Python lifecycle
before its repaired exact-commit block. That legacy path reset to a mutable
branch, suppressed source errors, and started the complete stack before the
migration fence; it also caused the later rollback baseline to describe already
mutated state. Fresh hosts lacked an authenticated host-key enrollment boundary,
TLS probes disabled trust verification, and standalone migration/verification
entrypoints did not enforce the API-before-Django-before-start sequence. Data
review found broad API read/update access to outbox rows containing reset tokens,
missing site/asset generation triggers for ledger-changing reassignments, and a
0032 reverse migration that did not restore predecessor RLS state. B319-B325
capture every deduplicated blocker and required negative proof. Both complete
gates and all repetitions must restart from zero after repair.

## Analysis cycle 37 — repaired-head complete-gate rejection

The first complete gate on `66a9988f36a10af7ec9215d35b6526cbb01567bf`
rejected only the API test aggregate. The new migration CLI parsed the parent
pytest process arguments when its `main()` function was called directly, so its
existing unit contract failed before exercising the ledger. B326 separates the
programmatic empty-argument default from the executable's real argument parsing
and adds a direct non-mutating `--check` proof. The rejected run is historical;
both complete gates restart from zero on the next exact commit.

## Analysis cycle 38 — changed-line coverage rejection

Complete gate 1 on `eb945adee459ee8243b82a304d3fc3aaf6fbd5e0`
passed every functional check but rejected changed-line coverage at 89.98%
against the unchanged 90% floor. The added disabled legacy-orchestrator guards
are intentionally unreachable through the supported deployment entrypoint, but
the nearby API migration disable and bounded advisory-lock failure behavior was
not directly exercised. B327 adds those meaningful release-safety proofs rather
than excluding code or lowering the floor. The rejected gate remains historical
and both complete gates restart on a new exact commit.

## Analysis cycle 39 — independent review rejects the twice-green head

Exact commit `50302d08c6b8ed3fc6414692e21596476b7f765a` passed all 107
complete-gate checks twice, ten privacy/runtime repetitions, and ten
backup/release/deployment repetitions. Fresh independent review nevertheless
returned UX C0/H0/M2/L0, data C0/H0/M1/L0, and operations C1/H4/M2/L1. The
candidate is rejected; all exact-head automated evidence is historical and no
publication, merge, deployment, provider, DNS, certificate, credential, or
destructive action is authorized from it.

The critical issue exposed the complete operator environment to Traefik and
persisted its raw environment in remote evidence. High findings cover an
inconsistent provisioning-mode state machine, staging-only certificates tested
against the ordinary production trust store, rollout failures outside the
rollback boundary, and asynchronous mutation being able to reach terminal
success before completion. Medium findings cover migration wrappers that omit
role bootstrap and owner migration identity, fail-open tracked-environment
detection, independently failed Settings resources shown as empty/default fact,
and untranslated privacy operation tokens. Tasks B328-B337 capture the complete
deduplicated repair and proof set. Both complete gates, critical repetitions,
and all independent reviews restart from zero only after a new clean commit.

## Analysis cycle 40 — pre-gate fresh-host and evidence hardening

Pre-gate inspection of the cycle-39 deployment repairs found two additional
release blockers before a new candidate was committed. Prior-state capture
required an existing `.env`, making the approved newly provisioned-host path
unable to deploy or prove a safe rollback. Rendered Traefik diagnostics also
retained scoped basic-auth verifier values even though the broad container
environment capture had been removed.

B338-B340 record explicit fresh-versus-existing rollback state, structural
basic-auth evidence redaction, and their focused acceptance. These findings were
caught before publication or provider mutation. All earlier exact-head evidence
remains historical; complete gates and independent review may restart only from
the new committed candidate after this bounded repair passes.

## Analysis cycle 41 — exact-head changed-line coverage rejection

Complete gate 1 on `84a12df45924e28a33882463e0e9a1aa7b29778b`
passed every functional check but rejected changed-line coverage at 89.48%
against the unchanged 90% floor. The missing lines were concentrated in the new
deployment-mode and staging-TLS command, retry, timeout, disabled-verification,
and missing-SAN paths. B341 records direct behavioral coverage of those release
boundaries. The rejected gate is historical; both complete gates restart from
zero on the next exact commit.

## Analysis cycle 42 — independent review rejects the twice-green head

Exact commit `52e741259be7f61d33812b18a5d229ceae222f2d` passed all 107
complete-gate checks twice, ten privacy/runtime repetitions, and ten
backup/release/deployment repetitions. Fresh review nevertheless returned UX
C0/H0/M1/L0, data C0/H1/M0/L0, and operations C0/H5/M1/L1. The candidate is
rejected and all exact-head evidence is historical.

Review found an owner-scoped migration process that did not receive production
environment validation, untranslated security-action identifiers, fail-open
provider lookup, an unbuilt distinct migration image, incomplete fresh-target
teardown proof, fail-open evidence retention, suppressed AllTests failures,
and staging subsite probes without pinned trust or terminal assertions. B342-
B350 record the complete deduplicated repair and proof set. Publication, merge,
deployment, provider, DNS, certificate, credential, and destructive authority
remain unavailable; every exact gate and review restarts after a new commit.

## Analysis cycle 43 — pre-commit coverage tracer isolation

The repaired working tree passed its focused deployment suites, but the first
complete pre-commit gate exposed rare C-tracer interpreter-state corruption in
the DigitalOcean partition: `pathlib` internals became invalid even though the
same deterministic partition passed immediately in isolation with the same
test order. The failure remained visible and blocked the gate. B351 records the
bounded correction to use coverage's pure-Python tracer for this partition,
preserving subprocess isolation, coverage enforcement, and nonzero failure
propagation while removing the native corruption surface. All exact-head gates
and reviews remain pending until a clean repaired commit exists.

## Analysis cycle 44 — independent review rejects the twice-green candidate

Exact commit `635437ea21587250f9ecc847b13fc6d7b004221e` passed both
107-check complete gates plus ten privacy/runtime and ten
backup/release/deployment repetitions. Fresh independent review nevertheless
returned UX C0/H0/M1/L0, data C0/H0/M1/L1, and operations C0/H3/M1/L1. The
candidate is rejected and every automated result is historical.

The reviewers found that real security events collapsed to an unknown label,
DATABASE_URL could override the validated database host, the standalone
evidence verifier did not reject symlinked ancestors, AllTests retained a
separate insecure TLS stack, provider creation remained vulnerable to a
lookup/create race and duplicate selection, credential-bearing source URLs
could enter provider-retained user-data, and the htpasswd validator did not
propagate failure. The bootstrap also retained floating root-piped installers.
B352-B360 record the complete deduplicated repair and proof set. No publication,
merge, deployment, provider, DNS, certificate, credential, or destructive
action is authorized; all gates, repetitions, and reviews restart from zero on
the next clean commit.

## Analysis cycle 45 — combined repair gate catches stale DSN test contract

The cycle-44 repair passed its focused deployment, API, localization, lint, and
production-build suites. Its first combined complete gate then correctly failed
one API security check: the runtime now consumes the validated
Settings.DATABASE_URL, while the older test mutated the process environment
after the singleton settings object had loaded and expected the former bypass
behavior. The test was corrected to exercise the validated value, and malformed
URL coverage was added without restoring the bypass.

The exact affected security partition passed 64 checks, the deployment
regression subset passed 57 checks, the full DigitalOcean suite passed 399
checks, and the repaired dirty tree passed all 107 complete-gate checks at
.artifacts/complete-gate/20260909T082503Z/result.json. B352-B359 have complete
implementation evidence but remain unchecked under the contiguous ledger until
the earlier acceptance and closeout tasks can also close. B360 remains open
until a clean commit passes both exact-head gates, both ten-run critical suites,
and fresh independent UX, data, and operations review with zero critical, high,
or medium findings.

## Analysis cycle 46 — exact-head changed-line coverage rejection

Exact candidate bddc9549aa182e108a0c0f319bc99ceca29b27c2 passed every
functional and runtime family in exact-head gate 1 but was rejected by the
unchanged changed-line coverage floor: 89.83% against the required 90%. The
missing proof was concentrated in the new provider lookup CLI and lease error
paths. No functional failure was waived and the floor was not changed.

B361 adds direct typed success, provider-error, invalid-identity, empty-name,
and lease-release behavior. The focused suite passed 15 checks; the full
supported DigitalOcean coverage run then passed and raised changed-line
coverage to 90.05%. The rejected candidate and its gate are historical. Both
exact-head complete gates restart from zero after the correction is committed.

## Analysis cycle 47 — second exact-head gate visual nondeterminism

Exact candidate a94cd4ac9a1033516a58982e39adea610e6cfc79 passed gate 1
with all 107 checks, then gate 2 rejected the visual harness. The desktop run
selected a hidden duplicate Search option by ordinal, while the mobile run
measured 2.375 CSS pixels of subpixel center variance against a two-pixel
threshold. The same product behavior passed the other viewports and the first
exact gate, proving the selector and threshold were nondeterministic.

B362 selects the actually visible accessible option and retains a strict
three-CSS-pixel centering tolerance. The failed second gate and the green first
gate are both historical; the visual matrix and both exact-head gates restart
from zero after the correction is committed.

The first replacement candidate then exposed the deeper accessibility contract:
three loop copies were simultaneously accessible while selection normalized to
the middle copy. Decorative copies are now aria-hidden and removed from keyboard
focus, leaving exactly one canonical option per utility. The stale unit test was
updated to the same single-option contract. The affected unit suite passed 5
checks, the affected three-viewport browser suite passed 6 checks, the full
visual matrix passed 50 checks with 4 intentional skips, and the complete
frontend suite passed all 280 checks with its coverage thresholds intact.

The next exact gate reproduced one final product race: the click handler began
smooth centering and then reread the old scroll position two animation frames
later, allowing an intermediate loop item to overwrite the user's direct
selection. Direct selection now atomically centers the canonical option before
normal scroll reconciliation. The affected six-check browser matrix passed five
consecutive repetitions across desktop, tablet, and mobile with no recurrence.
All exact-head evidence restarts again from the new commit.

## Analysis cycle 48 — independent review rejects the twice-green candidate

Exact commit `3499adffe823d4e586ed494fbff910bcf3729253` passed both
107-check complete gates plus ten privacy/runtime and ten
backup/release/deployment repetitions. Fresh independent review nevertheless
returned UX C0/H0/M2/L0, data C0/H1/M1/L0, and combined
code/security/operations C0/H2/M2/L0. The candidate is rejected and all of its
automated evidence is historical.

Review found runtime database roles could collide with the PostgreSQL owner,
canonical local database aliases could bypass the external-target guard,
enabled public utility controls had no action while disabled controls could
become selected, and the public Obsidian shell lacked German, Arabic, and RTL
parity. The provider tag pseudo-lock was neither conditional nor owner-bound,
the explicit address override bypassed authoritative provider identity,
provider dependencies remained mutable, bootstrap package resolution was not
attested, and the staging TLS repair lacked behavioral certificate validation.
B363-B370 record the deduplicated repair and proof set. No publication, merge,
deployment, provider, DNS, certificate, credential, or destructive action is
authorized; every exact gate, repetition, and independent review restarts only
after a new clean repaired commit.

## Analysis cycle 49 — conditional lease implementation correction

Implementation review rejected the first B366 repair before commit. The
DigitalOcean Spaces API documents conditional headers for object reads but not
for `PutObject` creation or `DeleteObject`; treating those undocumented headers
as an atomic mutex would permit duplicate paid-resource creation. The draft
Spaces implementation and its credentials were removed without contacting a
provider.

The replacement uses Git server-side atomic ref creation and exact
`force-with-lease` deletion in a dedicated private coordination repository.
Production configuration rejects a missing remote, local-only remote, insecure
or credential-bearing URL, command-style helper, and any canonical alias of the
source origin. The lease commit binds name, random owner nonce, and expiry;
conflict, crash, expiry, changed ownership, and uncertain provider-create
outcomes remain fail-closed until exact-owner recovery. Real simultaneous
pushes to a disposable bare remote admitted exactly one owner, and the focused
deployment, provider, TLS, visual-contract, database-role, API-host, and UI
tests passed. The complete gate now includes the provider lease, paginated
lookup, and real TLS behavior suites. Exact-head evidence remains pending until
the repaired source is committed.

## Analysis cycle 50 — pre-commit coverage admission

The repaired dirty-tree complete gate passed 106 of 107 checks. Its sole
rejection was changed-line coverage at 89.94% against the unchanged 90% floor.
The newly added provider lease and its real Git concurrency tests were untracked,
so the exact Git-diff coverage collector correctly did not admit either side of
that evidence. This is not accepted as release evidence and the threshold is
not reduced. B370 requires the complete repaired tree to become one clean exact
candidate before both gates restart; that exact commit will make the source and
tests jointly visible to changed-line coverage.

## Analysis cycle 51 — first exact-head gate rejects uncovered utility wiring

Exact candidate `40dd228fed75e86029571bcdb5843c25263efdd9` passed 106 of
107 complete-gate checks. Changed-line coverage remained release-blocking at
89.71% against the unchanged 90% floor. Review of the uncovered lines found the
new Home utility dispatcher needed direct behavior tests and also exposed that
the security and command sections had test identifiers but no matching DOM IDs,
so their real scroll actions were inert.

The repair adds the missing stable section IDs and exercises German localized
security and search actions, Web Share success and user cancellation, clipboard
fallback, visible prompt fallback, remote-lease configuration isolation,
insecure transport rejection, bounded owner/TTL inputs, exact revision release,
and Git transport failure. Focused UI and provider suites pass. The failed gate
is historical; both exact-head gates restart only after a new commit.

## Analysis cycle 52 — independent review rejects the twice-green candidate

Exact commit `82df375cbbdb42ce83613883b949573de228dbcf` passed both
107-check complete gates plus ten privacy/runtime and ten
backup/release/deployment repetitions. Fresh independent review still returned
UX C0/H0/M2/L0, data C0/H0/M1/L0, and combined
code/security/operations C0/H0/M4/L2. The candidate is rejected and all of its
automated evidence is historical.

Review found that percent-encoded database authorities could validate
differently from libpq, the public utility action rail claimed incomplete
listbox semantics, localized share outcomes and titles were missing, paid
provider activation could poll forever, the Git lease inherited ambient
transport trust, unvalidated deployment names and paths entered root shell
source, and required provider/bootstrap identities were not bound into terminal
evidence. Documentation and dependency helpers also lagged the implementation.
B371-B379 contain the deduplicated repair and proof set. No publication, merge,
deployment, provider, DNS, certificate, credential, or destructive action is
authorized; both exact gates, both repetition families, and all independent
reviews restart only from a new clean repaired commit.

## Analysis cycle 53 — independent review rejects the repaired candidate

Exact commit `9eb4f32f35fe28f7d88223d234ab40cd347fa62b` passed both
107-check complete gates and broader ten-run privacy/runtime/settings and
backup/release/deployment suites. Fresh review nevertheless returned data
C0/H0/M1/L0, UX C0/H0/M0/L1, and combined code/security/operations
C0/H0/M4/L0. The candidate is rejected and none of its green automation permits
publication.

Data review proved that libc/libpq legacy numeric IPv4 forms such as
`2130706433`, `127.1`, `017700000001`, and `0x7f000001` still resolved to
loopback after strict Python address parsing declined them. Operations review
found no hard maximum on the configured provider-ready deadline, ambient Git
askpass/exec-path/token state outside the partial scrub, terminal evidence that
did not require exact discovered provider ID/IP correlation, and repetitions
that were observed in the terminal but not persisted under the reviewed source
hash. UX review found the blocking manual-copy prompt left a status which
incorrectly described the already-closed dialog. B380-B385 contain the complete
deduplicated repair and proof set, including a source-bound atomic repetition
manifest. Both complete gates, persisted repetitions, and every independent
review restart only after the next clean commit.

## Analysis cycle 54 — pre-commit coverage admission

The cycle-53 repaired working tree passed 107 of 108 complete-gate checks. Its
only rejection was changed-line coverage at 89.94% against the unchanged 90%
floor. The new exact-head repetition runner and its tests were untracked, so the
Git-diff coverage collector correctly excluded their paired source and proof,
the same admission boundary previously observed for new deployment modules.

The runner was moved under the supported DigitalOcean coverage partition and
its focused suite now covers clean/exact source admission, successful execution,
failed execution, atomic replay, member tampering, manifest tampering, missing
evidence, and CLI success/failure. The failed dirty-tree gate remains historical
and is not release evidence. B385 requires committing the complete source and
tests together before both exact-head gates and persisted repetitions restart.

## Analysis cycle 55 — independent review rejects the twice-green candidate

Exact commit `9f4d58acf068ec6d51f701bed01f49238ddd7798` passed both
108-check complete gates and produced one exact-source manifest binding twenty
broader repetition logs. Fresh UX review accepted with C0/H0/M0/L0, but data
review returned C0/H0/M2/L0 and operations review returned C0/H0/M3/L0. The
candidate is rejected and no publication is permitted from its green evidence.

Review proved that named libc localhost aliases bypassed the production database
guard, while the repetition runner inherited credential-bearing URLs and could
label mixed source if its checkout changed during the long run. Operations also
found the native-Windows broker skipped ACL validation and the otherwise absolute
Git process retained loader-injection state. B386-B390 contain the deduplicated
repair and proof set: fixed local-name rejection, a minimal test environment, an
exact detached worktree with continual source validation, strict evidence member
admission, and SID-based Windows broker ancestry validation plus a minimal Git
environment. Both exact gates, persisted repetitions, and every independent
review restart only after a new clean candidate. No publication, merge,
deployment, provider, DNS, certificate, credential, or destructive action is
authorized by this analysis.

## Analysis cycle 56 — pre-commit coverage admission

The repaired dirty tree passed 107 of 108 complete-gate checks. The sole
rejection was changed-line coverage at 89.95% against the unchanged 90% floor,
three covered executable lines short of admission. Every product, security,
integration, visual, dependency, and plan check otherwise passed.

Inspection found the fixed trusted-Git selector's symlink and filesystem-error
failure paths were not directly exercised. B391-B392 add behavioral rejection
tests for both paths and require a new full pre-commit pass without lowering,
rounding, or bypassing the coverage floor. The failed gate is historical and no
exact-head evidence or publication can begin until the complete repaired tree
passes.

## Analysis cycle 57 — final operations review rejects the candidate

Exact commit `8b3dc9fd5f3498e3635d5e0a29615869f6185d97` passed two
108-check complete gates and its isolated source-bound 10+10 repetitions. Fresh
UX and data reviews accepted with C0/H0/M0/L0, but combined operations/security
review returned C0/H0/M1/L1. The candidate is rejected and remains unpublished.

The Windows ACL verifier derived PowerShell from ambient SYSTEMROOT, and the
token-bearing Git child retained ambient SYSTEMROOT, WINDIR, COMSPEC, and temp
paths. A hostile caller could therefore substitute executables before the SID
decision. Review also found that ignored repetition-evidence parent directories
could be symlinked even though the destination and members were protected.
B393-B395 replace ambient Windows roots with the kernel-reported directory,
validate one newly created private temp root, omit command-shell authority, and
reject every symlinked/non-directory evidence ancestor. Every exact gate,
repetition, and review restarts from the next clean commit; no publication or
external action is authorized by the rejected evidence.

## Analysis cycle 58 — operations review finds outer temp authority

Exact commit `eddc45c6f14fcdb31ff283165edee5dabdc55215` passed two
108-check exact gates and exact-source 10+10 repetitions. UX and data reviews
again found no critical, high, or medium issue, but operations/security review
returned C0/H0/M1/L1. The candidate is rejected and remains unpublished.

Although each Git child's TEMP/TMP was ACL-validated, authoritative lease object
construction and deletion still created an outer repository through Python's
ambient temporary-root selection. A hostile outer root could therefore alter
the objects/refspec before the remote CAS. Reviewers also noted replay accepted
group/world-widened evidence permissions. B396-B399 introduce one fixed-anchor
private-temp factory for both outer repositories and inner scratch, validate
owner/mode and safe ancestry on Unix plus SID ACLs on Windows, ignore ambient
temp selection, and reject evidence permission drift. Both exact gates,
repetitions, and all reviews restart from the next clean candidate; the rejected
evidence grants no publication or external authority.

## Analysis cycle 59 — pre-commit coverage and visual admission

The cycle-58 dirty tree passed 106 of 108 complete-gate checks. Changed-line
coverage remained release-blocking at 89.94% against the unchanged 90% floor.
The light-theme media-detail screenshot also differed once by five percent even
though no frontend or baseline source changed; an immediate isolated rerun of
all three light-theme media owners passed against the existing baselines.

B400 directly exercises the unified private-path factory's Windows ACL success,
ACL rejection, and filesystem-error paths rather than weakening coverage. B401
retains the one-time visual failure as historical evidence, forbids an unrelated
baseline update, and requires the full visual owner to pass again inside a new
complete gate. No candidate commit or exact-head evidence is admitted until the
entire repaired tree is green.

## Analysis cycle 60 — exact-head repetition failure visibility

Exact commit `233b9ad5a7e4926dceb3b7def6f0140d00e49527` passed two
independent 108-check complete gates. Its isolated repetition runner then stopped
at backup/release/deployment repetition six. The same 211-test family passed
immediately under a freshly constructed equivalent hermetic environment, so no
deterministic product assertion was reproduced. The failed runner staging area,
however, was removed before its log could be reviewed; this is an observability
gap even though it fails the release safely.

B402-B403 require bounded private failure evidence containing exact source,
suite, repetition, command, exit code, output truncation state, and member plus
aggregate digests before the sanitized terminal error is returned. The existing
candidate is rejected despite both green complete gates. All exact gates and
repetitions restart only after the evidence runner proves both terminal failure
retention and success; no publication is authorized by the partial evidence.

## Analysis cycle 61 — concurrent lease availability and coverage admission

The cycle-60 precommit gate completed 106 of 108 checks. The provider lease's
real simultaneous-claim test intermittently rejected both contenders, and
changed-line coverage reported 89.93% against the unchanged 90% floor. Stress
reproduction confirmed the lease result was intermittent while remaining safe:
no run admitted two owners.

The shared fixed-anchor private parent was removed after each child context.
Two callers could each validate that parent, then one could remove it before the
other created its child; a later cleanup could similarly remove a newly created
empty parent. B404-B405 retain the validated owner-only parent while continuing
to delete every scratch child, then exercise concurrent construction and remote
claim behavior. B406 directly covers the new failure evidence's truncation and
replay-rejection branches rather than weakening or rounding coverage. The failed
gate is historical; exact evidence and publication remain blocked until a new
complete gate passes.

## Analysis cycle 62 — exact coverage admission

The cycle-61 complete gate passed 107 of 108 checks. Concurrent lease admission,
all product and security suites, browser visuals, account E2E, and isolated
PostgreSQL acceptance passed. The sole rejection was changed-line coverage at
89.99% against the unchanged 90% floor. B407 directly exercises the remaining
non-directory evidence-ancestor rejection. The threshold is neither lowered nor
rounded, and exact-commit evidence remains blocked until the next full gate is
green.

## Analysis cycle 63 — native-Windows evidence privacy review

Fresh UX and data reviews accepted exact commit `6dd7f3d3` with no findings.
Operations/security accepted publication with C0/H0/M0/L1: native Windows would
skip POSIX ownership/mode enforcement for repetition evidence, while chmod is
not a SID/DACL privacy guarantee. Current WSL evidence is private and valid, but
the reusable candidate is rejected to close the residual.

The repository's operational boundary mandates WSL Bash for this workflow.
B408-B409 therefore fail native-Windows execution before source or artifact
access instead of duplicating a privileged ACL verifier in the evidence runner.
B410 restarts all exact evidence and reviews from a new clean commit and raises
final acceptance to zero findings at every severity. No publication or external
action is authorized by the rejected candidate.

## Analysis cycle 64 — hosted CI parity rejects the published draft

Draft PR #55 at exact commit `03cbfc9cbf3a0fd218f2c159c01da09d0567e9cd`
was correctly rejected by hosted CI despite two green 108-check local gates,
twenty persisted exact-source repetitions, and zero-finding independent reviews.
The hosted environment exposed four deterministic parity gaps: API typing relied
on an untracked PyYAML stub, the workflow replaced pinned tooling with mutable
latest installs, Django typing was absent locally and found an invalid inferred
database-settings shape, and both integration and disposable stacks violated the
required role-bootstrap -> API-migration -> Django-migration order. The E2E and
smoke jobs therefore stopped before any browser or HTTP assertion, while the
backend integration job omitted the migration that creates the fenced email
enqueue function.

B411-B417 make development and CI tool dependencies exact, add Django typing to
the complete gate, enforce one schema bootstrap DAG in backend CI and the fresh
Compose stack, exercise email enqueue and delivery through their distinct
least-privilege roles, retain migration-specific failure logs, and add repository
contracts for every ordering decision. The published candidate and all earlier
green evidence are rejected. A new clean commit must pass fresh local gates,
fresh-volume E2E/smoke, persisted repetitions, zero-finding reviews, and every
required GitHub check before readiness can be reconsidered. Merge, deployment,
provider, DNS, certificate, credential, and destructive authority remain absent.

## Analysis cycle 65 — fresh-volume readiness exposes stale ledger authority

The corrected disposable migration graph completed both API and Django ledgers
from a new empty volume, proving the original crash fixed. Runtime startup then
failed closed at API schema readiness: the dedicated API role could read the API
ledger but had no permission to read Django's ledger. Inspection also found that
readiness accepted API migration 012 and Django migration 0031 even though newer
required migrations existed. The failed fresh-volume run is retained as
historical evidence and does not authorize release.

B418-B420 add a reversible forward migration granting only `SELECT` on the
non-secret Django migration ledger to the API runtime role, bind readiness to the
actual latest required API and Django migrations, and require a second empty-
volume stack plus role-negative checks before exact evidence restarts. No owner,
DDL, table-data, bypass-RLS, publication, merge, deployment, or provider
authority is added.

## Analysis cycle 66 — disposable-stack host-port collision

The second fresh-volume stack reached a healthy least-privilege API after the
ledger-readiness correction, but the frontend could not bind host port 8080
because a separate existing local Base2 test stack already owned it. This is an
environment isolation defect, not a product or migration failure; the existing
stack was preserved rather than stopped or destroyed.

B421-B422 retain CI's documented default ports while allowing an explicit local
E2E host-port namespace, and prove the disposable stack can coexist without
mutating unrelated containers. Container ports, service URLs inside the graph,
and hosted CI behavior remain unchanged.

## Analysis cycle 67 — browser test-support role isolation

The isolated-port fresh stack became healthy and smoke-ready. Playwright then
rejected both email-token scenarios because the legacy test-support route tried
to read the outbox through the now-correct least-privilege API process. Granting
the API direct outbox reads would undo the production boundary, so that path is
rejected.

B423-B425 place the single keyed outbox inspection route in a synthetic-only
application process using the existing email-worker read role, expose it only on
host loopback in the disposable Compose file, and direct Playwright alone to its
separate endpoint. The synthetic application fails startup unless explicit E2E
mode and key are present, publishes no docs or OpenAPI surface, and is absent
from production Compose and deployment paths. Fresh browser and negative-route
tests must pass before exact evidence restarts.

## Analysis cycle 68 — full-gate reversed-function inspection

The first repaired full gate rejected two deterministic proof defects. The
surface-drift lock correctly detected the intentional complete-gate manifest
change. PostgreSQL acceptance also proved that the reversed API-role checker
tried to resolve privileges for the intentionally absent enqueue function after
it had already verified absence; PostgreSQL rejects that undefined signature
before returning a boolean. Neither defect changes runtime authority, and the
failed gate is retained as evidence.

B426-B428 make the privilege assertion conditional on the forward state while
retaining the explicit absence assertion in the reversed state, add a local
contract for that branch, refresh the generated surface lock only after the
manifest is final, and require the affected acceptance checks plus a new full
gate. Release evidence remains invalid until a clean candidate passes the whole
exact-source sequence and hosted CI.

## Analysis cycle 69 — hosted pytest collection boundary

The first cycle-68 commit passed the 109-check local gate, the pre-push API,
Django, and frontend suites, and 33 hosted checks. Both duplicate hosted API
jobs nevertheless failed closed because pytest's recursive filename discovery
treated `test_support_main.py` as a test module and imported its intentional
production-mode startup guard during collection. The integration job inherited
the same collection failure before reaching database assertions. This is a
packaging/name contract gap; the synthetic service itself remained loopback-only
and no authority was widened.

B429-B431 rename the synthetic entrypoint outside pytest's test-file grammar,
update every exact reference, and locally prove both normal recursive collection
and explicit fail-closed startup behavior. All evidence for commit `02d08ef` is
rejected, including its interrupted exact gate. A new commit must restart local,
fresh-stack, repetition, review, and hosted evidence from zero.

## Analysis cycle 70 — post-format generated-lock ordering

The cycle-69 collection proof passed, then the surface validator rejected the
working tree because the prior commit hook had formatted the governed complete-
gate JSON after its hash lock was generated. The validator behaved correctly,
but the hook lacked a post-format validation phase. The pushed commit therefore
remains rejected even though the semantic JSON was unchanged.

B432-B434 run surface validation after all lint-staged formatters, prove the
ordering contract, regenerate the lock from final formatted bytes, and require a
new clean candidate. The hook does not auto-approve or auto-rewrite the lock: it
fails closed until an intentional drift refresh is reviewed and staged.

## Analysis cycle 71 — explicit integration-marker override

The cycle-70 commit cleared normal hosted API collection and 30 other hosted
checks. Backend integration ran its nine general integration tests, then exited
with pytest code 5 before exercising the two role-correct email tests. The API
pytest configuration defaults to `not integration`; the isolated second pytest
invocation did not explicitly override that default even though the file is
correctly marked integration. No database assertion failed, but an empty test
selection is not acceptable evidence.

B435-B437 explicitly select the integration marker for the isolated role-correct
email invocation, bind that exact command into the CI policy contract, and prove
the command collects and executes both tests. Commit `f228ab7` and its interrupted
exact gate remain rejected; all exact-source evidence restarts from the next SHA.

## Analysis cycle 72 — role-switch helper changed-line coverage

The first exact gate for cycle 71 passed every functional lane but rejected the
candidate at 89.83% changed-line coverage against the unchanged 90% floor. The
new integration-only email role context correctly ran on the fresh PostgreSQL
stack, while its missing-credential and owner-environment restoration branches
were not exercised by the normal coverage suite. Lowering, rounding, or excluding
the integration helper would hide a security-sensitive boundary and is rejected.

B438-B440 directly test missing credentials, worker switching, pool closure, and
both present and absent owner-value restoration in the unit suite. The failed
coverage report and commit `78dd4c2` remain rejected. A replacement commit must
clear the exact 90% floor before any repetition or review evidence can begin.

## Analysis cycle 73 — staged Python lint parity

The cycle-72 unit coverage passed locally, while hosted Ruff rejected one nested
context in the new test under rule SIM117. The full gate would also have rejected
it, but the candidate was published before that long gate completed because the
existing pre-commit hook linted only frontend files. The code finding is simple;
the missing fast local parity guard is the systemic gap.

B441-B443 use one multi-context statement and add pinned API Ruff to lint-staged
for every staged API Python file. The hook remains WSL/repository-local and gains
no network or external authority. Commit `6f1c04a`, its interrupted exact gate,
and hosted failures are rejected; the next candidate must pass local Ruff before
publication and restart all evidence.

## Analysis cycle 74 — delayed responsive-layout scroll state

The first exact gate for the cycle-73 candidate passed every lane through the
visual harness until the tablet movement-control scenario. At that viewport,
late document growth occurred after the navigation's initial geometry read and
without a window scroll or resize event. The retained state therefore reported
the page at its lower edge and omitted the descend control even after the test
returned the viewport to the top. Desktop and mobile passed, but a width-specific
stale control is a user-visible failure and the candidate is rejected.

B444-B447 observe bounded document-size changes and page lifecycle restoration,
settle geometry again after mount, make the browser scenario establish and prove
its top-edge precondition, and stress the exact tablet interaction repeatedly.
The correction grants no network or privileged authority. Commit `2b819a8`, its
failed complete gate, and every prior candidate remain ineligible; all final
evidence must restart from the replacement SHA.

## Analysis cycle 75 — isolated E2E operator contract

The first final fresh-volume attempt used intuitive but nonexistent `HOST_PORT`
variable names because the isolated-port interface was present only in Compose
and absent from the testing guide. Compose correctly ignored those names, then
failed on the occupied default web port without changing the preserved local
stack. The exact disposable project and its new volumes were removed. This was
an operator-contract defect even though hosted CI and both complete gates passed.

B448-B450 document the three exact variable names, fixed isolated project
boundary, test invocation, and exact-project teardown; bind that documentation
to the Compose contract; then restart all final exact-source evidence from a new
candidate. Similar names remain rejected by normal Compose behavior, and no
command gains authority over unrelated projects, providers, or live services.

## Analysis cycle 76 — concurrent visual-review isolation

The first exact gate for cycle 75 collided with a simultaneous independent UX
review because both Playwright processes correctly refused to share fixed
loopback port 4174. The review completed successfully and released its process,
but a multi-agent readiness workflow must not serialize or invalidate evidence
merely because two hermetic visual suites start together.

B451-B454 add an optional strictly numeric unprivileged visual port while
retaining 4174 as the release default, loopback binding, strict-port behavior,
and server non-reuse. Contract tests and operator guidance cover the boundary,
and concurrent focused visual runs on distinct ports must pass before all exact
evidence restarts. No remote host, URL, command, or reusable server becomes
configurable.

## Analysis cycle 77 — isolated browser and readiness review

Independent operations and UX review rejected cycle 75's isolated E2E claim.
The API and web mappings were not loopback-bound, browser build and CORS origins
still targeted hosted defaults, all three tests used Playwright request context
instead of a page, test-support lacked health admission, and the manual guide
did not guarantee preclean, bounded readiness, or teardown after interruption.
The passing request tests therefore proved API flows but not isolated browser
integration, and the known test credentials were needlessly reachable on LAN
interfaces.

B455-B462 bind all published test ports to loopback, parameterize only coherent
browser/API origins with unchanged hosted defaults, add synthetic readiness and
a real page-driven registration journey, and replace manual lifecycle steps with
one fixed-project WSL runner. The runner validates distinct unprivileged ports,
precleans only its exact project, waits for all three services, and traps exact
teardown. Parsed-Compose and policy tests prevent false documentation. All prior
evidence and reviews are rejected until the corrected exact SHA passes the full
sequence with zero findings.

## Analysis cycle 78 — real browser exposes missing API routing

The first real page-driven isolated run rendered the signup UI, but its POST to
the relative `/api` path reached the static Nginx container and returned 405.
The test then timed out because its response predicate incorrectly expected the
direct API-port origin. All three request-context flows still passed and the
runner removed the exact project, confirming that the new journey found a real
frontend-to-backend integration gap rather than a lifecycle failure.

B463-B466 add a fixed same-origin `/api` proxy to the private Compose service,
keep CSP `connect-src 'self'`, bind the browser assertion to the web origin, and
remove the now-unnecessary configurable browser API build origin. The proxy has
no client-controlled upstream and fixed timeouts. A new fresh-volume browser run
must prove the response and authenticated transition before evidence restarts.

## Analysis cycle 79 — fixed-project concurrent ownership

The corrected fresh-volume run passed all four browser and API journeys and
cleaned every exact-project container, volume, and network. A final adversarial
review found that the deliberately fixed Compose project still permitted two
runner processes to overlap: the second process could execute its preclean while
the first owned the stack. Port isolation does not prevent that destructive
same-project race, so the passing single-owner run alone is insufficient.

B467-B469 acquire a nonblocking repository-local `flock` before constructing or
executing any Docker command, assert that ordering in policy tests, and document
the single-owner contract. Kernel process ownership releases the lock after all
terminal paths without a stale lock cleanup procedure. A controlled concurrent
attempt must fail before Docker access while the owner completes and tears down
normally; exact-source evidence restarts only after that proof is committed.

## Analysis cycle 80 — hosted bare-health route guard

Candidate `f3765c6fd9a3dad7fd088a27595d7bd56bbf1333` passed both complete
gates, the fresh-volume browser/concurrency proof, exact 10+10 repetitions, and
every hosted functional, integration, browser, audit, SBOM, and security job.
Both duplicated repository guard jobs correctly rejected the synthetic support
application's bare `/health` decorator because the guard scans all `api` source
and reserves that spelling against accidental public product exposure. The
synthetic process was loopback-only and test-only, but bypassing or weakening
the global guard would create an ambiguous future exception.

B470-B472 preserve the global guard and rename the no-schema readiness route to
the explicit `/synthetic-health` path. Compose health admission, hosted polling,
the fixed WSL runner, and boundary tests consume that exact name; tests also
prove the synthetic process exposes neither bare `/health` nor product
`/api/health`. All otherwise-green evidence for `f3765c6` remains rejected and
must restart from the replacement commit, including both hosted guard jobs.

## Analysis cycle 81 — pure-Python coverage tracer corruption

The first complete gate for candidate `ef3b1a8d914075ea4ce9c98bd2c5d260d18c971f`
passed 240 DigitalOcean tests before Coverage.py's pure-Python `PyTracer`
corrupted its internal `should_trace_cache` state during partition 5 and raised
`TypeError: FileDisposition object is not iterable` from an ordinary `pathlib`
comparison. The prior C tracer had already produced rare interpreter-state
corruption, so retrying either implementation would make nondeterminism part of
the release contract. The gate retained the failure and did not run coverage
admission.

B473-B475 use Coverage.py's supported Python 3.12 `sys.monitoring` core for only
the isolated DigitalOcean coverage partitions. The formerly failing four-file
partition passed 33 tests under that core without warnings. The partitioning,
source boundary, parallel data files, combine/report steps, failure propagation,
and coverage floor remain unchanged. Exact-source release evidence restarts only
after the complete coverage runner and its contract tests pass on a new commit.

## Analysis cycle 82 — exact repetition native interpreter crash

The fresh-stack proof for candidate `84acb69d88013ca0c4763194afd9f47e6eaf39e0`
passed, but privacy/runtime repetition 10 terminated with native `SIGSEGV` while
Pydantic Settings executed ordinary Python environment parsing. The runner
correctly retained a bounded source-bound failure manifest and stopped before
either complete gate. This is the same WSL/Python native-instability class for
which narrower repository runners already use a three-attempt native-only
policy, but the exact-head runner lacked both deterministic allocator settings
and bounded recovery.

B476-B479 add fixed `PYTHONHASHSEED=0` and `PYTHONMALLOC=malloc` values to the
credential-free allowlisted child environment. Only `-11`, `134`, and `139`
receive up to three attempts; each failed attempt is persisted before retry and
referenced by the successful integrity-bound manifest. All assertion failures,
timeouts, source drift, permission or hash changes, and third native failures
remain terminal. Exact-source evidence restarts from a new commit.

## Analysis cycle 83 — disposable migration container native crash

Candidate `5fbf27d5ae2a07398ed3d880af5e710d8c9c88b9` passed the fresh-stack
proof, all 20 exact repetitions without recovery, and its first complete gate.
The second gate then passed every workspace, API-role, worker-role, and media RLS
assertion before a disposable Django migration process exited `139`. The runner
removed its synthetic PostgreSQL container and the gate retained the failure,
but seven downstream checks correctly remained unrun. A transaction-safe target
migration is idempotent; the surrounding role and SQL assertions are not retry
eligible.

B480-B483 add fixed allocator/hash settings to only the disposable migration
process and a three-attempt native-only wrapper around only its target migration
commands. Exit `1`, assertion checks, role probes, PostgreSQL checks, startup,
and teardown remain single-shot. Unit tests cover recovery, exhaustion, ordinary
failure, and fixed call-site scope; the full disposable acceptance and all exact
evidence must restart on a new commit.

## Analysis cycle 84 — Django coverage native crashes

Candidate `ec7b2ba654782fba82eac4efdc24e947626bdee7` passed fresh-stack and
repetition evidence plus its first complete gate. The second gate's Django lane
then crashed twice: first during migration-state rendering and again inside the
Coverage.py C tracer's report parser. The gate's one retry retained both traces
and failed closed, preventing seven downstream results from being inferred.
This is runtime instrumentation instability, not a Django assertion failure.

B484-B487 move the fixed Django coverage command to the already proven Python
3.12 `sys.monitoring` core, add deterministic allocator/hash settings, and bound
only native exits to three attempts inside the isolated wrapper. Partial JSON is
removed before retry; exit `1` and every ordinary test/configuration failure are
immediately terminal. Coverage starts the interpreter before pytest-django can
import application settings, avoiding a late-start measurement gap. Unit tests
and a real 96-test coverage run precede another
complete exact-source restart.

## Analysis cycle 85 — recovery-collateral replay and repository environment

Independent review of candidate `c2ef83145a584796388bd329089eb5e12295bd20`
found two medium assurance gaps. A passed repetition manifest bound recovered
native failures only by pathname and did not revalidate those sibling failure
receipts during replay. Separately, the documented `.venv` repository-test
command relied on PyYAML, jsonschema, and Pillow without declaring them in its
hash-locked requirements; after those imports were installed, the complete
repository suite also exposed two stale contract assertions.

B488-B492 replace recovery strings with exact path-and-manifest-digest records
and require every referenced receipt and log to remain private, contained,
nonsymlinked, structurally valid, digest/hash/size bound, exact-source bound,
and limited to a fixed suite attempt with a recognized native exit. Replay
regressions cover deletion, tamper, symlink, traversal, wrong commit, invalid
exit, and valid reuse. The repository environment now directly pins all three
collection-time imports, while the stale profile assertion includes the
supported media module and lease fencing asserts database-time plus the opaque
lease token. The documented repository command passes 391 tests and 81
subtests. All exact-source evidence restarts from a new commit.

## Analysis cycle 86 — long-lived Django interpreter corruption

The first complete gate for candidate
`32239023586e86053508d83433abaa917e799053` failed closed after 95 Django
tests when migration model construction received an impossible `ModelBase`
object in place of a dictionary item tuple. Because the process returned exit
`1`, the native-only retry boundary correctly treated it as terminal. The
formerly failing migration module then passed twenty independent fresh-process
runs, identifying accumulated interpreter state as the unsafe boundary rather
than an assertion eligible for retry.

B493-B496 execute each of the 21 exact Django test modules in a separate
deterministic `sys.monitoring` coverage process. Every partition remains a
fixed ordinary-failure boundary; only native exits receive bounded recovery.
Parallel coverage data is combined with retained inputs so a native combine
failure is retry-safe, then partition residue is removed after the JSON report
is written. The partitioned run completed all 96 tests, reproduced the exact
56.18826263800116 percent line coverage total, emitted no tracer warning or
retry, and left no parallel data file. Exact-source evidence restarts again
from the replacement commit.

## Analysis cycle 87 — focused Django checks retained unstable coverage

The first complete gate for candidate
`b8d7b87bddb53b3f4b1c9fab7e6f3ba2d018eaf1` reached a focused Django
site-content check that still inherited pytest-cov from `django/pytest.ini`.
Before any test body ran, its C tracer corrupted a cloned `CharField` and the
process exited `1`; the gate correctly failed immediately. The new partitioned
Django coverage lane was not involved, revealing duplicate legacy
instrumentation in four focused contract checks.

B497-B500 give every focused Django check explicit empty pytest addopts and
disable the coverage plugin. Coverage remains mandatory once, in the dedicated
21-process all-module lane, so this removes unstable duplicate instrumentation
without reducing measured scope or thresholds. The gate-manifest contract
binds all four commands, and the formerly failing eight-test site-content
module passed twenty fresh-process repetitions without a retry. Exact-source
evidence restarts from another replacement commit.

## Analysis cycle 88 — failed parallel coverage shard contamination

Independent operations review of candidate
`b25d78fed06e1b63013b7da087dff50d3a1f1ee8` found that a failed per-module
Django coverage attempt could leave its partial parallel data shard beside
successful shards. Removing only the JSON report was insufficient: a later
successful retry could cause `coverage combine` to admit measurements from the
failed attempt and overstate or corrupt the final evidence.

B501-B504 snapshot the fixed shard namespace immediately before each module
attempt and remove every shard newly created by a nonzero attempt before either
native retry or ordinary terminal propagation. Unexpected symlink shards are
unlinked without following their target and then fail closed; other invalid
types also fail closed. Tests cover native recovery, ordinary failure, symlink
target preservation, and successful-shard retention. A real partitioned run
must again pass all 96 tests at the unchanged coverage result with no residual
parallel shard before exact-source evidence restarts from a new commit.

## Analysis cycle 89 — complete-gate ownership and successful shard admission

The first complete-gate attempt for candidate
`78cb81f0e7ade8df8964fb462e64f2fe214a264d` overlapped an unintended second
invocation. Both processes shared fixed API and DigitalOcean coverage
directories and visual port 4174. The retained failed receipt
`20260910T011611Z` records vanished coverage directories and a visual port
collision. Two later serialized gates passed 109/109, proving serial behavior
but also demonstrating that the complete gate lacked single-owner admission.

Operations review also found that cycle 88 validated shards only following a
nonzero subprocess exit. A subprocess returning zero could therefore leave a
symlink, directory, unsafe-mode file, empty or oversized file, or unexpected
shard count for later combination.

B505-B512 add a restrictive nonblocking repository lock before source or child
work. A contender starts zero checks, returns a distinct busy exit, and writes
only a run-unique digest-bound busy receipt outside active release evidence;
normal and exceptional owner exits release the kernel lock. Successful Django
partitions must create exactly one contained regular nonempty bounded shard,
which is normalized to mode 0600. The entire exact shard set and cardinality is
revalidated immediately before combination. Owner/contender and adversarial
shard tests plus a real 96-test coverage run precede another new exact-source
candidate and complete evidence restart.

## Analysis cycle 90 — concurrency proof self-contention

The first fresh-stack concurrency proof after candidate
`39d1dd540784fd4ba9530512657d6206a3c63bcd` failed before Docker access. Its
owner reported the fixed project lock already in use, while the lock was free
immediately after proof cleanup. The proof's readiness loop used repeated
nonblocking acquisitions of the same lock; one probe could win the startup race
and cause the owner it was observing to fail.

B513-B516 replace that self-contentious observation with a fixed readiness
marker written by the runner only after it owns the lock and removed by its
cleanup trap. The proof first performs one pre-launch availability check so it
cannot remove a real owner's marker, then watches the marker without touching
the lock. Policy tests forbid the former polling pattern. The real proof must
show owner success, contender exit 3, and empty exact-project inventory before
another exact-source evidence restart.
