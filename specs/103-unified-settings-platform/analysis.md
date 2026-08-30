# Analysis Log

## Cycle 1 - Initial product and architecture review

Findings:

1. A generic settings JSON endpoint would create an unsafe and unversioned mutation surface.
2. Base2 already has profile, MFA, session, privacy-operation, organization, and audit foundations; duplicating them would introduce drift.
3. A universal settings page would expose irrelevant controls in generated sites.
4. Existing visual assurance emphasizes public pages and does not prove authenticated settings states.
5. “100% tested” cannot honestly mean all unknowable future defects.

Corrections:

- Required typed entities, closed schemas, explicit versions, and optimistic concurrency.
- Required integration of existing contracts rather than replacement.
- Added manifest-driven capabilities and negative API admission tests.
- Added authenticated state and rendering matrices with explicit review sidecars.
- Defined completeness as 100% requirement/task/test/evidence traceability plus regression coverage for every discovered defect.

Open findings: migration parity, ownership context, notification mandatory semantics, and detailed visual-state cost require deeper review.

## Cycle 2 - Security and privacy review

Findings:

1. Existing unrestricted avatar URLs permit privacy leaks when clients load third-party resources.
2. Reauthentication can expire between rendering a confirmation and submitting it.
3. Recovery codes and personal identifiers could enter screenshots or artifacts.
4. Cross-tenant not-found behavior and stale-version mutation need direct negative tests.
5. Deactivation and deletion have different recoverability and cannot share one ambiguous action.

Corrections:

- Added safe URL parsing, no backend dereference, and future first-party media guidance.
- Required server-side recent-auth validation at mutation time.
- Added secret and personal-data artifact scans plus synthetic fixtures.
- Added cross-owner, cross-tenant, replay, and conflict tests.
- Split deactivation and deletion with distinct consequence and confirmation contracts.

Open findings: dependency outages, worker deferral, capability changes during navigation, and accessibility state announcements remain.

## Cycle 3 - Reliability, accessibility, and visual review

Findings:

1. A successful UI toast can lie if an optimistic save fails or a second device changed the version.
2. Screenshot comparisons alone do not prove keyboard, touch, focus, announcements, or overflow behavior.
3. Running the full cross-product visual matrix on each tiny change is wasteful.
4. Capability changes during an active route could strand a user on an unauthorized page.
5. Privacy-worker downtime must preserve durable queued state rather than silently fail.

Corrections:

- Required visible rollback and typed conflict refresh.
- Added behavioral geometry/accessibility assertions alongside images.
- Split representative pull-request coverage from the expanded release matrix.
- Required route revalidation and safe overview fallback on capability changes.
- Reused durable privacy operations with explicit deferred state and recovery tests.

**Current result**: `NO_UNRESOLVED_SPEC_OR_TASK_FINDINGS`

Implementation must now proceed in ordered tasks, followed by an implemented-system analysis cycle.

## Cycle 4 - Implemented-system and visual analysis

The first integrated unit and browser passes found eight reproducible defects:

1. Embedding `AccountCenter` through a render-local wrapper remounted the entire subtree on every state update, resetting MFA enrollment.
2. The prior standalone account test expected a heading that the remount made inaccessible.
3. Settings tests completed while asynchronous capability state was still updating, emitting uncontained React updates.
4. The authenticated header logo and theme controls were smaller than the required interactive target on compact screens.
5. Generated Northstar and Ember profile logo paths pointed to absent SVG assets.
6. Fixed-only background composition produced a white seam below one viewport in full-page compact and short-landscape captures.
7. The authenticated shell inherited low-contrast dark text in dark mode.
8. New settings cards skipped from the page `h1` to `h3`, violating heading order; the authenticated footer was also an empty visual block.

Corrective tasks were added to the implementation work, and each defect now has a regression assertion or screenshot baseline. The second browser pass covered all nine settings routes, three representative viewport shapes, axe, horizontal overflow, target geometry, deep-link convergence, mandatory notification semantics, and destructive confirmation with zero findings.

**Current implemented-system result**: `NO_UNRESOLVED_FOCUSED_OR_VISUAL_FINDINGS`. Complete-repository and publication gates remain later ordered tasks and are not implied by this result.

## Cycle 5 - Complete-gate and migration-execution analysis

The first complete-gate and closeout audit found four additional defects:

1. Settings API SQL files existed, but migrations `008` and `009` were absent from the executable runner list.
2. The public-contract command used Vitest's default fork pool instead of Base2's bounded single-worker thread policy.
3. Async public interaction tests emitted React `act` warnings even though assertions passed.
4. The incomplete-output classifier treated any `Error` text as a terminal result, including the intentional error-boundary fixture, and therefore did not retry a genuinely truncated process.

