# Analysis Cycles: Feature 093

Analysis checks requirement coverage, task executability, dependency validity, test-first order, error visibility, security/authority, rollback, observability, documentation, and measurable acceptance. A cycle is complete only after findings are reflected in artifacts and rechecked.

## Cycle 17 - Tenant isolation and database defense truth

The identity checkpoint had explicit `site_id` predicates but no single tenant
contract for request validation, cache keys, job envelopes, pooled connection
state, or Django admin visibility. PostgreSQL RLS was also named without a safe
role-separation decision, which could have produced a false security claim.

- Added canonical tenant validation, tenant-owned cache/job namespaces,
  transaction-local database binding, and unconditional pooled-connection
  rollback/reset on success and failure.
- Required every site-content repository checkout and SQL query to carry the
  same tenant key; retained generic not-found and sanitized service failures.
- Added membership-scoped Django admin query/object controls and model-level
  cross-tenant search-document validation.
- Recorded RLS as `deferred` until provisioning supplies distinct migration and
  non-owner runtime roles. The gate cannot report RLS as active before the
  direct-query, pool-reuse, and migration-bypass PostgreSQL matrix passes.

**Result**: T074, T075, and T123 are resolved without claiming an unavailable
database control. Focused API and Django matrices pass; complete-gate validation
is required from the resulting commit.

## Cycle 18 - Identity realm and interactive-control gap

The React account/admin test-first slice exposed two gaps that the earlier API
contract tests did not prove. FastAPI public accounts use UUID identities in
`api_auth_users`, while Django administration uses its separate staff identity
realm; joining these realms by mutable email would be unsafe. The existing
session inventory also lacked an owner-bound endpoint for revoking exactly one
session, and several planned controls had no complete server action contract.

- Added T134 to codify public-account versus operator-CMS realm separation,
  tenant ownership, and hostile cross-token rejection without email joins.
- Added T135 for the complete tenant-owned administration action surface before
  T077 may claim functional UI completion.
- Added an exact owner-bound active-session revoke operation with generic
  not-found behavior and append-only redacted audit evidence.
- Added the React account/admin test matrix and initial manifest/private-route,
  MFA capability, session, admin inventory, bounded-error, and accessibility
  surfaces. T076 is complete; T077 remains open until T135 actions and the
  browser/visual matrix prove that every exposed control works or is explicitly
  unavailable.

**Result**: No false completion claim is made for the identity/admin UI. The
focused API and React matrices pass, and the newly exposed architecture work is
ordered before data-rights and the US5 checkpoint.

T134 is now resolved with a required machine-readable realm contract. FastAPI
tokens yield only a UUID public principal even when hostile role, permission,
tenant, or organization claims are injected. Django rejects all public-account
API lookalikes, the public API does not accept Django identities, and mutable
email/name joins are explicitly forbidden. A future cross-realm mapping remains
a separately reviewed migration with proof-of-control and rollback requirements.

## Cycle 1 - Scope decomposition

**Findings**:

1. “Universal website” was unbounded and could not be accepted.
2. Visual work lived on a dangerously stale branch.
3. Deployment reliability, cost control, core site behavior, modules, and factory work were mixed together.
4. “100% testing” could be misrepresented as line coverage.
5. Live provider/payment/public actions lacked a fresh authority boundary.

**Corrections**:

- Defined 10 independent stories, 58 requirements, 12 representative packs, extension contracts, and explicit non-goals.
- Made current main the only base and documented patch-level visual porting.
- Ordered truth/deployment blockers before experience, identity, modules, operations, and factory.
- Defined requirement/control/state/boundary evidence plus honest ratcheted coverage.
- Added separate approval boundaries to spec, plan, and tasks.

**Result**: Resolved; proceed to task-graph analysis.

## Cycle 2 - Task graph and failure modes

**Findings**:

1. T025 referenced malformed dependency IDs (`T19`, `T21`, `T22`, `T24`).
2. Site/module/lease contracts omitted policy fields required by FR-021/FR-041 and constrained DNS/cost evidence.
3. Threat modeling, license provenance, resource exhaustion, outbound email, browser compatibility, edge headers, database defense, capacity, and generated-repository governance were implicit rather than executable.

**Corrections**:

- Corrected dependency IDs and validated the graph for missing tasks and cycles.
- Expanded all four contracts with strict policy, lifecycle, cost, DNS, and evidence fields.
- Added T115-T126 with specific tests, outputs, dependencies, and acceptance evidence.

**Result**: Resolved; automated analysis advanced to one open finding in this document.

## Cycle 3 - Cost safety versus data safety

**Findings**:

1. Idle teardown was cost-safe but did not explicitly classify persistent preview state or bind snapshot verification to deletion and recreation.

**Corrections**:

- Added T127-T128 for state classification, encrypted verified preservation, retention, destructive-transition denial, and destroy/recreate validation.
- Bound the generated child trial to state preservation as well as zero billable resources.

**Result**: Resolved.

## Cycle 4 - Final consistency pass

**Checks**:

- 58/58 requirements traced to implementation and failure-oriented evidence.
- Task IDs unique; every dependency exists; dependency graph acyclic.
- Test tasks precede implementations and user stories retain independent checkpoints.
- Deployment, credential, DNS, payment, destructive, publication, and production actions have explicit boundaries.
- Error, interruption, replay, rollback, resource exhaustion, tenant isolation, privacy, and state preservation are explicit.
- Contracts parse as strict JSON and match the planned semantic surface.
- No unresolved clarification markers, template placeholders, or open analysis findings remain.

**Result**: Resolved; zero planning findings.

## Cycle 5 - Visual source history correction

**Findings**:

1. The initial branch-count assumption was wrong: the visual branch is not one unique commit behind main. It is 231 commits ahead of exact current main, although its final tip changes one CSS file.
2. The net branch delta includes a nonvisual deployment bootstrap mutation with soft-failure and destructive checkout behavior.
3. Several visual components contain mock operational data or no-op actions that cannot be ported as finished capability.

**Corrections**:

- Corrected research and baseline evidence to the exact merge base, ahead count, 17-file delta, and line counts.
- Added `visual-port-map.md` covering every changed file and explicitly excluding the deployment mutation.
- Bound visual porting to manifest/content/action contracts, component decomposition, honest operational labeling, and deterministic tests.

**Result**: Resolved; zero remaining planning findings after revalidation.

## Cycle 7 - Clean WSL bootstrap

**Findings**:

1. WSL had no Linux Node binary and resolved `npm` to a Windows shim despite the repository's pinned Node/npm requirements.
2. After installing the exact Linux toolchain, the supported first-start flow failed because tracked Bash helpers lacked executable mode while being invoked directly.

**Corrections**:

- Installed and SHA-256-verified official Linux Node 24.13.1 user-locally, then updated npm to the required 11.10.0.
- Added T129 to make the clean-clone executable boundary and exact toolchain an enforced regression rather than a workstation-only repair.

**Result**: Resolved. The fallback/mode regression passes, supported first-start completes, and all applicable WSL environment tests pass.

## Cycle 6 - Current route and control inventory

**Findings**:

1. The authenticated/public route set contains no catch-all, exposes `/items` despite placeholder service behavior, and has duplicated/dead OAuth surfaces.
2. E2E support routes can return full message bodies and require a production-exclusion test in addition to a runtime key.
3. The dashboard, contact form, hero, footer, projects, and several navigation actions visibly imply behavior that does not exist.

**Corrections**:

- Added `experience-inventory.md` with route, control, data-source, state, and disposition ledgers.
- Expanded T023-T024 to prove E2E-only route exclusion and typed route startup behavior.
- Expanded T072-T073 to select one OAuth contract and remove dead 501 duplicates.
- Bound T060-T069 to automated reconciliation with zero unexplained controls.

**Result**: Resolved; zero remaining planning findings after revalidation.

## Cycle 8 - Complete-gate Python isolation

**Findings**:

1. API and Django pin incompatible transitive versions, so the legacy aggregate `requirements-dev.txt` cannot create one deterministic test environment.
2. The initial gate manifest embedded POSIX virtual-environment paths and pointed Django at the root pytest configuration, bypassing pytest-django initialization.
3. WSL Python package installation can terminate with signal 11 despite ample memory; accepting the partial environment would create a silent bootstrap failure.

**Corrections**:

- Added T130 and split service dependencies into `.venv-api`, `.venv-django`, and orchestration `.venv` while preserving explicit single-target installation flags.
- Added platform-resolved interpreter tokens to the no-shell gate runner and corrected Django to its service-owned pytest configuration.
- Added bounded one-retry installation, mandatory `pip check`, and tests for platform interpreter resolution. A repeated failure remains terminal and visible.

**Result**: Resolved in implementation; final task completion remains evidence-gated on the full first-start and complete-gate rerun.

## Cycle 9 - Exact-commit replay defects

**Findings**:

1. The first exact-commit gate failed after the pre-commit formatter aligned Markdown table columns because traceability parsing assumed one literal space around requirement IDs.
2. A recovered legacy CRA dependency installation omitted the transitive `react-refresh` peer, allowing unit tests to pass while the production build failed.

**Corrections**:

- Made traceability parsing whitespace-tolerant and added a formatter-aligned regression fixture.
- Declared the exact compatible `react-refresh` build dependency directly; the optimized production build now succeeds rather than relying on a transitive peer accident.

**Result**: Resolved; the next complete-gate receipt must bind the repaired exact commit.

## Cycle 10 - Clean-checkout Compose validation

**Findings**:

1. Docker and Compose were installed and healthy, but the gate invoked Compose without an interpolation environment.
2. The production Compose file also referenced private `.env` directly, preventing safe validation from a clean checkout.

**Corrections**:

- Parameterized only the Compose `env_file` path while retaining `.env` as the runtime default.
- Added a no-shell validator that supplies the repository-owned, non-secret `.env.example` for both interpolation and service configuration.
- Kept personal `.env` files ignored and out of gate evidence.

**Result**: Resolved in implementation; exact-commit complete-gate replay remains required.

## Cycle 11 - Coverage-scope truth

**Findings**:

1. The frontend's 100% label covered only a selected glass/theme subset; whole React runtime coverage is materially lower.
2. API totals included test modules, Django measured only `project`, root tooling lacked a policy artifact, and DigitalOcean had no coverage plugin.
3. A single global percentage would conceal these incompatible scopes.

**Corrections**:

- Added six separately labeled measured surfaces with test inclusion, scope, exclusions, baseline metrics, and non-inflated floors.
- Retained the 100% critical glass/theme contract while separately recording the whole React baseline.
- Added strict changed-line and expiring owner-approved exception contracts; there are currently zero exceptions.
- Added regression tests rejecting duplicate, unmeasured, inflated, expired, or ownerless policy state and proving test-module exclusion.

**Result**: T016 resolved. T017 remains responsible for producing and enforcing every machine-readable report in the complete gate.

## Cycle 12 - WSL signal-11 containment

**Findings**:

1. The current exact-commit gate saw Django terminated by kernel signal 11 while all other checks passed; prior bootstrap runs observed the same host signal in unrelated Python and Node processes.
2. Treating this as an application assertion failure obscures the host fault, while unbounded generic retries could hide real defects.

**Corrections**:

- Added one runner-level retry only for subprocess return code `-11`.
- Recorded attempt count and separated attempt output in integrity-bound evidence.
- Ordinary failures, timeouts, and a repeated signal remain terminal without additional retries.

**Result**: Contained, not declared eliminated; WSL/kernel stability remains a host risk and every recovery is visible in the gate receipt.

## Cycle 13 - Coverage enforcement integration

**Checks**:

