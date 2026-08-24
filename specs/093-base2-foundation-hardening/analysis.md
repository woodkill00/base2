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
