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