- Root Node tests emit LCOV and enforce line/branch/function floors.
- React emits whole-runtime and critical glass/theme Istanbul reports; the critical subset retains 100% lines/functions/statements and 99% branches.
- API, Django, and supported DigitalOcean runtime emit Coverage.py JSON with test and experimental scopes explicitly excluded.
- The gate evaluates each labeled surface independently and enforces 90% changed executable lines from the fixed `main` merge base.
- Missing reports, missing metrics, floor regressions, changed-line regressions, and non-executable-only changes have deterministic fixtures.

**Result**: T017 resolved with six passing surfaces and 100% (34/34) measured changed executable lines; no coverage exception exists.

## Cycle 14 - CI policy baseline

**Findings**:

1. Five security jobs use `continue-on-error`, eight commands suppress failure, and action references use mutable tags.
2. Diagnostic cleanup and security enforcement were not distinguished by machine policy.
3. Required pull-request workflows and job IDs had no fixed repository-owned map.

**Corrections**:

- Added a required workflow/job map covering nine pull-request workflows and their required jobs.
- Added fixtures for pinned/blocking success, job omission, mutable actions, forbidden suppression, and the narrowly marked diagnostic-cleanup case.
- Frozen the pre-T019 repository baseline at 41 explicit findings so repair cannot silently omit a class.

**Result**: T018 resolved. The repository policy intentionally remains red until T019 removes all 41 findings and adds the validator to the required gate.

## Cycle 15 - Blocking immutable CI

**Corrections**:

- Resolved nine upstream action tags to exact 40-character commits and pinned every action in every workflow, including manual chaos/load workflows.
- Pinned PostgreSQL and Redis service images to verified registry digests.
- Removed all security-job `continue-on-error`, scanner suppression, and Grype `fail-build: false`; high-severity findings now block.
- Retained only five explicitly marked diagnostic cleanup/log-capture suppressions that run during failure handling and cannot turn a failed test green.
- Updated security jobs to Node 24.13.1 and isolated incompatible API/Django license environments.
- Added the zero-finding CI policy validator to the required complete gate; monthly grouped Dependabot updates remain the controlled update path.

**Result**: T019 resolved; all six policy fixtures and the full workflow scan pass with zero findings.

## Cycle 16 - Dependency severity authority

**Corrections**:

- Defined blocking critical/high policy with zero allowed exceptions and 0/72-hour remediation deadlines.
- Defined 30/90-day moderate/low remediation and a maximum 30-day owner-approved exception lifecycle.
- Required exact package/advisory, accountable owner, rationale, mitigation, approver, review, and expiry fields.
- Added deterministic rejection for malformed severity rules and high, expired, overdue, ownerless, duplicated, or overlong exceptions.
- Added the zero-exception policy validator to the complete gate and mirrored the machine contract in `docs/SECURITY_POLICY.md`.

**Result**: T020 resolved; five policy regressions pass and there are zero active exceptions.

## Cycle 17 - Legacy CRA removal

**Findings**:

1. `react-scripts` concealed the ESLint preset, jsdom, JSX-in-`.js` transform, Jest globals, and Istanbul setup behind one vulnerable dependency tree.
2. Storybook's retained version supports Vite 6 but not Vite 8, so selecting the newest Vite release would break an existing visual contract.
3. The runner migration initially changed Istanbul statement accounting by 0.23 points and fell below the independent 52% floor.

**Corrections**:

- Selected Vite 6.4, Vitest 4, the Vite React plugin, explicit jsdom, and Storybook's Vite framework from declared compatibility evidence.
- Preserved `build/`, public `REACT_APP_*` inputs, all Istanbul output paths, Docker serving, and the complete-gate interface while removing CRA, Webpack Storybook, patch-package, and stale Jest flags.
- Converted hoisted mocks to Vitest, retained a test-only Jest namespace bridge for non-hoisted APIs, and added explicit legacy JSX/Babel/TypeScript transforms.
- Kept the coverage floor unchanged and covered two previously untested explicit legacy route surfaces; whole-frontend statements now pass at 52.10% and critical glass/theme remains 100% statements/lines/functions.
- Upgraded the OpenAPI generator to remove the final high advisory. Full audit now reports five moderate and zero high/critical findings; production audit contains no high/critical findings.

**Result**: T021 resolved. Lint, 46 suites/86 tests, Vite production build, Storybook build, six coverage surfaces, and the high/critical audit gate pass.

## Cycle 18 - Security result normalization

**Findings**:

1. Existing security jobs retained CycloneDX, SARIF, npm-audit, and pip-audit files with incompatible result shapes and no common source-commit or raw-digest binding.
2. Gitleaks explicitly disabled artifact upload, so a passing/failing job had no owner-retained machine-readable result.
3. Image, DAST, provenance, and IaC scans require later task-owned activation inputs; treating them as currently green would be false evidence.

**Corrections**:

- Added one strict normalized result contract and adapters for secret, SAST, dependency, SBOM, provenance, image, DAST, and IaC families.
- Bound every normalized result to exact source commit and SHA-256 of the raw artifact, rejected malformed/inconsistent counts, and failed closed on critical, high, or unknown severity.
- Added 12 fixtures covering a red or malformed result for every family, green integrity binding, policy completeness, normalized-count consistency, and required CI workflow wiring.
- Retained raw plus normalized outputs for Syft/Grype, npm audit, both pip audits, Gitleaks, and Semgrep. The local complete gate now blocks on the adapter contract tests.
- Kept image, DAST, provenance, and IaC activation explicit rather than claiming scans without a trusted image, isolated target, generated output, or enabled policy.

**Result**: T022 resolved. The real frontend npm audit normalized to five moderate, zero high/critical/unknown, and an integrity-bound passing result.

## Cycle 19 - API startup and readiness contracts

**Findings**:

1. Required middleware, error handlers, OpenAPI generation, and route imports were wrapped in broad exception suppression, so an incomplete API could report a successful process start.
2. The health endpoint returned `ok: true` even when its only database probe failed; schema, Redis, Celery, and startup-component state were absent.
3. Production settings did not reject E2E support mode, invalid flag sources were silently replaced with an empty response, and enabled telemetry failures disappeared without evidence.
4. The first red-test process encountered the independently tracked WSL Python signal-11 fault during FastAPI schema import; lightweight startup primitives were therefore tested separately before application integration.

**Corrections**:

- Added a typed startup registry that terminates required-component failures and records optional-component degradation without exposing exception messages or secrets.
- Made CORS, request/tenant middleware, error handlers, routes, test-support routes, and complete OpenAPI generation explicit registered startup components. The schema is eagerly generated only after every route is installed.
- Added redacted readiness for database connectivity, Django-owned schema presence, Redis, optional-or-required Celery, and the startup component snapshot. The API performs no migration operation at boot.
- Rejected production E2E mode, removed development settings fallback, made invalid flag sources return the generic server error contract, and moved enabled telemetry failure handling to the visible optional-component boundary.
- Added 18 startup cases covering terminal/degraded initialization, the full readiness matrix, probe redaction, migration exclusion, schema probes, both telemetry exporter paths, production support-route exclusion, and flag failure; retained focused OpenAPI, health, and settings-failure logging checks.

**Result**: T023-T024 resolved. Ruff passes, focused validation passes 21/21, and the full API suite passes all 64 applicable tests with eight explicitly environment-dependent skips (72 collected). The first exact gate retained its signal-11 failure; the next run reached coverage and correctly rejected 85.48% changed-line coverage before the missing schema/telemetry tests were added.

## Cycle 20 - Threat boundaries and response ownership

**Findings**:

1. Security requirements named many controls but did not provide one reviewable STRIDE/privacy/abuse ledger spanning public, tenant, admin, module, factory, and provider boundaries.
2. Detection and prevention existed in separate tasks without a mandatory response path, accountable owner, or executable test linkage per boundary.

**Corrections**:

- Added the six-boundary threat model with principals/assets, multiple misuse cases, prevention, detection, response, owner, and exact test tasks.
- Made fail-closed authority, untrusted-data handling, zero-unapproved-mutation, sanitized evidence, and separate live activation explicit global rules.
- Added five mutation tests for missing, blank, duplicate, unknown, untested, and policy-incomplete ledger content and made the policy a required complete-gate node.

**Result**: T115 resolved. The live model passes with all six trust boundaries and every injected omission fails.

## Cycle 21 - Supply-chain admission

**Findings**:

1. Node and Python license jobs used different inline allowlists; the Python script skipped missing reports and accepted missing license values.
2. A permissive license could not independently block a known-forbidden package.
3. Generated-artifact and source-provenance requirements lacked one strict admission contract, including a verified-signature requirement.

**Corrections**:

- Added one versioned policy and validator for Node/Python licenses, exact forbidden packages, generated-artifact identity/digests, SLSA v1 subject binding, builder/build type, and verification identity/signature digest.
- Replaced both CI license allowlists with the shared validator and retained each raw inventory beside its machine-readable policy result.
- Added a blocking supply-chain workflow and complete-gate node plus eight fixtures covering allowed dual licenses, unknown/missing licenses, forbidden Node/Python packages, valid provenance, tampering, unsigned output, and incomplete policy.

**Result**: T116 resolved. All 13 combined threat/supply-chain policy tests, live policy validators, CI policy validation, workflow YAML parsing, and Feature 093 analysis pass.

## Cycle 22 - Portable React runtime image

**Findings**:

1. The React Dockerfile generated its site configuration with Dockerfile heredoc syntax, which is not portable to the supported classic frontend.
2. Both Nginx configuration files were embedded in Dockerfile shell commands, preventing direct review and route-fallback contract testing.
3. The current WSL user cannot access the Docker daemon and has no Buildx plugin, so claiming a local image build would be false; the repository can still enforce frontend syntax/config contracts and Compose interpolation independently.

**Corrections**:

- Added checked-in main and site Nginx configuration, copied with portable Dockerfile `COPY` instructions.
- Preserved non-root worker behavior, port 8080, SPA history fallback, static-asset 404 behavior, immutable cache policy, and existing security headers.
- Added three required-gate fixtures covering classic and BuildKit frontend compatibility, checked configuration content, and fallback-before-static routing order.

**Result**: T026-T027 resolved. The intentional pre-implementation run failed on both builder contracts and absent files; the corrected 3/3 suite and production Compose configuration validation pass.

## Cycle 23 - Service readiness contracts

**Findings**:

1. React's Compose probe called `curl` although its runtime image installs only `wget`.
2. Django ran a configuration check rather than probing its serving process and database; its internal DB health view returned HTTP 200 even when the database failed.
3. Static Nginx had no healthcheck, Flower called absent `wget`, and API readiness required Redis without waiting for Redis health.
4. Docker daemon access is denied to the current WSL user, so the required production-like all-container healthy acceptance cannot yet be claimed.

**Corrections**:

- Added a four-case service health contract covering every runtime service, installed probe binaries, meaningful endpoints/dependencies, and Traefik ping support; the original matrix failed six defects.
- Switched React to installed `wget`, made Django probe `/internal/health`, made DB failure return redacted HTTP 503, added static Nginx and Python-native Flower probes, and added Redis as an API healthy dependency.
- Added two Django readiness tests and made the service-health contract a required complete-gate node.

**Result**: T028 resolved and the T029 implementation is present. The corrected 4/4 contract, 2/2 Django readiness cases, and production Compose configuration validation pass. T029 remains open until all built containers can be observed healthy through an accessible Docker daemon.

## Cycle 24 - ACME storage bootstrap

**Findings**:

1. Three startup/deployment paths independently created ACME files with shell commands and suppressed ownership/mode failures.
2. A directory replaced by a file, an ACME file replaced by a directory or symlink, wrong ownership, and idempotent content preservation had no focused contract.
3. The PowerShell/Bash paths could drift because filesystem mutation was duplicated rather than delegated.

**Corrections**:

