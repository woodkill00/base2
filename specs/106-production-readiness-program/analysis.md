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
