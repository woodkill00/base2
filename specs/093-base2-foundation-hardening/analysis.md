# Analysis Cycles: Feature 093

Analysis checks requirement coverage, task executability, dependency validity, test-first order, error visibility, security/authority, rollback, observability, documentation, and measurable acceptance. A cycle is complete only after findings are reflected in artifacts and rechecked.

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
3. The gate scheduled frontend test/build, API, Django, and DigitalOcean coverage processes concurrently on the same constrained WSL host, recreating the independently observed Node/Python process instability.

**Corrections**:

- Preserved the failed receipt and did not classify it as green or weaken any test/coverage threshold.
- Serialized the memory-intensive frontend build, API, Django, and DigitalOcean coverage nodes through explicit manifest dependencies while retaining parallel lightweight policy checks.
- Kept both exact full gates required after this scheduling correction.

**Result**: The deterministic suite passes in isolation. T025 remains open pending two consecutive exact green receipts on the corrected resource-aware manifest.