- Added one Python implementation using no-follow file creation, fixed filenames, exact directory/file modes, exact UID/GID, post-change verification, content preservation, and redacted receipts.
- Added thin Bash and PowerShell wrappers; local start, post-reboot convergence, the primary Python orchestrator upload set, and the legacy remote deployment block route to the same implementation.
- Added nine cases for absent storage, file/dir/symlink conflicts, wrong ownership metadata, wrong modes, content preservation, idempotency, live Bash delegation, and static PowerShell delegation; made them a required complete-gate node.

**Result**: T030 resolved and the T031 implementation is present. All 9 focused and 36 DigitalOcean tests, shell syntax/parity, and command-matrix checks pass. T031 remains open until accessible Docker acceptance observes Traefik running with UID 1000 and both ACME files at mode 0600.

## Cycle 25 - Staging-only certificate activation boundary

**Findings**:

1. Although staging was the documented default, the static configuration still defined a live resolver and omitted its `caServer`, which makes Traefik default to the production ACME endpoint.
2. A production-shaped `ENV` made both the entrypoint and deployment script select the live resolver, while remote validation expected that behavior.
3. The smoke test rejected staging issuers in a production-shaped test, directly conflicting with the owner requirement that Traefik remain test-only.

**Corrections**:

- Removed the live resolver and all live storage selection from Traefik's static configuration; the sole resolver uses the exact Let's Encrypt staging endpoint and isolated staging storage.
- Made the entrypoint reject any non-staging resolver, made deployment always normalize to `le-staging`, and made remote/smoke validation require staging regardless of the application environment name.
- Added a required repository policy gate and hostile fixtures for the live endpoint, resolver, storage, and entrypoint override. This is static/offline validation and performs no ACME request.
- Recorded live certificate issuance as a separately approved future activation that Feature 093 cannot enable.

**Result**: The policy validator reports `mode=staging-only`; all 13 ACME policy/bootstrap cases pass. No Traefik process was started and no certificate request was made.

## Cycle 26 - Single strict deployment configuration

**Findings**:

1. Provider preflight read only ambient process variables while orchestration independently used both `load_dotenv` and `dotenv_values`.
2. Duplicate and unknown provider keys, malformed identities, quoting/CRLF differences, and unresolved templates could therefore be interpreted differently at different deployment stages.
3. Configuration failures lacked a focused assurance that secret values would not be echoed.

**Corrections**:

- Added one non-executing parser and normalizer for comments, quotes, whitespace, CRLF, strict keys, known DigitalOcean fields, templates, provider identities, and redacted diagnostics.
- Routed both preflight and the orchestrator through the same implementation; the orchestrator loads once before provider identity or client construction and no longer imports either dotenv parser.
- Added parser, preflight, integration, and secret-redaction cases, then made the contract a required complete-gate node.

**Result**: T032-T033 resolved. All 23 parser/preflight/env cases pass, and the combined focused ACME/config matrix passes 36/36.

## Cycle 27 - Integrity-bound preview leases

**Findings**:

1. The PreviewLease contract existed, but there was no durable implementation for exact replay, ownership, expiry, transition, or restart reconciliation.
2. No runtime boundary rejected traversal IDs, changed replays, hostile resource tags, malformed nested records, state tampering, or interrupted writes.
3. TTL renewal lacked a maximum extension and expired resources had no deterministic transition to teardown authority.

**Corrections**:

- Added a private lease store with strict contract validation, deterministic ownership tags, canonical SHA-256 envelopes, owner-only permissions, an exclusive lock, fsync, atomic replacement, and interruption cleanup.
- Implemented exact idempotent create replay, bounded state transitions, capped UTC renewal, and deterministic expired-lease reconciliation to `teardown_due` without provider mutation.
- Added 15 cases binding runtime fields to the reviewed schema and covering valid round trips, unchanged replay, conflicts, tampering/truncation, interrupted replacement, transitions, expiry, renewal, terminal state, resource ownership, hostile IDs, and modes.
- Added the lease suite as a required complete-gate node.

**Result**: T034-T035 resolved. The intentional absent-module run failed during collection; the implementation passes all 15 focused cases.

## Cycle 28 - Exact-owned teardown

**Findings**:

1. The legacy orchestrator instantiated a provider client at import, searched and deleted by mutable droplet name, and caught deletion failure while continuing to a misleading completion message.
2. Optional DNS cleanup deleted a broad fixed set of names without exact before-state or lease evidence.
3. There was no compare-before-delete identity/tag check, replacement-resource protection, bounded rate-limit behavior, or post-delete zero-resource proof.

**Corrections**:

- Replaced name-based deletion with an import-safe lease-bound command requiring exact provider, kind, immutable ID, and deterministic ownership tag before mutation.
- Added bounded retry for 429/5xx responses, bounded eventual zero-resource verification, idempotent already-absent/destroyed handling, and durable `destroying`/`destroyed` transitions.
- Disabled DNS deletion until the separate transactional DNS contract is implemented; leases containing DNS mutations fail closed in this path.
- Added seven provider-fake cases for exact deletion, wrong ID/tag, name replacement, missing/tampered receipts, residual resources, bounded rate limits, and idempotency, then made them a required gate node.

**Result**: T036-T037 resolved. The legacy import failed before tests because it eagerly created a real client; the corrected 7/7 teardown and combined 22/22 lease/teardown cases pass without provider access.

## Cycle 29 - Transactional DNS contract

**Findings**:

1. Preview DNS changes had no exact before-state transaction, partial-apply recovery, health gate, or reverse-order restoration primitive.
2. A stale or third-party-modified record could be overwritten, and certificate SAN evidence was not bound to the exact mutation names.
3. Lease DNS mutation state could not be advanced atomically with integrity verification.

**Corrections**:

- Added bounded DNS mutation transitions to the integrity-bound lease store.
- Added an offline provider-neutral transaction that preflights every exact prior/desired value before mutation, reconciles an interrupted remote apply, binds exact mutation names to the exact certificate SAN set, and verifies health before completion.
- Health failure restores exact prior values in reverse order; a third-party change during rollback fails closed rather than being overwritten.
- Added five transaction fixtures and a required gate node.

**Result**: T038 resolved and the core T039 transaction implementation is present. The intentional absent-module run failed during collection; the corrected DNS/lease/teardown matrix passes 27/27. T039 remains open until the primary deployment orchestrator uses this primitive through a provider adapter.

## Cycle 30 - Complete-gate resource contention

**Findings**:

1. The first exact gate passed, but the immediate second gate's frontend test exited `1` directly after the Vitest banner with no test result, assertion, stack, or coverage output.
2. An immediate isolated replay passed all 46 files and 86 tests, identifying host resource contention rather than a deterministic product/test failure.
3. Inspection of the runner proved checks were already sequential. The initial concurrency hypothesis was rejected before closeout rather than retained as an unsupported explanation.

**Corrections**:

- Preserved the failed receipt and did not classify it as green or weaken any test/coverage threshold.
- Replayed the exact frontend command independently; all 46 files and 86 tests passed, proving the empty gate exit was intermittent rather than a deterministic assertion failure.
- Kept both exact full gates required and left the failed receipt unchanged.

**Result**: The deterministic suite passes in isolation. A subsequent exact gate printed all API test progress but timed out during coverage finalization after 900 seconds, further identifying a bounded host-process failure. T025 remains open.

## Cycle 31 - Bounded infrastructure retry classification

**Findings**:

1. The runner retried only signal 11, while the same WSL instability also appeared as an incomplete test process exit and a post-test coverage-finalization timeout.
2. Retrying every nonzero result would hide real assertion, lint, audit, security, or policy failures.
3. The API timeout was 900 seconds despite an isolated exact run completing 53 passed/8 skipped in under two seconds.

**Corrections**:

- Added an optional, manifest-validated maximum of two attempts for only `timeout` and `incomplete-test-output`; signal 11 retains its existing single bounded retry.
- Enabled incomplete-output retry only for the frontend test and timeout retry only for API coverage. Output containing test pass/fail/error markers is never classified as incomplete.
- Reduced the API timeout to a conservative 120 seconds, limiting a pathological two-attempt run to four minutes, and retained each attempt in the redacted evidence log.
- Added runner tests proving timeout recovery, incomplete-output recovery, ordinary failure non-retry, and assertion-failure non-retry.

**Result**: All 11 gate-runner cases pass. No product threshold or failure classification was weakened; recovered infrastructure attempts remain explicitly labeled in the signed result. Exact commit `45ad21b7d391997956c4be884f2bbac52c944cfb` then passed two consecutive complete gates (`20260824T204904Z`, `20260824T204926Z`) with every required check green and zero retries in either run. T025 is resolved.

## Cycle 32 - Terminal deployment evidence and cost receipts

**Findings**:

1. Lease, DNS, and teardown state did not provide one commit/manifest/run-bound terminal receipt spanning stages, costs, and admitted artifacts.
2. Console failures could omit a terminal stage result, and stored diagnostic structures had no recursive secret-key rejection.
3. Budget state could be internally inconsistent or a successful operation could exceed its approved ceiling.

**Corrections**:

- Added a strict deployment-evidence schema for deploy/update/rollback/teardown/reconcile/canary actions, terminal stages, explicit safe failure codes, cost ceilings/projected/actual totals, and digest/size-bound artifacts.
- Added an owner-only, locked, canonical SHA-256 evidence store using fsync and atomic replacement; changed replay and tampering fail closed.
- Added recursive secret-key rejection, exact nested-field validation, budget consistency/admission, and terminal success/failure lifecycle methods.
- Added an orchestration adapter and integrated it into provider-neutral DNS and exact-owned teardown entrypoints so every invoked operation stage becomes terminal and cost-accounted.
- Added the combined evidence/DNS/teardown matrix as a required complete-gate node.

**Result**: T040-T041 resolved. The intentional absent-module run failed at collection; the implementation passes all 28 combined cases, including five independently injected failure stages, secret fixtures, integrity tampering, DNS success evidence, and teardown success evidence. T039 remains open only for replacement of the legacy deploy script's broad DNS path.

## Cycle 33 - TTL and idle cleanup controller

**Findings**:

1. Preview leases had an absolute expiry but no explicit activity/idle deadline or unattended cleanup controller.
2. Concurrent sweepers could duplicate teardown attempts, while unbounded retries or raw exception notifications could increase cost and leak provider details.
3. A healthy no-active/no-due state had no explicit tested no-op result.

**Corrections**:

- Extended the lease contract with paired optional `lastActivityAt`/`idleExpiresAt` fields and added an atomic activity-touch operation; malformed partial/negative windows fail closed.
- Reconciliation now chooses the earliest absolute or idle deadline and transitions only eligible leases to `teardown_due`.
- Added a nonblocking owner-only sweeper lock, fixed three-attempt retry with bounded backoff, exact lease-ID teardown callback, and one sanitized exhaustion notification with no exception text.
- Added no-lease, active-lease, absolute expiry, idle expiry, transient recovery, retry exhaustion, and overlapping-run coverage; made the suite a required gate node.

**Result**: T043 resolved. All 6 focused sweeper and 31 combined lease/sweeper cases pass without provider access or live mutation.

## Cycle 34 - Lease-bound preview orchestration and DNS restoration

**Findings**:

1. The DNS primitive was not yet composed with provision, bootstrap, health, evidence, teardown, interruption resume, or exact replay.
2. A resumed lease was incorrectly re-created from its original payload, conflicting with durable resource state added after provisioning.
3. Failure cleanup could not restore planned/applied/verified DNS mutations before exact resource deletion, so safe teardown failed closed but leaked the resource.
4. The DNS transaction used a placeholder health result instead of the exact provisioned resource, and evidence/ownership tampering needed end-to-end hostile coverage.

**Corrections**:

