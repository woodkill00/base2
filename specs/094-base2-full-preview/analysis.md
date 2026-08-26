# Analysis: Base2 Full-Stack Obsidian Preview

## Cycle 1 - Initial consistency review

Findings:

1. The initial concept treated DNS cleanup as a service post-step; the live teardown proved that a no-mutation `not_expired` result could still trigger DNS deletion.
2. The visual requirement did not distinguish profile identity, brand theme, and user light/dark preference.
3. Protected surfaces needed both denied and successful outside-in probes.
4. A full preview needed an explicit route mode rather than weakening minimal canary.
5. Live readiness needed a state distinct from local readiness.

Corrections:

- Added unified lease-v2 teardown tasks T049-T055 and the early-teardown regression T014.
- Added profile propagation and first-paint tasks T021-T023.
- Added authenticated/denied route work T035-T040 and T060.
- Added strict three-mode selection T007/T034.
- Added readiness/live evidence work T017/T062/T073.

## Cycle 2 - Security and failure-mode review

Findings:

1. Public-IP admission could accidentally accept private/broad networks.
2. Swagger, Traefik, and pgAdmin would expose sensitive operational information behind only one control.
3. DNS partial failure and legacy records lacked explicit treatment.
4. A 2 GB build could fail from concurrency despite healthy runtime sizing.
5. Credentials could leak through process arguments or probe output.

Corrections:

- Added hostile CIDR policy T010/T041 and authorized refresh T044.
- Required edge auth plus allowlist for all operator surfaces and application auth where available.
- Added legacy inventory, transactional creation, rollback, and reconciliation T047-T053.
- Added bounded/cached build tests and orchestration T018/T058.
- Added private renderer, safe htpasswd, probe redaction, and multi-surface scans T011/T042-T045/T060.

## Cycle 3 - Completeness and verification review

Findings:

1. Local visual proof alone could repeat Feature 093's false confidence.
2. `/api` required an intentional contract rather than accepting a 404.
3. Generated React imports could drift as profiles are added.
4. Live branch cleanup and replay behavior were not explicit.
5. Completion needed exact requirement-to-evidence traceability.

Corrections:

- Added deployed screenshot/console/network verification T061.
- Added API tests/implementation T006/T031.
- Added generated registry T005/T021.
- Added replay and source-branch cleanup T063/T064.
- Added final traceability T071.

## Cycle 4 - Residual gap audit

Reviewed specification requirements, edge cases, entities, policy contracts, task dependencies, rollback, and test families. Every functional requirement maps to one or more ordered tasks; every external mutation remains behind T074; staging-only TLS is invariant; no unresolved clarification or known silent-failure path remains in the task model.

**Result**: `NO_UNRESOLVED_FINDINGS`
**Next state**: implementation may begin with T001.

## Cycle 5 - Implemented-system residual audit

Findings:

1. The first live DNS implementation accepted syntactically valid non-public IPv4 targets and did not accept the DigitalOcean inventory envelope directly.
2. A successful DNS migration lacked a separately callable exact rollback receipt for a later probe failure.
3. The lifecycle contract had no packaged expiry service/timer or separately bound allowlist-refresh operation.
4. The initial browser gate checked HTTP routes but did not retain visual, console, failed-request, identity, and keyboard-interaction evidence.
5. The default forked Vitest worker could exit under WSL memory pressure after otherwise passing tests.

Corrections:

- Restricted DNS targets to globally routable IPv4 and added DigitalOcean-envelope coverage.
- Bound created and replaced record identities and added exact rollback/reconciliation behavior.
- Added one hardened unified expiry service/timer plus an atomic run-and-CIDR-bound allowlist refresh.
- Added a credential-private Playwright live gate for the public Obsidian site and all five operator hosts.
- Changed local and CI unit execution to one threaded worker; the rerun completed all 54 files and 125 tests.

Verification:

- Focused Feature 094 policy, DNS, lease, live-simulation, allowlist, probe, renderer, profile, Traefik, systemd, and API tests pass.
- The three-viewport visual suite passes all 18 checks with six approved Base2 references.
- The complete repository gate passed three times during refinement; the final pre-publication result has every required check green at `.artifacts/complete-gate/20260825T235910Z/result.json`.
- Filtered tracked, staged, and history secret-pattern scans reported zero findings; the excluded DigitalOcean public API specification contains upstream example keys and is not executable or secret input.

**Result**: `NO_UNRESOLVED_IMPLEMENTATION_FINDINGS`
**Next state**: publish, merge, verify merged-main readiness, then cross the separately approved live boundary.

## Cycle 6 - Publication and CI residual audit

Findings:

1. The first post-commit coverage run exposed that untracked new entrypoints had not been included in the earlier changed-line calculation; measured coverage was 63.45%, below the unchanged 90% policy.
2. Pull-request CI attempted the intentionally destroyed production hostname in the performance job instead of reserving that external probe for explicit non-PR execution.
3. Security CI used an obsolete Grype action incompatible with current CycloneDX output, omitted the GitHub token required by the Gitleaks pull-request action, and generated Node license evidence without installing locked dependencies.
4. The Python lockfiles contained late-2025 packages with known 2026 advisories, and the license allowlist omitted legitimate SPDX/name aliases emitted by current scanners.
5. CI had relied on an undeclared `pytest-cov` package, and cffi 2.1.1 exposed no machine-readable license value to the required license scanner.

Corrections:

- Added direct behavioral coverage for the CLI, expiry adapter, SSH bootstrap, live launcher, HTTPS probe transport, renderer, allowlist refresh, Obsidian navigation, and feedback interaction; removed one unreachable unused component.
- Restricted the external performance smoke away from pull requests while retaining its explicit/manual and protected-branch paths.
- Updated the pinned Grype action and SARIF handoff, supplied only the scoped workflow GitHub token to Gitleaks, and installed locked Node dependencies before validating license evidence.
- Regenerated both Python locks from their existing inputs, verified zero findings with current `pip-audit`, and added only scanner-equivalent license aliases.
- Declared `pytest-cov` in both dependency inputs and constrained cffi to audited 2.0.0, whose MIT metadata is verifiable; regenerated locks remain zero-finding under `pip-audit`.

Verification:

- The focused command/guard matrix passes 23 tests.
- The React suite passes 55 files and 128 tests.
- The complete gate passes after final dependency-source correction at `.artifacts/complete-gate/20260826T004917Z/result.json`.
- Changed-line coverage is 838/929 lines, or 90.20%, against the unchanged 90% floor.

**Result**: `NO_UNRESOLVED_PUBLICATION_FINDINGS`
**Next state**: push the corrective commit and require all pull-request checks to pass before merge.