Corrections:

- Made the runner inventory an exported ordered tuple and added an equality regression against every checked-in SQL file.
- Added direct reversible Django migration-operation proof.
- Standardized the public contract on one thread worker and repaired async interaction boundaries.
- Replaced keyword guessing with terminal-summary detection, explicit worker/SIGSEGV signatures, and tests proving ordinary assertions are never retried.

## Cycle 6 - Host runtime and visual release analysis

Repeated Node and Chromium exits were confirmed by the WSL kernel as real signal-11 faults. They occurred under Node 24.13.1 and 24.20.0, with no OOM event and more than 30 GiB available memory. Runtime inspection found WSL explicitly constrained to one processor on a 14900HX host.

Corrections:

- SHA-256 verified and installed current Node 24.20.0 LTS within the declared Node 24 policy.
- Aligned active NVM, Docker, CI, setup, environment-example, and operator documentation pins to 24.20.0.
- Increased the workstation WSL allocation from one to eight processors and restarted WSL; repository state remained intact.
- Added a complete-gate preflight that fails immediately with the exact `.wslconfig` remedy when WSL exposes fewer than two processors.
- Added a narrowly matched API-coverage retry for the observed impossible Python stdlib `re` compiler corruption; ordinary application exceptions and assertion failures remain non-retryable, and repeated corruption still fails closed.
- Replayed the full frontend coverage suite, 24-test visual release matrix, settings state matrix, 10-project settings release matrix, and 79-check complete repository gate successfully without a retry.

**Final local implemented-system result**: `NO_UNRESOLVED_LOCAL_IMPLEMENTATION_OR_VISUAL_FINDINGS`. Publication, merge, and separately approved live-provider acceptance remain distinct phases.

## Cycle 7 - Exact-commit visual interaction analysis

The exact-commit visual harness exposed one intermittent desktop behavior: the descend control selected the next arbitrary geometric snap stop and then inferred a semantic section, so the visible active marker could remain `home` instead of advancing to `features`.

Correction:

- Movement controls now traverse the declared semantic section order directly and synchronize the active-section ref before geometry alignment begins.
- Obsolete geometric stop-selection code was removed.
- The five focused component tests passed, and the exact desktop movement journey passed ten consecutive Playwright repetitions.

**Cycle result**: `NO_UNRESOLVED_MOVEMENT_OR_VISUAL_INTERACTION_FINDINGS`.

## Cycle 8 - Changed-line coverage and V8 worker analysis

The post-movement exact gate correctly rejected 88.89% changed-line coverage against the required 90% floor. A subsequent direct coverage attempt also produced another kernel-confirmed V8 worker fault.

Corrections:

- Added user-visible regression tests for stale preference conflicts, successful export plus failed correction, and failed profile saves with preserved form state.
- Changed-line coverage increased to 93.47%; the settings service reached 100% line/function/branch coverage in the full frontend report.
- Standardized every Vitest entrypoint on one worker with V8 concurrent recompilation and concurrent marking disabled. WebAssembly, normal JavaScript execution, browser engines, and production build behavior remain enabled and unchanged.
- The full frontend coverage suite completed under the stabilized command.

**Cycle result**: `NO_UNRESOLVED_COVERAGE_OR_VITEST_WORKER_FINDINGS`.

## Cycle 9 - Publication lint and interpreter-fault analysis

The first publication CI run found five API-test lint violations that the feature-focused
and complete gates did not report: four semicolon-compressed fixture statements and one
SIM300 assertion ordering issue. After those deterministic findings were corrected, the
next exact-commit complete gate failed closed when the Python standard-library JSON encoder
entered an impossible internal state (`_indent=None` while executing the indented-output
branch). The same module checkpoint had passed in the prior exact gate, and a separate
DigitalOcean coverage process recovered from a native interpreter crash in the same run.

Corrections:

- Reformatted the worker fixtures, corrected the assertion order, and reproduced the exact
  GitHub Ruff command successfully in a fresh Python 3.12 container.
- Added an exact three-part JSON-encoder corruption signature to the complete gate's existing
  one-retry infrastructure boundary.
- Added regression proof that the exact impossible stdlib state receives one bounded retry,
  while application `TypeError` output and ordinary assertions remain non-retryable.
- Kept the gate fail-closed after the single retry and retained retry count plus diagnostic in
  integrity-bound evidence.

Closure evidence:

- Exact feature head `0431f253c7c641599141b33ccb35f4921a0033ba` passed all 79 complete-gate
  checks with zero failures and zero retries.
- Every pull-request workflow passed, including API, Django, backend integration, frontend,
  E2E, smoke, contract, performance, repository guards, supply-chain, secret, license, SBOM,
  Semgrep, and Storybook/Chromatic checks.
- PR #29 merged that exact reviewed head into `main` as
  `bb29bc0964431c0d8b84dcad22984633586343cf`; every post-merge workflow passed and local
  `main` matched `origin/main` with a clean worktree.

**Cycle result**: `NO_UNRESOLVED_PUBLICATION_OR_RUNTIME_CLASSIFICATION_FINDINGS`.
Live provider acceptance remains a separately admitted phase.

## Cycle 10 - Live canary process-argument secret analysis

The first bounded staging-certificate canary reached `live-verified`, but a read-only
runtime diagnostic found that Flower received its generated Redis broker credential in
an explicit `--broker` command-line argument. Although the credential was ephemeral and
the exact-owned droplet and DNS records were immediately destroyed, process arguments
are an unnecessarily broad disclosure surface and the canary was rejected rather than
accepted.

Corrections:

- Removed the broker URL from Flower's command and retained it only in the established
  `CELERY_BROKER_URL` environment contract supported by Celery/Flower.
- Added a compose-contract regression requiring the broker environment entry while
  forbidding `REDIS_PASSWORD`, `redis://`, and `--broker` in Flower argv.
- Required the replacement canary to use a newly generated ephemeral Redis credential
  and to report only a sanitized pass/fail result when checking runtime argv.
- Required exact teardown replay and zero exact-owned provider inventory before any live
  task can be closed.

**Cycle result**: `CORRECTIVE_IMPLEMENTATION_COMPLETE_LIVE_REPLAY_PENDING`.

## Cycle 11 - Live settings-journey coverage analysis

The replacement canary proved all existing public and operator routes were available, but
analysis of the executable live-browser suite found that it did not exercise the Feature
103 authenticated settings experience. Passing that suite alone therefore could not close
T086. The first expanded live journey then found that the shared browser API client omitted
the required tenant header, so settings and identity reads failed visibly and a valid
appearance save returned `tenant_required`.

Corrections:

- Added a live-only ephemeral account journey that visits all nine settings areas and
  records full-page visual evidence for each.
- Added live axe checks, horizontal-overflow checks, compact-viewport target geometry,
  settings search, persisted appearance changes, mandatory security-notification
  protection, and destructive-confirmation behavior.
- Bound the shared browser API client to the generated immutable site-profile tenant on
  every request, overriding request-supplied drift, and added a focused interceptor
  regression.
- Required every live settings route to render with zero alerts before accessibility or
  visual evidence can pass.
- Kept the account and all mutations inside the exact-owned ephemeral canary database;
  teardown remains mandatory and no production identity is used.

**Cycle result**: `CORRECTIVE_LIVE_JOURNEY_IMPLEMENTED_VALIDATION_PENDING`.

## Cycle 12 - Live migration-admission analysis

The exact-main canary carried the corrected tenant header, but the expanded live journey
then isolated HTTP 500 responses from preferences and notifications. The deployment path
started healthy containers without applying the API-owned SQL migration ledger, so generic
health was green while Feature 103 tables were absent.

Corrections:

- Added API migration application as an explicit named remote-bootstrap stage after
  Compose startup and before service inventory, route verification, or a live receipt.
- Kept the operation fixed-argv and inside the ephemeral API container with its existing
  private database environment; no credential values are passed on the command line or
  emitted.
- Added a deployment-contract regression proving migration execution is ordered before
  acceptance.
- Added secret-free live HTTP failure evidence containing only method, path, and status so
  future partial schema failures identify themselves without exposing identities, bodies,
  tokens, or credentials.

**Cycle result**: `CORRECTIVE_MIGRATION_BOOTSTRAP_IMPLEMENTED_LIVE_REPLAY_PENDING`.

## Cycle 13 - Live tenant-transaction and privacy-worker analysis

The exact-main replay proved automatic admission of all nine API migrations and passed
the existing public, operator, Django, pgAdmin, settings, accessibility, responsive, and
visual paths until the newly added privacy-worker exercise. The export request returned
HTTP 500 before dispatch because `create_operation` bound PostgreSQL's transaction-local
tenant context and then attempted to change `autocommit` inside that active transaction.
The same unsafe pattern existed in two older tenant-scoped content/scheduling write paths.

Corrections:

- Kept every tenant-scoped write in the transaction that owns its RLS tenant binding and
  committed explicitly; no repository changes transaction mode after tenant admission.
- Added focused regressions for privacy-operation commit/replay, community-post commit,
  form submission, and scheduling reservation behavior.
- Extended the durable live settings journey to require an encrypted export to reach
  `completed` through Celery and require the preference update's redacted audit event to
  be visible through the owner projection.
- Added a read-only secret-free runtime verifier for the exact migration ledger, critical
  service health, completed export, and preference-audit counts.

**Cycle result**: `CORRECTIVE_TENANT_TRANSACTION_IMPLEMENTED_VALIDATION_PENDING`.

## Cycle 14 - Live privacy-worker secret-parity analysis

The transaction-corrected exact-main replay accepted and dispatched the encrypted export,
but the Celery worker failed it with the stable error `identity_encryption_unavailable`.
The API container received the generated ephemeral encryption key, while the worker that
must decrypt the queued request and sign the export receipt did not receive that key or
the receipt pepper.

Corrections:

- Added only `IDENTITY_ENCRYPTION_KEY` and `TOKEN_PEPPER` to the privacy worker's runtime
  environment and added the previously omitted receipt pepper to the API container.
- Kept both values environment-only and absent from worker command arguments and evidence.
- Applied the same least-secret contract to development, local, and isolated E2E Compose
  definitions so test and generated-site behavior cannot drift.
- Added a Compose regression requiring API/worker parity for these two exact bindings and
  proving neither is present in worker argv.

**Cycle result**: `CORRECTIVE_PRIVACY_WORKER_SECRET_PARITY_IMPLEMENTED_VALIDATION_PENDING`.

## Cycle 15 - Live worker completion assertion analysis

The secret-parity replay completed the export successfully, but the live test matcher
expected a literal space between the adjacent `export` and `completed` flex spans. DOM
`textContent` concatenates adjacent span text without inserting whitespace, so the received
semantic state was `exportcompleted` and the product had already succeeded.

Correction:

- Made the assertion accept zero or more whitespace characters between the separately
  rendered kind and status while retaining exact `export`/`completed` ordering.

**Cycle result**: `CORRECTIVE_LIVE_MATCHER_IMPLEMENTED_REPLAY_PENDING`.

## Cycle 16 - Live navigation-cancellation analysis

The corrected worker-completion assertion passed. A subsequent route transition reported
the already-rendered site-mark request through Playwright's `requestfailed` event because
the browser canceled it during navigation. There was no HTTP failure, console error, alert,
or missing visual asset.

Correction:

- Ignore only explicit browser `ERR_ABORTED` navigation cancellations in request-failure
  collection. DNS, TLS, connection, timeout, and all other request failures remain fatal,
  while every HTTP 4xx/5xx remains independently fatal through response collection.

**Cycle result**: `CORRECTIVE_NAVIGATION_CANCELLATION_IMPLEMENTED_REPLAY_PENDING`.

## Cycle 17 - Final exact-main live acceptance and zero-finding closeout

Exact-main run `base2-full-20260830-174011` deployed commit
`33b20810c643cdac69184d9125e2b8335fff2449` with staging certificates only. The
controller verified all eight routes and six DNS records with zero secret values emitted.

Final proof:

- All five unfiltered live browser suites passed, covering public Obsidian identity,
  responsive section geometry and scrolling, anonymous operator denial, owner operator
  access, Django and pgAdmin second logins, all nine settings routes, axe, search,
  persisted appearance, mandatory notification delivery, destructive confirmation,
  encrypted export completion, and redacted audit visibility.
- The independent read-only runtime verifier proved 9/9 automatic API migrations, 6/6
  critical services healthy, three completed exports, three preference audit events, and
  a secret-free Flower command with exactly one broker environment binding.
- Public and API live requests returned HTTP 200 in 0.2094s and 0.164358s respectively.
- The retained private browser evidence contains 56 PNG screenshots and 2 structured
  files; its aggregate SHA-256 is
  `0d48ad615622feb202066d7a32fa9e01b1f03d2e50b3e6e5b8f3a075b94b2cdf`.
- Exact teardown deleted one owned Droplet and six bound DNS records. Immediate replay
  returned the same terminal `destroyed` evidence, and independent provider inventory
  reported zero Droplets, zero managed DNS records, and zero mutation requests.

No unresolved specification, implementation, security, accessibility, visual, runtime,
worker, migration, evidence, teardown, or provider-inventory finding remains.

**Cycle result**: `ZERO_UNRESOLVED_FINDINGS_FEATURE_103_COMPLETE`.