- Added a provider-neutral preview orchestrator for admission, exact-owned provision, bootstrap, transactional DNS, health, update, rollback, interruption resume, and terminal evidence.
- Existing leases and evidence are now loaded through their integrity-checked stores; exact successful replay makes no provider call, while changed or tampered state fails closed.
- Added exact DNS restoration for planned/applied/verified mutations. It restores only exact desired values, accepts already-restored prior values, refuses third-party drift, and completes before exact resource deletion.
- Bound DNS health to the exact provider resource and reject provision responses lacking the deterministic ownership tag before lease admission.
- Added the lifecycle/DNS matrix as a required complete-gate node.

**Result**: T039 resolved. Fourteen DNS transaction/orchestration cases and the combined 55-case lease, DNS, teardown, and lifecycle matrix pass without credentials or provider access. T042 implementation is substantially present but remains open behind T029/T031 runtime observations and final provider-fake admission/fault coverage.

## Cycle 35 - Provider admission, circuit breaking, and durable notification

**Findings**:

1. Provider creation could begin despite a local resource ceiling, provider quota, budget overflow, low disk/memory, or current OOM evidence.
2. Provider throttling and transient failures lacked one cross-operation retry-storm boundary; simultaneous cooldown probes could amplify recovery load.
3. A notification marked deduplicated before successful delivery could be permanently lost when its delivery adapter failed.
4. Cleanup must remain available during pressure and circuit incidents or safety controls could cause billed-resource leaks.

**Corrections**:

- Added immutable policy/snapshot contracts and fail-before-call admission for local resource, provider quota, budget, disk, memory, and OOM conditions.
- Added exact retry classification for 429/5xx only, fixed maximum attempts/delays, integrity-bound owner-only circuit state, cooldown, and a single half-open probe.
- Added atomic pending-notification state. Delivery failure remains queued across restart, delivered incidents deduplicate, and circuit recovery produces a distinct sanitized notice.
- Routed preview admission, create, bootstrap, DNS, health, and update provider operations through the controller. Exact DNS/resource cleanup deliberately bypasses admission so it can always reduce resource usage.
- Added the combined admission/orchestration matrix as a required complete-gate node.

**Result**: T117-T118 resolved. Fourteen focused quota/budget/pressure/OOM/rate-limit/retry/circuit/notification/integrity/concurrency cases and nine end-to-end provider-fake lifecycle cases pass. Exhaustion performs no excess provider mutation, half-open permits one probe, notification adapter failure is durable, and cleanup remains exact and available.

## Cycle 36 - Preview state preservation authority

**Findings**:

1. Lease teardown treated all preview data as equivalent, so state requiring retention, snapshot, encryption, or later restoration had no fail-closed classification boundary.
2. Missing keys, corrupt/interrupted evidence, expired snapshots, and mismatched lease identities had no stable denial contract.
3. Retention expiry and restore-required state were not represented in a strict machine-readable contract.

**Corrections**:

- Added strict declaration and snapshot-receipt schema definitions for ephemeral, retained, snapshot-before-destroy, and restore-required state.
- Added a providerless preservation authority with exact fields, safe IDs, Vaultwarden reference-only keys, timezone-aware timestamps, encrypted snapshot digest/size/verification/retention checks, and stable denial codes.
- Retained state blocks before its declared expiry; preserved state blocks on missing/mismatched keys, missing/corrupt/interrupted/unencrypted/expired evidence, lease mismatch, or future verification time.
- Added the 14-case preservation matrix as a required complete-gate node.

**Result**: T127 resolved. All 14 classification, retention, evidence, encryption, identity, integrity, and hostile-field cases pass. T128 remains separately responsible for integrating this authority with snapshot creation, teardown, restore, and recreation; no provider or destructive action was performed.

## Cycle 37 - Real Compose health and staging-only Traefik observation

**Findings**:

1. A root-created, newly absent ACME file skipped the ownership/mode contract because a Boolean expression short-circuited the normalization call.
2. The static Nginx health probe resolved `localhost` to IPv6 while Nginx listened on IPv4, leaving a working service incorrectly unhealthy.
3. The first disposable pgAdmin fixture was not a syntactically valid email address; the corrected reserved domain was also rejected by pgAdmin's stricter validator.
4. An externally interrupted observer could leave its isolated Compose project holding ports 80/443, and the final staging assertion initially inspected the template path rather than Traefik's rendered runtime path.

**Corrections**:

- Always apply the ACME identity contract after file creation and added a regression proving every new path is normalized.
- Bound the static Nginx probe to `127.0.0.1:8081` and added an explicit IPv6-ambiguity regression.
- Generate a non-secret, accepted `fixture@example.com` only inside the disposable canary environment.
- Added signal-specific cleanup, idempotent teardown, pending-service diagnostics, and assertions against `/tmp/traefik.yml`, the actual rendered configuration.
- Ran the complete real Compose stack under a unique project and removed its volumes, network, containers, and temporary environment after observation.

**Result**: T029 and T031 resolved. All 12 services reached healthy state. The rendered Traefik configuration contained only the Let's Encrypt staging endpoint and `acme-staging.json`; storage was mode `0600`, uid/gid `1000:1000`. Post-run Docker inventory was empty. No DigitalOcean resource, public DNS record, production credential, or live certificate endpoint was used.

## Cycle 38 - Required providerless lifecycle canary

**Findings**:

1. The lifecycle matrix proved individual paths but the required gate had no one-shot deploy/replay/update/rollback acceptance receipt.
2. A CI canary must not inherit provider credentials, contact a provider, mutate public DNS, or exercise certificate issuance.
3. Live-canary approval needed an explicit separation from ordinary local and providerless validation.

**Corrections**:

- Added a deterministic in-memory provider canary using the production lease, evidence, admission, DNS transaction, teardown, and preview orchestration implementations.
- The canary verifies first deploy, exact no-call replay, update, rollback, exact prior DNS restoration, destroyed lease state, and zero residual fixture resources.
- Added tests that make socket creation fail, remove provider-token variables, and assert the machine-readable zero-authority receipt.
- Made the canary a required complete-gate node and documented that any live run needs new exact commit/manifest/provider/DNS/resource/cost/lease/trial authority.

**Result**: T042 and T044 resolved. The combined provider-fake matrix passes 88 cases, and the standalone canary reports zero network requests, credential reads, external provider mutations, public DNS mutations, production certificate requests, or residual resources. T045 remains deliberately open and no live DigitalOcean action was performed.

## Cycle 39 - WSL DigitalOcean coverage tracer stability

**Findings**:

1. The exact-commit complete gate failed because the DigitalOcean coverage process segfaulted twice during pytest collection; its ordinary 88-case focused matrix remained green.
2. The host had 30 GiB available memory and 943 GiB free disk, excluding resource exhaustion as the immediate cause.
3. Coverage's pure-Python tracer avoided the segfault but failed inside Python 3.12 typing imports and warned that trace data was unreliable.
4. Coverage's supported Python 3.12 `sys.monitoring` core completed the unchanged tests and report successfully.

**Corrections**:

- Added one fixed portable wrapper that selects `COVERAGE_CORE=sysmon` and replaces itself with the exact existing pytest/coverage command.
- Routed only the DigitalOcean coverage gate through that wrapper; test selection, coverage source, report path, required status, and coverage policy remain unchanged.
- Added manifest/wrapper regressions so the stable tracer cannot silently drift back to the crashing core.

**Result**: The DigitalOcean suite passes 162 tests with a valid JSON coverage report under `sys.monitoring`. Strict malformed-evidence and invalid-source-identity cases raised changed-line coverage from 89.06% to 91.15% against the unchanged 90% floor. No retry, test exclusion, threshold reduction, or unavailable classification was used. The complete gate must be replayed before this cycle is closed.

## Cycle 40 - Redacted live-canary approval preflight

**Findings**:

1. The Base2 checkout had no local `.env`, while the operator's ignored Base2 environment and the Pi's private resolved profile were present.
2. The live task lacked a deterministic way to show the exact non-secret scope before credential or provider authority was granted.
3. The stored profile currently selects `s-4vcpu-8gb` and legacy image `docker-20-04`; neither should be silently treated as the intended smallest modern canary.
4. The legacy deployment path proposes a broad hostname set, while the acceptance canary needs only one exact temporary record.

**Corrections**:

- Added a networkless redacted preflight that parses the ignored environment as data, resolves bounded templates, rejects symlinks/unsafe targets/reserved domains/non-exact commits, and emits no secret value.
- The plan binds commit, safe plan digest, project/region/size/image, one commit-derived A record and certificate SAN, three sequential trials, one maximum concurrent droplet, 15-minute leases, a USD 1.00 total ceiling, and staging-only certificates.
- Added six tests with sockets disabled, secret non-disclosure, exact output, hostile target rejection, symlink rejection, and machine-readable CLI coverage; made the contract required in the complete gate.

**Result**: The first approved read-only preflight performed zero network requests and emitted zero secret values. It produced exact DNS candidate `f093-6d8e4ecd.woodkilldev.com` and plan digest `a80e62d1c226633a839abf4051b3c24a49c617629c609eec3b145a7d3ff0700f`. No provider or DNS mutation occurred. A new exact-commit plan and separately approved provider-read validation remain required before T045 can run.

## Cycle 41 - Stable coverage tracing across Python services

**Findings**:

1. After the DigitalOcean coverage repair, the next exact gate passed all 168 DigitalOcean tests but the FastAPI coverage process aborted in native memory cleanup with signal 6 and no assertion result.
2. Kernel evidence recorded the abort despite 30 GiB available memory; it also contained an unrelated Python/libapt segfault, confirming broader WSL native-process instability rather than application pressure.
3. The unchanged FastAPI suite passed immediately under Python 3.12's `sys.monitoring` coverage core.

**Corrections**:

- Added fixed FastAPI and Django coverage wrappers matching the already-proven DigitalOcean wrapper.
- All three Python coverage surfaces now replace themselves with their unchanged pytest selections, sources, report paths, and thresholds after selecting `COVERAGE_CORE=sysmon`.
- Added manifest and wrapper drift tests for all three isolated interpreters.

**Result**: The unchanged FastAPI matrix passes under the stable tracer with a valid JSON report. No retry, exclusion, skip, or coverage-policy reduction was introduced. The exact complete gate must still be replayed.

## Cycle 42 - Live-canary admission fail-closed finding

**Findings**:

1. The approved exact plan named one temporary DNS record and one certificate name, but the ordinary Traefik dynamic template declares several additional subdomain SANs. Starting that template would exceed the reviewed mutation/certificate set even though issuance is staging-only.
2. The provider-neutral preview lifecycle has only provider fakes and an exact-owned teardown adapter; it has no bounded live adapter implementing provision, exact-source bootstrap, health, transactional single-record DNS, and inventory under one contract.
3. The legacy live deployment path broadly edits root, `www`, administrative, monitoring, and wildcard-adjacent records and therefore cannot safely satisfy the exact Feature 093 plan.
4. The approved plan was correctly stopped before its first mutation. Credential validation and six GET-only inventory requests succeeded, with zero matching DNS records or Droplets and one matching existing SSH key.

**Corrections**:

- Added explicit T131-T133 test-first work for a hostile live-adapter matrix, bounded DigitalOcean adapter, exact-source bootstrap, and one-host staging-only Traefik canary surface.
- Bound T045 to those corrections so evidence cannot mark the live acceptance complete using the broad legacy deployer or an ad hoc operator command.
- Retained the exact clean-inventory discovery as read-only evidence; the superseded mutation approval cannot transfer to a corrected source commit or changed plan digest.
- Implemented a dependency-free, fixed-host DigitalOcean client with exact owned-resource reconciliation, bounded waits, transactional one-record DNS, compare-before-delete teardown, and sanitized receipts.
- Added a fixed-argv SSH/SCP bootstrap that verifies the exact archive digest remotely, installs the canary at one fixed path, and runs only the registered bootstrap and health commands.
- Added an explicit Traefik canary template containing only the approved hostname, staging ACME storage/endpoint assertions, private generated environment handling, and a three-trial exact-plan runner.
- Bound the initially unknown Droplet address only after exact resource identity is persisted; existing providerless flows remain unchanged when DNS values are already known.

**Result**: T131-T133 pass. The DigitalOcean suite passes 184 tests, the focused canary/feature matrix passes 12 tests, and the real local Compose canary reached 12/12 healthy services while verifying the exact single-host route and staging-only ACME configuration. Cleanup left no Compose project. No Droplet, DNS record, certificate request, project resource, repository remote, or billable resource was created. T045 remains open until the corrected implementation is committed, its deterministic archive and plan dry-run pass, and the new exact plan receives separate approval.

## Cycle 43 - Exact-commit coverage and WSL native-process replay

**Findings**:

1. The first exact-commit replay passed every functional node but measured changed-line coverage at 87.96%, below the unchanged 90% floor.
2. The same replay exposed the known WSL native-process instability as an `npm audit` allocator abort; a following Python collection attempt also segfaulted with ample host memory.
3. The production dependency audit itself reports only two moderate React Router advisories, below the fixed high-severity failure threshold; it does not authorize a breaking major-version upgrade.

**Corrections**:

- Added direct dependency-free HTTP adapter tests covering every fixed Droplet and Domain operation, request-path/method rejection, HTTP failure redaction, and connection cleanup.
- Added hostile live-boundary tests for every exact config dimension, private input permissions, ownership tags, invalid DNS addresses, bounded readiness exhaustion, health failure, and non-404 provider errors.
- Terminated and restarted only the Ubuntu WSL VM after the native crashes, then replayed the unchanged test and audit commands without weakening or retrying around an assertion failure.

**Result**: The DigitalOcean matrix now passes 196 tests and changed-line coverage is 90.34% against the unchanged 90% floor. The production audit completes normally with zero high/critical findings. No Pi, provider, DNS, certificate, repository remote, or billable resource was mutated.

## Cycle 44 - Backward wall-clock correction

**Findings**:

1. A clean exact-gate replay observed WSL time move backward between a canary receipt's start and finish timestamps.
2. The integrity validator correctly rejected the impossible timestamp ordering, but a real NTP correction could otherwise interrupt cleanup and strand a preview.

**Corrections**:

- Wrapped the live canary's injected wall clock in a nondecreasing observer and routed admission, orchestration, lease, deploy, and rollback evidence through that single view.
- Added a deterministic regression that advances and then reverses wall time during all three canary trials while requiring successful teardown, empty DNS, and zero provider resources.

**Result**: The focused regression passes, the full DigitalOcean matrix passes 197 tests, and changed-line coverage is 90.43% against the unchanged 90% floor. Evidence ordering and cleanup remain valid across a backward wall-clock correction.

## Cycle 45 - Pi stdlib-only live-run import

**Findings**:

1. The exact archive and plan transferred to the Pi with the approved archive digest, but the Pi-side dry-run stopped before provider access because the shared teardown module imported optional legacy `pydo` at module load.
2. The live canary supplies its own dependency-free provider and never exercises the legacy standalone teardown CLI, so importing `pydo` for that path improperly broadened the runtime dependency.

**Corrections**:

- Made `pydo` optional at shared-library import and retained a fail-closed, explicit error only when the legacy standalone teardown CLI is invoked without it.
- Added CLI-unavailable coverage and a subprocess regression that imports the complete live canary with Python `-S`, proving the path works with only the standard library.

**Result**: The focused matrix passes 18 tests, the DigitalOcean matrix passes 199 tests, and changed-line coverage remains above policy at 90.37%. The failed Pi dry-run made no provider request or mutation; its superseded archive will not be executed.

## Cycle 46 - Approved three-trial DigitalOcean acceptance

**Findings**:

1. Exact plan `7438b48e416db8283a49bcda7f630e7a0112da407cb511d9881f23b7ae0c1c93` passed both local and Pi networkless dry runs before live authority was used.
2. On each clean Droplet, pgAdmin briefly entered an unhealthy startup state while initialization continued, then recovered inside the fixed 240-second service window; the other eleven services converged normally.
3. Destroying every Droplet between trials intentionally removed all Docker/image cache, so each trial independently proved Ubuntu package bootstrap, exact archive verification, image construction, service health, staging-only Traefik, DNS, public health, and teardown.

**Corrections**:

- Ran the exact approved source commit `43c888eebabde3c1541ad27cbbed7a001585ee36` as a Pi user service so workstation or SSH loss could not interrupt the lifecycle.
- Required the existing fixed health contract to observe pgAdmin recovery; no service was excluded and no health threshold was weakened.
- Preserved all three lease/deploy/rollback receipts and the final result in an owner-only artifact directory, then performed a separate read-only provider/DNS inventory using the private runtime credential.

**Result**: All three trials passed. Droplets `594979819`, `594981694`, and `594983363` were each created sequentially, reached 12/12 service health, served the exact public API health route through staging-only Traefik, restored DNS, and reached terminal `destroyed`. Final receipt digest is `b54c53305ede82c780c4ea6e41cf85ef4de268b4f292652e08de39706ffa80c5`; deploy/rollback receipt digests are integrity-bound in that receipt. Independent API inventory found zero owned Droplets and zero exact DNS records. Estimated cost was 3 USD minor units against the approved 100-unit ceiling, and zero secret values were emitted. T045 is complete.

## Cycle 47 - Site-manifest contract and cross-language consumers

**Findings**:

1. The contract schema described the desired shape but had no executable semantic boundary for canonical domains, module compatibility, navigation exposure, locale fallback, safe local URLs, file provenance, or raw-secret rejection.
2. No shared consumer or fixture profiles existed, so service-specific configuration could silently interpret the same site differently.
3. Repository-wide TypeScript compilation currently includes unrelated legacy test typing failures; a focused strict compile is required for the new typed consumer until that broader debt is resolved in its ordered task.

**Corrections**:

- Added a dependency-free strict Python loader with exact-field checks, bounded real-file reads, canonical SHA-256, compatibility-catalog enforcement, capability dependencies, safe paths, locale/domain invariants, and recursive secret rejection.
- Added an independent Node consumer and a strict typed React consumer; golden tests require Python and Node to produce identical site identity and digest.
- Added Ember Studio and Northstar Library fixtures with distinct domains, brands, locales, modules, policies, and digests, plus a hostile nine-test matrix.
- Made the manifest contract a required complete-gate node with both Python and Node tool admission.

**Result**: T046-T048 complete. Both profiles validate and digest differently; the independent consumers agree exactly, the typed consumer compiles under focused strict TypeScript, and malformed or secret-bearing manifests fail closed. T049 remains open for Django/FastAPI/React/config integration and dual-brand builds.

## Cycle 48 - Integrity-bound service profile generation

**Findings**:

1. API, Django, and React images use separate build contexts, so directly reading the root manifest would either fail in containers or require broadening every context and its secret-exclusion boundary.
2. Merely finding a brand string in a minified bundle does not prove which profile the build selected because multiple public fixture manifests may be compiled into the same application.
3. A runtime-supplied unknown profile could otherwise become a path traversal or silent fallback, and independently copied profile files could drift or be tampered with.

**Corrections**:

- Added one atomic generator that validates canonical profiles, requires filename/site identity agreement, emits identical service-local copies, and binds every generated profile to a canonical SHA-256 index.
- Added API and Django runtime loaders that allow only indexed IDs, reject symlinks, verify exact identity and digest, fail closed on unknown/tampered input, and default compatibly to `ember-studio`.
- Threaded `SITE_PROFILE` through both Compose surfaces and worker processes, exposed only bounded public site metadata from FastAPI, and applied the selected locale, title, and site identity in React.
- Added a strict Vite selection plugin that rejects unknown profiles and emits explicit public `site-profile.json` plus an HTML site-ID marker; the required build verifier builds both fixture brands and proves distinct output from the same tree.

**Result**: T049 complete. Twelve manifest/runtime tests pass, API and Django resolve Northstar to the same canonical digest, focused API/Django/React regressions pass, and both Ember Studio and Northstar Library production builds are distinct and identify their exact selected profile. The generator `--check` mode and dual-build verifier are required complete-gate nodes; no secret, provider, DNS, certificate, or external mutation is involved.

## Cycle 49 - Generated profile formatter ownership

**Findings**:

1. The first exact-commit expanded gate failed because pre-commit's general JSON formatter rewrote all six generated profile copies after the generator had verified their exact bytes.
2. The integrity check failed closed and blocked the dependent dual-brand build check; all other required gate nodes passed.

**Corrections**:

- Declared all three generated profile directories formatter-exempt so the canonical generator is their sole byte-level owner.
- Regenerated every service-local profile from the validated canonical source and required `generate_site_profiles.py --check` before the replacement commit.

**Result**: The original failed result remains preserved under ignored gate evidence. The regenerated files match the generator exactly, and a new exact-commit complete gate is required; no validation threshold, profile contract, or required check was weakened.

## Cycle 50 - Visual contract before visual port

**Findings**:

1. Existing glass styles mix layout, palette, and component values without one strict source describing supported themes or required interaction states.
2. The visual branch inventory calls for volcanic/obsidian behavior, while the second fixture manifest requires a distinct polar theme; none had a machine-readable completeness contract.
3. Storybook covered individual component variants but did not prove the full default, hover, focus, disabled, error, selected, responsive-navigation, and modal-state inventory.

**Corrections**:

- Added a strict versioned design-system contract and schema covering semantic color, spacing, radius, motion, typography, breakpoints, volcanic/obsidian/polar themes, CSS variables, and exact required component states.
- Added semantic CSS tokens and manifest-selected theme activation without removing the existing compatibility aliases needed by current components.
- Added a Storybook visual-contract inventory containing every required state marker and a five-test gate that validates schema, exact theme completeness, CSS exposure, component raw-color exclusion, bounded motion, breakpoints, reduced motion, and story coverage.
- Made the visual contract a required gate dependency after both fixture brands build successfully.

**Result**: T050 complete. All five contract tests pass, strict TypeScript and ESLint pass for the inventory, and the Storybook production build succeeds. The upstream Storybook runtime reports its known build-time `eval` and bundle-size warnings; this tool-only output is not shipped in the application image and does not change the production CSP boundary addressed by T119.

## Cycle 51 - Reviewed visual port onto current components

**Findings**:

1. The stale visual branch mixes useful layout/contrast intent with hardcoded Base2 identity, an external decorative image, simulated operational claims, new no-op navigation surfaces, and an unrelated unsafe deployment-script delta.
2. Wholesale merging would bypass the manifest and current component behavior while importing 231 historical commits.
3. Current home tests intentionally preserve the public heading, CTA focus order, section inventory, and accessibility contract.

**Corrections**:

- Rebuilt the approved volcanic/obsidian composition on the current `HomeHero`, `HomeVisual`, `HomeFooter`, and `Home` tree using semantic theme tokens and responsive/reduced-motion rules.
- Bound hero identity, voice, theme, locales, operations profile, and module summary to the selected generated manifest; removed the remote Unsplash dependency and replaced it with deterministic local CSS presentation.
- Declined the stale simulated runtime/security panels, no-op navigation additions, hardcoded repository identity, and deployment changes.
- Added a required ancestry/current-component/semantic-style/no-false-claim gate proving the visual tip is not an ancestor and only reviewed current surfaces own the port.

**Result**: T051 complete. Four visual-port tests, five visual-contract tests, ESLint, and all four focused home keyboard/accessibility tests pass. The existing public heading and CTA focus behavior remain intact, and no stale branch history or external visual asset was merged.

## Cycle 52 - Hermetic browser capture boundary

**Findings**:

1. WSL initially held Chromium revision 1217 while the lockfile-resolved Playwright required revision 1208; after installing the exact browser, its declared Ubuntu native libraries were also absent.
2. The page's fixed animated menu control crossed the hero capture bounds and changed a small pixel region between otherwise identical captures.
3. Google OAuth attempted to request its remote client script during page startup, even though the visual harness must never depend on external network success.

**Corrections**:

- Added a dedicated single-worker Chromium harness fixed to locale `en-US`, UTC, 1280x900 at scale 1, dark color scheme, reduced motion, frozen time, local production build, no service workers, no server reuse, and local-only routing.
- Installed the repo-pinned browser revision and Playwright-declared Chromium OS dependencies in WSL; missing browser/runtime dependencies now fail the required harness visibly.
- Blocked every non-loopback request, asserted zero external response, removed filters/backdrop and transient animation from capture, settled motion state, and hid only the fixed out-of-scope menu toggle before capture.
- Added exact repeated PNG byte equality plus a static contract test that prevents removal of any frozen-input or local-only boundary.

**Result**: T052 complete. Both real-browser tests pass: repeated hero captures converge to byte-identical PNG output, and browser identity/time/theme/motion/network assertions match exactly. Two static harness-contract tests also pass. No external request completed, and no provider, DNS, Pi, or production service was touched.

## Cycle 53 - Identity/admin action and browser completion

**Findings**:

1. The identity schema and route skeleton did not provide complete MFA challenge, one-time recovery, exact session revocation, invitation, role, credential, or truthful passkey behavior.
2. Account/admin UI lacked manifest gating, permission-safe routing, and a real-browser interaction/layout gate.
3. Task identifiers T132/T133 were already assigned to DigitalOcean work; the first draft of the identity findings incorrectly reused them.

**Corrections**:

- Added encrypted TOTP enrollment, atomic recovery login, MFA enforcement for password and Google OAuth, non-recent refresh tokens, exact session revocation, tenant membership/RBAC actions, one-time credentials, and disabled-by-default owner bootstrap.
- Added account, admin, and invitation surfaces with manifest, authentication, and permission boundaries plus a hermetic Northstar browser matrix with local API fixtures and blocked external responses.
- Renumbered the new identity tasks to T134/T135 and updated dependencies and traceability without altering the existing DigitalOcean tasks.

**Result**: T135 and T077 complete. Focused API, repository, schema, React, accessibility, adapter, auth, production build, and three-case real-browser matrices pass. Screenshot encoding triggered the already observed WSL `SIGSEGV`; the required account gate uses deterministic rendered layout and interaction assertions without capture, while the independent visual harness continues to own screenshot evidence.

## Cycle 54 - Durable data-rights lifecycle

**Findings**:

1. Privacy routes returned placeholder success responses without durable work, receipts, retention, or status.
2. A broker outage could otherwise strand work silently, and retries could create duplicate active operations.
3. Export restoration had no explicit prohibition against a live target.

**Corrections**:

- Added API/Django parity migrations, encrypted durable operations, one-active-kind uniqueness, guarded claims/completion, explicit deferred dispatch, bounded periodic replay, and daily sensitive-material expiry.
- Added recent-reauthenticated export/correction/deletion requests, owner-only status/download, permission-gated tenant status, receipt-bound no-store downloads, exact correction/deletion limits, redacted audits, and generic failures.
- Restricted restore to integrity-checked isolated preview and added operator/security documentation plus required complete-gate nodes.

**Result**: T078 and T079 complete. Twenty-eight focused lifecycle, route, repository, worker, replay, retention, receipt, restore, and schema tests pass. A real PostgreSQL container migration remains unavailable in this WSL account because the Docker socket is not accessible and sudo requires the owner password; SQL and Django parity are verified, and T080 retains the live database acceptance requirement.

## Cycle 55 - Complete-gate browser and signal isolation

**Findings**:

1. The first exact `d87ea7c` gate let the existing compatibility browser and new account browser claim the same loopback port and concurrently rewrite the same Vite build directory.
2. WebKit mobile then observed missing locale state during that collision, while the account server failed its strict-port admission.
3. WSL terminated npm-wrapped ESLint with SIGSEGV exit 139, but the gate recognized only direct subprocess signal `-11` for its single bounded infrastructure retry.

**Corrections**:

- Assigned the account harness its own fixed port and serialized visual, compatibility, account, and frontend chains through explicit gate dependencies.
- Recognized both direct `-11` and shell-normalized `139` as the same bounded SIGSEGV infrastructure retry, with a regression proving exactly one recovery attempt and no conversion of persistent failure into success.

**Result**: The failed evidence remains preserved. Focused runner and browser replacement tests must pass before a new exact-commit complete gate; no test was removed, made optional, or given an unbounded retry.

## Cycle 56 - WSL Django assertion-rewrite isolation

**Findings**:

1. The replacement gate passed the browser collision point but the Django identity node received two native Python SIGSEGVs at unrelated interpreter locations: migration model rendering and pytest path collection.
2. The same 17-test command passes immediately and consistently with pytest assertion rewriting disabled, matching the earlier focused identity validation behavior on this WSL instance.

**Corrections**:

- Set only the affected Django identity gate to `--assert=plain`. Test discovery,
  database creation/migrations, assertions, coverage, required status, and the
  bounded retry policy remain unchanged; only pytest's bytecode-rewriting layer
  is bypassed.

**Result**: All 17 identity domain/no-public-admin tests pass with plain assertions. The second failed gate remains retained, and a new exact-commit gate is required. The persistent native WSL instability remains a host risk and is not classified as an application pass.

## Cycle 57 - Partitioned API coverage isolation

**Findings**:

1. After a clean WSL restart, the unchanged visual harness passed all six cases, proving the prior Rollup failure was transient host corruption.
2. The full API suite completed its assertions but aborted while the forced C tracer generated coverage; the pure-Python tracer also SIGSEGVed during collection. The shared factor is long-lived whole-suite tracing on this WSL runtime.
3. Retrying the same monolithic interpreter cannot isolate corrupted tracer state and consumed both bounded attempts.

**Corrections**:

- Replaced the monolithic API coverage process with an exact sorted test-file inventory partitioned into bounded groups of eight.
- Each partition runs the same marker exclusion and API source coverage in a fresh interpreter, retries only native abort/segfault exits once, discards failed fragments, and fails visibly on any ordinary test failure.
- Coverage data is combined only after every partition passes, then emitted to the same required `api.json` policy input. Unit tests bind ordering, exactly-once inventory flattening, and partition bounds.

**Result**: The third failed gate remains preserved. The partitioned runner must produce a valid complete API coverage artifact and pass the unchanged coverage policy before another exact-commit gate. No test, source package, marker, coverage threshold, or required node was removed.

## Cycle 58 - Partition retry and changed-line recovery

**Findings**:

1. Six isolated API partitions completed all 165 selected tests, including one transparently retained native-crash retry, but the first fresh coverage JSON process then received SIGSEGV.
2. Retrying that read-only report command in a fresh interpreter succeeded, proving combined data remained valid.
3. The first valid partitioned report exposed changed-line coverage at 89.2%, below the unchanged 90% policy, primarily because several new identity repository branches lacked direct tests.

**Corrections**:

- Applied the same one-retry native-crash boundary to coverage combine/report processes, retained raw fragments through combine, removed partial output before retry, and added ordinary-failure/no-retry regressions.
- Added direct repository coverage for authenticator lookup, challenge creation/consumption, recovery replacement, invitation acceptance, owner bootstrap, and unauthorized/stale role updates.
- Extended coverage evidence with per-file executable, covered, and missing changed lines so future shortfalls identify actionable locations instead of only a global percentage.

**Result**: All 165 API tests pass across six isolated coverage partitions, a valid combined report is produced, and the unchanged coverage policy passes at 90.12% changed lines. Identity repository coverage is 91%; the partition/retry and policy tests pass. Host SIGSEGV remains visible and bounded rather than silently ignored.

## Cycle 59 - Topological gate and smaller crash domains

**Findings**:

1. The fourth exact gate declared `account-admin-browser` before its newly added compatibility dependency. The runner used manifest order rather than a dependency order, so it incorrectly marked the valid later dependency as blocking before evaluating it.
2. One eight-file API partition encountered native corruption on both allowed attempts during the gate, despite the same complete partition inventory and coverage policy passing immediately beforehand.

**Corrections**:

- Added a stable topological scheduler after cycle validation, with a regression proving later-declared dependencies execute first and their consumer runs.
- Reduced API crash domains from eight to four files, allowed at most three attempts only for native abort/segfault exit codes, and emit an explicit recovery line with the exact partition and retry count. Ordinary assertion/configuration failures still receive no retry.

**Result**: The fourth failed evidence remains preserved. Scheduler and partition-bound regressions plus the full partitioned coverage policy must pass before the next exact gate. No required check or coverage threshold changed.

## Cycle 60 - Cross-surface Python crash isolation

**Findings**:

1. The fifth gate executed dependencies correctly, but the monolithic DigitalOcean coverage process and ten-file identity matrix each received two unrelated native SIGSEGVs during Python/FastAPI import and collection.
2. This proves the WSL corruption is process-duration/load sensitive across Python surfaces rather than isolated to API coverage.

**Corrections**:

- Partitioned the full sorted DigitalOcean test inventory into four-file coverage processes with exact combine/report output, native-crash-only bounded recovery, and explicit recovery reporting.
- Partitioned the fixed ten-file identity security inventory one file per process with the same ordinary-failure-immediate/native-crash-bounded policy.
- Updated complete-gate static contracts to bind both partitioned inventories and their unchanged C-tracer/report targets.

**Result**: The fifth failed evidence remains preserved. Both partitioned surfaces and the unchanged combined coverage policy must pass before another exact-commit gate; no test or required status was removed.

## Cycle 61 - Data-rights reporting crash isolation

**Findings**:

1. The sixth exact gate passed every other required node and all 19 data-rights assertions, then aborted with native allocator corruption while pytest-cov parsed source for its terminal report.
2. Repository-wide API coverage already executes this exact inventory in isolated coverage partitions and enforces the unchanged coverage policy, so this contract node was redundantly creating a second monolithic report without adding assurance.

**Corrections**:

- Replaced the redundant monolithic data-rights invocation with an exact five-file inventory executed one file per fresh interpreter.
- Disabled duplicate coverage only in this focused contract node; the required partitioned API coverage node still measures every data-rights test and source line and remains a prerequisite of the final policy gate.
- Retained at most three attempts only for native abort/segfault exits, explicit recovery reporting, and immediate failure for every ordinary test, collection, or configuration error. Added gate-contract coverage for the exact inventory and policy.

**Result**: All five isolated partitions and all 19 assertions pass, complete-gate contract tests pass, and Feature 093 analysis reports zero findings. The sixth failed evidence remains preserved; a new exact-commit gate is required.

## Cycle 62 - Public module registry foundation

**Findings**:

1. The versioned module JSON schema existed, but no runtime validator or registry enforced semantic compatibility, namespaces, cross-module conflicts, dependency existence/cycles, safe references, or deterministic installation.
2. Accepting executable hooks, import paths, or module-provided commands would make a manifest an unreviewed code-execution boundary.

**Corrections**:

- Added a standard-library module validator with exact keys, strict semantic versions and Base2 constraints, safe relative references, namespaced permissions, fixed provider capabilities, explicit lifecycle policy, and deep-copied normalized data.
- Added registry-wide duplicate, conflict, missing-dependency, and cycle rejection plus stable dependency-ordered install and health inventories.
- Added hostile fixtures for unknown keys, traversal, absolute paths, unsafe routes, cross-namespace permissions, unknown capabilities, incompatible versions, duplicates, missing/cyclic dependencies, conflicts, malformed JSON, and symlinks.
- Made the six-case module registry suite a required complete-gate dependency. The contract accepts no command, shell, callable, import, or executable hook field.

**Result**: T081 and T082 complete. The focused module suite and gate-contract suite pass, and the install plan is deterministic data only. Lifecycle mutation remains intentionally absent until T083/T084 define its receipt, replay, rollback, and persistent-data semantics.

## Cycle 63 - Receipt-bound module lifecycle

**Findings**:

1. Registry validation alone did not define durable install, enable, disable, upgrade, export, removal, replay, or rollback behavior.
2. A lifecycle implementation could otherwise lose persistent data, leave scheduled jobs active while disabled, accept downgrade/migration-history loss, or replay changed requests under an old operation identity.

**Corrections**:

- Added locked atomic owner-only lifecycle state, HMAC-signed before/after receipts, exact-request replay, changed-request rejection, and exact-latest rollback with state-integrity checks.
- Added explicit job suppression/reactivation, preserve/archive and forbid/backup-required/purge data policies, forward-only semantic upgrades, migration-history preview, export inventory, and sanitized stable admin overview.
- Added seven focused lifecycle cases covering every transition, state corruption, receipt tampering, replay, upgrade order, migration preview, removal policy, persistent state, and scheduled jobs.
- Added operator-facing SDK documentation and made lifecycle validation a required gate node chained before the remaining repository checks.

**Result**: T083 and T084 complete. Thirteen module registry/lifecycle cases and the gate-contract suite pass. Provider declarations remain inert metadata and no dynamic module code execution or provider activation was introduced.

## Cycle 64 - SDK-only fixture boundary

**Findings**:

1. The SDK needed proof that a new module could be described without editing registry code or adding an executable extension hook.
2. Programmatic hostile mutations did not leave durable review fixtures for the two highest-risk boundaries: command injection and path traversal.

**Corrections**:

- Added `fixture-notes` using only the public declarative manifest, settings schema, and reviewed SQL migration surface.
- Added durable hostile command-field and migration-traversal manifests and required both to fail closed through the same public validator used by the valid fixture.
- Kept the fixture provider-free and tenant-keyed; it grants no runtime route activation or migration execution merely by existing in the repository.

**Result**: T085 complete. The fixture produces the exact one-module deterministic install plan, and every durable hostile fixture is rejected before lifecycle state changes.

## Cycle 65 - Typed content-pack reuse

**Findings**:

1. Portfolio, blog, and documentation require distinct public experiences but share the already-reviewed tenant-owned content, publication, revision, search, and media controls.
2. The existing collection endpoint could not filter by content type, so a pack page could mix unrelated published records.

**Corrections**:

- Added three conflict-free providerless module manifests and settings schemas, each disabled until a site manifest explicitly enables it.
- Extended the Django-backed FastAPI repository/service/route with a validated tenant-bound content-type filter while preserving cursor bounds and published/search-visible policy.
- Added reusable React collection/detail behavior, encoded links, exact type requests, and fail-closed disabled pack routes for portfolio, blog, and documentation.
- Added independent Django tenant/type, API query/SQL, React service/rendering, and combined manifest tests plus pack documentation and a required gate node.

**Result**: T086 complete. The three packs reuse one hardened pipeline without data or navigation leakage, and none adds provider authority.

## Cycle 66 - Forms, gallery, and media packaging

**Findings**:

1. Hardened form/outbox and media quarantine/variant implementations existed, but they were not represented through the public module SDK.
2. Gallery must not become independently active without the media safety boundary, and capability declarations must not imply provider activation.

**Corrections**:

- Added forms, media, and gallery manifests with independent routes, permissions, jobs, settings, health checks, and persistent-data policies.
- Bound gallery to an explicit media dependency. The deterministic install plan therefore admits media before gallery.
- Declared email and storage only on the packs that may later use them; default settings keep adapters disabled and lifecycle receipts grant no provider or credential authority.
- Added combined dependency/capability tests, documentation, and a required gate node chained to the existing public-content abuse suite.

**Result**: T087 complete. Existing form replay/retention/outbox and media quarantine/variant tests remain authoritative, while the SDK gate proves correct pack composition and inert provider declarations.

## Cycle 67 - Real PostgreSQL identity acceptance

**Findings**:

1. Docker access became available after owner-approved group membership, allowing the deferred real-database checkpoint.
2. The public-account audit table was append-only by application convention but lacked database-enforced UPDATE/DELETE rejection.
3. Docker Desktop did not expose ephemeral PostgreSQL reliably through WSL host or bridge addressing, and a fresh image build hit the known native exit 139 during dependency installation.

**Corrections**:

- Added API and Django-parity migration `007/0004` with a PostgreSQL trigger that rejects audit UPDATE/DELETE using SQLSTATE `55000`.
- Added a bounded acceptance harness that runs PostgreSQL 16 and a read-only current-source API checker in one private Docker network, generates an ephemeral password, and removes every owned container on pass or failure.
- Reused an existing local Base2 API dependency image after the host-native build crash; current source is mounted read-only and forced first on `PYTHONPATH`.
- Added a required static parity contract binding both migrations and the API migration inventory.

**Result**: T080 complete. The live trial created two tenants, denied cross-tenant owner access, persisted exact refresh-session revocation, rejected audit deletion at the database layer, reset transaction-local tenant state before pool reuse, returned a machine-readable pass, and left zero owned containers.

## Cycle 68 - Transactional events and booking

**Findings**:

1. Events require UTC instants plus valid IANA presentation zones; naive or invented zones would create ambiguous bookings.
2. Capacity checks without a row lock permit concurrent oversubscription, while unbound event IDs permit cross-tenant probing.

**Corrections**:

- Added tenant-owned Event and Booking models, constraints, migration parity, exact attendee replay, and a `select_for_update` capacity transaction.
- Added tenant-bound FastAPI event listing and authenticated booking admission with generic not-found/conflict errors.
- Added manifest-gated React listing and booking feedback, provider-inert event/booking manifests, and operations documentation.
- Added SQLite contract cases and an ephemeral PostgreSQL 16 two-thread capacity-one race; the latter produced exactly one confirmation and one capacity rejection and cleaned all owned containers.

**Result**: T088 complete. Scheduling manifests install events before booking, only booking declares inert email capability, and all focused model, API import, React, manifest, migration-drift, and live race checks pass.

## Cycle 69 - Scheduling changed-line coverage

**Findings**:

1. The exact `bcd27b8` gate passed every functional node but the unchanged 90% changed-line policy failed at 89.68%.
2. The new repository SQL branches and client request binding were exercised indirectly but not directly attributed by their isolated coverage processes.

**Corrections**:

- Added direct tenant-bound event listing, locked successful reservation, missing-event rollback/no-insert, encoded event ID, seat count, and generated-tenant client tests.
- Kept the coverage floor and every required check unchanged.

**Result**: The failed exact evidence remains preserved. Focused coverage must pass before a replacement exact-commit gate.

## Cycle 70 - Moderated community and private support

**Findings**:

1. Community content cannot use immediate publication safely, and support payloads cannot inherit public content visibility.
2. Notification adapters must not receive post bodies, messages, emails, or credentials.

**Corrections**:

- Added bounded active-content rejection, deterministic abuse scoring, explicit moderation transitions/reasons, and opaque notification payloads.
- Added authenticated tenant-bound community submission stored as non-searchable draft content pending review.
- Added support-specific processing consent and forced private retention classification over the existing replay/CSRF/rate-limit/outbox pipeline.
- Added content/community/support SDK manifests, dependency ordering, inert email declaration, focused policy/service tests, documentation, and a required gate node.

**Result**: T089 complete. Community cannot self-publish, support cannot become public, and notification payloads contain identifiers/status only.

## Cycle 71 - Disabled commercial pack composition

**Findings**:

1. Membership, catalog, and listing data can be provider-free, while their subscription, commerce, and marketplace transaction layers require an explicit payment boundary.
2. A capability declaration must not activate credentials, sockets, or production behavior.

**Corrections**:

- Added six independently versioned manifests as three dependency pairs, with every pack disabled by default and payment capability limited to transaction modules.
- Added deterministic membership, commerce, and marketplace domain services using only a credential-free in-process fake; network calls are forbidden by the test harness.
- Bound transactions to tenant/replay inputs, required marketplace moderation, rejected self-purchase, and documented the separate live-provider authority boundary.

**Result**: T090 complete. All three pack suites pass and no live-provider value or call path exists in their settings.

## Cycle 72 - Payment and webhook hostile boundary

**Findings**:

1. Provider callbacks require exact signature, freshness, event allowlist, bounded body, and changed-replay rejection.
2. Sandbox webhook configuration requires a SecretRef and scoped approval shape, while production activation is outside Feature 093 authority.

**Corrections**:

- Added constant-time HMAC verification over timestamp and exact body, five-minute freshness, stable event IDs, exact idempotent replay, and changed-body conflict rejection.
- Added disabled/local-fake payment activation and separately validated sandbox webhook configuration; production and plaintext credential modes fail closed.
- Added deterministic refund/cancel state transitions and hostile envelope, credential, mode, signature, replay, JSON, and event fixtures.

**Result**: T091 complete. Provider security tests execute with injected test bytes only, perform zero credential reads/network calls, and cannot activate production payments.

## Cycle 73 - Complete module checkpoint

**Findings**:

1. Pack-specific tests did not provide one inventory proving every declared module can traverse the same lifecycle and maintain conflict-free routes.
2. Visual, accessibility, compatibility, performance, and lifecycle results needed one required dependency chain rather than an informal checklist.

**Corrections**:

- Added a credential-free checkpoint that loads all manifests through the public registry and runs install, disable, enable, preview, upgrade, and export for every pack in a private temporary state store.
- Added exact route conflict detection, deterministic inventory digest, state-permission checks, cleanup evidence, and explicit zero credential/network counters.
- Chained the required checkpoint to the commercial pack, hermetic visual, accessibility, public experience/performance, and browser compatibility gates and documented its authority boundary.

**Result**: T092 complete. The combined US6/US10 bundle is deterministic, provider-inert, and required by the full gate.

## Cycle 74 - Module checkpoint exact-gate repair

**Findings**:

1. The tenant repository invariant still asserted five database contexts after the community insert added a sixth tenant-bound operation.
2. A mistaken `--help` invocation started this argument-free gate runner concurrently, causing two Playwright processes to contend for the same trace directory and one compatibility test to time out.

**Corrections**:

- Updated the static tenant matrix to require six explicit transaction contexts, five query predicates, and the tenant column on the community insert.
- Confirmed no duplicate complete-gate or Playwright process remains before isolated browser replay.

**Result**: The original exact-commit failure remains immutable evidence; both failed nodes must pass in isolation before a replacement commit and full gate.

## Cycle 75 - Observable incident lifecycle

**Findings**:

1. Health, queue, adapter, log, metric, and trace evidence needed one bounded schema and recursive secret redaction policy.
2. Repeated fault sampling could spam the owner unless incident and recovery transitions were durable and idempotent.

**Corrections**:

- Added strict structured event kinds, severity, diagnostic codes, correlation IDs, attribute bounds, and recursive secret-key/value redaction.
- Added an atomic owner-only alert ledger that emits exactly once on failure and once on recovery, with corrupt state failing closed.
- Added an integrity-digested diagnostic bundle limited to exact commit, boot, events, health, queues, and adapter state plus injected fault tests and operations documentation.

**Result**: T093-T094 complete. Fault, repeated-fault, recovery, redaction, corrupt-state, and safe-bundle cases pass without notification-provider or credential authority.

## Cycle 76 - Authenticated recovery and stateful preview preservation

**Findings**:

1. Backup evidence required authenticated encryption, exact target/schema binding, and an isolated restore boundary rather than checksum-only archives.
2. Stateful preview destruction needed a real snapshot receipt compatible with the existing preservation decision and exact recreation proof.

**Corrections**:

- Added AES-256-GCM backup envelopes with authenticated metadata, fresh nonce, exact digest/size, atomic owner-only storage, and SecretRef-only key identity.
- Added absent-target isolated restore, migration/rollback preflight, staging-only certificate drills, and hostile corruption, wrong-target, stale-schema, partial-file, existing-target, and secret-exposure tests.
- Integrated encrypted preview snapshots with lease ID, verification/expiry evidence, preservation admission, and exact state recreation.

**Result**: T095, T096, and T128 complete. The bounded local recovery drills preserve exact state and expose neither plaintext nor key material; production restores and provider actions remain unauthorized.

## Cycle 77 - Immutable health-gated release control

**Findings**:

1. A deploy identity must bind image digest, source commit, SBOM, provenance, and signature before any health or traffic action.
2. Failed candidate health and explicit rollback require exact prior/current identities and durable observation state.

**Corrections**:

- Added signed immutable release manifests and fail-closed rejection for tags, malformed provenance, tampering, and reused identities.
- Added an atomic provider-neutral release controller with idempotent replay, pre-traffic health gating, failed-candidate restoration, exact-current rollback, and sanitized observation.
- Added three successive update/replay cycles, health-failure restoration, tamper, mutable-image, and rollback-target tests.

**Result**: T097-T098 complete. All local release transitions are verified and reversible; the controller itself has no provider, registry credential, or public traffic authority.

## Cycle 78 - Capacity and operations checkpoint

**Findings**:

1. Capacity claims needed a versioned profile covering load, soak, memory, backpressure, cache contention, and queue drain with integrity assertions.
2. Operations readiness needed one providerless bundle proving repeated incident, restore, release, capacity, certificate, and cleanup behavior.

**Corrections**:

- Added the bounded small-preview profile plus queue saturation/rejection, exact drain, 32-way single-flight cache, three-round soak, p95, error-rate, and peak-memory tests.
- Added a combined checkpoint with three encrypted restore cycles, three immutable healthy releases, one alert and one recovery notification, staging certificate renewal, capacity evidence, and zero retained resources/state.
- Made both suites required full-gate nodes and documented the local-versus-live authority boundary.

**Result**: T124 and T099 complete. SLO, recovery, integrity, budget, idempotent alert, and cleanup evidence pass locally with zero provider calls or credential reads.

## Cycle 79 - WSL native-corruption recovery

**Findings**:

1. The first post-recovery complete gate recorded repeated native segmentation faults across unrelated Python imports and frameworks; an isolated replay additionally reported allocator corruption and a malformed standard-library `sysconfig` result despite 30 GiB available memory.
2. Existing API and DigitalOcean partition runners already retried native exits three times, and the gate retried direct native exits twice, so further retries would conceal a corrupted runtime rather than increase assurance.

**Corrections**:

- Preserved the failed exact-commit gate and stopped treating the condition as an application assertion.
- Restarted the WSL VM only after confirming the repository was committed and no owned containers or provider resources existed.
- Revalidated interpreter configuration, imports, API coverage partitions, all DigitalOcean partitions, and the full Django suite from the clean runtime.

**Result**: The isolated suites pass after runtime convergence with unchanged product code and unchanged test thresholds. A replacement exact full gate is required before the operations phase can be considered closed.

## Cycle 80 - Exact-commit website factory

**Findings**:

1. Child repositories must derive from immutable committed source without inheriting the parent worktree, identity, runtime residue, or authority.
2. Profile-controlled paths, commands, modules, secrets, compatibility, and governance require fail-closed schemas and a child-local gate.

**Corrections**:

- Added strict factory profile/provenance contracts, safe tar-member extraction from exact `git archive`, deterministic filtering, interruption cleanup, and Bash/PowerShell wrappers.
- Added distinct child identity, selected declarative modules, provenance, license/notice, vulnerability policy, CODEOWNERS, branch guidance, dependency updates, inherited CI, and SecretRef-only configuration.
- Added a non-applying upgrade advisor, hostile profile/commit/output fixtures, three distinct fixture profiles, deterministic double-generation, and an applicable child gate that executes no input-supplied command.

**Result**: T100-T107 and T125 complete. Blog/portfolio, SaaS, and marketplace children generate differently and deterministically from one exact commit, pass governance/module/provenance checks, and perform zero provider or credential actions.

## Cycle 81 - Generated-child live acceptance preflight

**Findings**:

1. T108 needs an exact child archive rather than the parent repository archive used by the earlier provider canary.
2. The approval must bind child identity/state intent plus existing DNS, lease, staging-certificate, concurrency, and cost controls before credentials or network access.

**Corrections**:

- Added deterministic normalized child archiving, tree digest, plaintext staging cleanup, and an approval-required plan compatible with the existing integrity-verifying live runner.
- Bound the exact parent commit, child archive digest, child identity/profile, restore-required state mode, unique DNS name, three sequential trials, one-resource concurrency, fifteen-minute lease, staging-only certificates, and existing cost ceilings.
- Added changed-archive and reused-output hostile tests; preflight reports zero network requests and secret emissions.

**Result**: T108 implementation and credential-free preflight contract are ready. The live deploy/verify/destroy/recreate run remains open until its newly generated exact plan receives separate provider approval.

## Cycle 82 - Bounded WSL native-corruption convergence

**Findings**:

1. Native corruption recurred after a clean WSL restart and could surface as segmentation faults or corrupted Python container iteration, sometimes causing wrapper exit 1 rather than a directly retryable signal.
2. Blindly retrying any failed gate would hide product, security, coverage, or policy defects.

**Corrections**:

- Added a strict evidence classifier that grants runtime-recovery eligibility only when every failed check contains a recognized native Python/allocator corruption signature.
- Added a Windows-side launcher that requires a clean tracked exact commit, runs the unchanged gate, permits at most one WSL restart, verifies the commit is unchanged, and refuses application or mixed failures.
- Added native-only, product-only, mixed-failure, bounded-retry, exact-commit, and static launcher tests plus an operator runbook.

**Result**: WSL recovery is automated without weakening a check or converting a failure into success. Original and replacement evidence remain separate, and recurring corruption after one restart still fails closed.

## Cycle 83 - Generated-child live acceptance

**Checks**:

- Revalidated exact commit `56ac18588b4b4f157f22f531e7767d4094edc21b`, plan digest `363074ed8057cab6b4698a2f832f8e30bd3b60c54a864183eed9a2cd4f0e0c64`, source archive digest, SSH identity, cost/lease/concurrency limits, staging-only certificate mode, ownership namespace, and exact DNS record before mutation.
- Ran three sequential create, full 12-service health, exact source identity, staging policy, DNS, teardown, and recreation trials.
- Independently queried the provider after completion and found zero ownership-matching Droplets and zero exact DNS records; every lease state was `destroyed` and temporary credential copies were removed.

**Result**: T108 live acceptance passed. Estimated cost was 3 USD minor units under the approved 100-unit ceiling; no production certificate or persistent provider resource was created.

## Cycle 84 - Final drift and evidence gap analysis

**Findings**:

1. Documentation, configuration, OpenAPI, generated-client/profile, module-inventory, and route-inventory changes could each become stale without one required cross-surface lock.
2. Final experience and recovery claims needed machine-readable builders that reject incomplete gates, missing checks, mismatched commits, incomplete restore cycles, or a non-destroyed canary.

**Corrections**:

- Added a six-family SHA-256 drift lock, named diagnostics, explicit reviewed refresh, and hostile stale/new/missing artifact tests to the required gate.
- Added final experience and recovery ledger builders bound to exact gate, profile, operations, and live receipts, with failure-oriented unit tests.
- Published one consolidated migration, operations, security, module, factory, cost, recovery, residual-risk, activation, and release guide.

**Result**: T109 and T126 are complete, and the T111-T113 evidence builders and documentation are ready. Final exact-commit gates and generated ledgers remain required before those tasks and T114 can close.

## Cycle 85 - Cross-runtime native failure classification

**Findings**:

1. The final gate launcher correctly recognized repeated Python/allocator corruption and restarted WSL once, but the clean-runtime replay encountered Playwright's exact unexpected worker `SIGSEGV` signature.
2. The classifier treated that native worker termination as a product failure because its allowlist covered Python and allocator signatures only.

**Corrections**:

- Added only Playwright's exact `worker process exited unexpectedly (code=null, signal=SIGSEGV)` signature to native recovery eligibility.
- Added positive worker-crash and mixed worker-crash-plus-accessibility-assertion tests; mixed or ordinary visual failures still forbid restart.
- Retained the exact-commit check, clean-worktree requirement, preserved evidence, and one-restart maximum.

**Result**: Native recovery covers the observed Python and browser-worker corruption classes without admitting screenshot, accessibility, product, security, coverage, policy, or mixed failures.

## Cycle 86 - Independent CI compatibility and lint truth

**Findings**:

1. The first exact-commit GitHub matrix proved five workflows green but exposed frontend and backend failures hidden by the unreliable local WSL runtime.
2. Frontend CI selected Node 18 for a locked jsdom dependency that requires a supported newer runtime, so every Vitest worker failed before tests and coverage incorrectly reported zero.
3. The API matrix linted the entire multi-service repository instead of its API boundary; after correcting that scope, 26 real API style findings remained. Django Mypy also found one untyped live-race result list.

**Corrections**:

- Moved frontend CI to supported Node 20 without changing dependencies, tests, or coverage thresholds.
- Bound API Ruff to `api`, mechanically reformatted the four reported API files, fixed the remaining nested-context finding, and retained the complete behavioral suite.
- Typed the Django race-test outcomes, explicitly allowlisted only these post-live CI-recovery paths, and extended the closeout-delta regression so unrelated runtime changes remain forbidden.
- Repaired the Gunicorn process-model probe so a dependency-degraded `503` still proves the server and structured readiness contract are live, while cleanup uses bounded terminate/kill/communicate instead of blocking on a live stdout pipe.

**Result**: Local focused validation passes Ruff, both Mypy partitions, the API matrix with threshold-passing coverage, 125 frontend tests with threshold-passing coverage, a real bounded Gunicorn readiness probe, Storybook, and all closeout-delta tests. Exact-commit independent CI replay remains required before T136-T137 or final closeout can complete.

## Cycle 87 - Frontend asynchronous-render determinism

**Findings**:

1. The repaired exact-commit matrix made six of seven workflows green and proved the backend process-model repair, but frontend CI exposed one timing race in the content-pack detail test.
2. The test waited only for the mocked repository call, then synchronously asserted a heading rendered by a later React state update. Runner timing could therefore fail a correct user-visible transition.

**Corrections**:

- Changed the test to await the actual accessible heading before verifying the exact repository call.
- Repeated the focused four-case content-pack suite five consecutive times and retained the same application behavior and coverage thresholds.
- Added only the exact test path to the post-live closeout delta and its fail-closed regression inventory.

**Result**: The focused test passes deterministically and the closeout/CI-policy regression suite passes 14 cases. Two consecutive exact-commit independent matrices remain required before T138 and final closeout can complete.

## Cycle 88 - Consecutive closeout proof

**Checks**:

- Ran two unchanged local complete gates at exact commit `05e71a59bcb7528791af5dab2ccadff9462338cc`; both passed all 77 required checks with zero non-passing statuses.
- Ran the full seven-workflow GitHub push matrix twice at the same commit; backend, frontend, contract, E2E, smoke, repository guards, and Option1 authority guard all passed on both attempts.
- Generated exact-gate experience and recovery ledgers; both passed their required check inventories and integrity constraints.
- Reconciled the live child canary to three destroyed leases, restored DNS, zero provider resources, staging-only certificates, three minor USD cost units, and zero emitted secret values.

**Result**: T110-T114 and T136-T138 are complete from evidence. All 138 tasks and 58 functional requirements are mapped and complete, with no known unresolved finding or silent failure. The branch remains unmerged; PR, merge, deployment, production activation, and provider mutation retain separate approval boundaries.
