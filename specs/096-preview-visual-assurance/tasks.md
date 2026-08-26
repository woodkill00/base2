# Ordered Tasks

## Phase 1 - Closeout and contracts

- [x] T001 Record Feature 095 PR, merge, live acceptance, DNS-cache finding, and exact teardown.
- [x] T002 Define Feature 096 objective, boundaries, user stories, requirements, and outcomes.
- [x] T003 Define architecture, security model, delivery phases, tests, and rollback.
- [x] T004 Record DNS, runtime, expiry, responsive, and SVG/raster decisions.
- [x] T005 Define control, runtime, inventory, DNS, expiry, and visual data models.
- [x] T006 Define CLI commands, safe JSON output, exit codes, and typed failure codes.
- [x] T007 Create initial requirement traceability.

## Phase 2 - Failing tests and fixtures

- [x] T008 Add native runtime admission tests for WSL, Linux ELF tools, Windows paths, UNC paths, and `/mnt/c` repositories.
- [x] T009 Add state-root permission, symlink, traversal, and malformed lease tests.
- [x] T010 Add multi-lease inventory, conflict, expiry, destroyed, and deterministic ordering tests.
- [x] T011 Add DNS converged, stale recursive, split view, unexpected AAAA, duplicate, and malformed observation tests.
- [x] T012 Add expiry plan, fixed command, persistent catch-up, drift, and idempotency tests.
- [x] T013 Add visual artifact hashing, PNG dimension, duplicate identity, traversal, symlink, oversized, and missing coverage tests.
- [x] T014 Add visual HTML escaping, deterministic ordering, and no-secret output tests.
- [x] T015 Add CLI stdout, exit-code, credential-free, lock, and deterministic receipt tests.
- [x] T016 Add Bash entrypoint boundary and native-runtime tests.

## Phase 3 - Runtime and inventory

- [x] T017 Implement owner-only canonical state-root admission.
- [x] T018 Implement native WSL repository and tool-path inspection.
- [x] T019 Implement Linux binary/version inspection without executing untrusted repository content.
- [x] T020 Implement integrity-valid lease discovery without symlink following.
- [x] T021 Implement deterministic lifecycle summaries and conflict classification.
- [x] T022 Implement sanitized inventory receipts and stable failure codes.

## Phase 4 - DNS convergence

- [x] T023 Implement normalized DNS observation schema.
- [x] T024 Implement provider/public/system/exact view separation.
- [x] T025 Implement stale, split, unexpected IPv6, and converged classification.
- [x] T026 Implement TTL-aware safe remediation without automatic network reconfiguration.
- [x] T027 Bind exact-address browser targets to validated live leases.
- [x] T028 Preserve public DNS as an independent required acceptance result.

## Phase 5 - Expiry and lifecycle assurance

- [x] T029 Implement fixed exact-run expiry plan generation.
- [x] T030 Implement persistent timer rendering and plan digest.
- [x] T031 Implement installed timer inspection and drift detection.
- [x] T032 Implement idempotent arm and verify behavior through a fixed systemd adapter.
- [x] T033 Implement backup-observer status when primary cleanup authority is unavailable.
- [x] T034 Implement bounded extension validation without silently changing provider authority.
- [x] T035 Preserve exact lease-v2 teardown and failure cleanup delegation.

## Phase 6 - Visual and asset assurance

- [x] T036 Implement safe visual artifact discovery and validation.
- [x] T037 Implement PNG dimension and SHA-256 extraction.
- [x] T038 Implement logical screenshot identity and duplicate rejection.
- [x] T039 Implement required public/operator/authenticated coverage matrix.
- [x] T040 Implement deterministic JSON manifest and private HTML index.
- [x] T041 Implement pending/approved/rejected review state without silent baseline mutation.
- [x] T042 Implement SVG UI-artwork and classified raster-exception policy scanner.
- [x] T043 Add responsive width/height/orientation/DPR/large-text geometry cases.
- [x] T044 Add left/right rail, footer, fixed-control collision, overflow, and internal-scroll assertions.

## Phase 7 - Unified control plane

- [x] T045 Implement typed `ControlReceipt` and error catalog.
- [x] T046 Implement exclusive state mutation lock and request digest.
- [x] T047 Implement `preflight`, `status`, `dns`, and `evidence` commands.
- [x] T048 Implement `arm-expiry`, `verify`, `extend`, and `destroy` delegation boundaries.
- [x] T049 Implement the WSL-only Bash entrypoint.
- [x] T050 Add bounded stderr diagnostics and one-object stdout behavior.
- [x] T051 Document exact operator workflows and recovery actions.

## Phase 8 - Analysis refinement and gates

- [x] T052 Run requirements-to-tasks completeness analysis.
- [x] T053 Run authority, credential, path, symlink, injection, and output threat analysis.
- [x] T054 Run DNS, provider, timer, reboot, concurrency, and partial-cleanup fault analysis.
- [x] T055 Run visual coverage, accessibility, responsive, and asset-policy analysis.
- [x] T056 Add and implement every task found by cycles T052-T055.
- [x] T057 Repeat analysis until zero unresolved findings remain.
- [x] T058 Run focused unit and CLI suites with changed-line coverage at or above 90%.
- [x] T059 Run React unit, accessibility, interaction, and expanded visual suites.
- [x] T060 Run API, Django, integration, E2E, smoke, security, audit, SBOM, license, and complete gates.
- [x] T061 Run staged/history secret scans and verify zero secret output.

## Phase 9 - Live acceptance and closeout

- [ ] T062 Commit and push the exact feature branch.
- [ ] T063 Publish a PR and require all checks green before merge.
- [ ] T064 Merge and deploy one bounded staging-certificate canary from exact `main`.
- [ ] T065 Verify authoritative/public/system DNS and exact-address browser evidence separately.
- [ ] T066 Review the generated visual evidence index and authenticated operator screenshots.
- [ ] T067 Prove persistent expiry is armed and observable.
- [ ] T068 Perform exact teardown and immediate idempotent replay.
- [ ] T069 Verify zero exact-owned provider resources and no unrelated mutation.
- [ ] T070 Record final evidence, mark every task complete, and close the feature.

## Additional tasks from refinement

- [x] T071 Define and validate an owner-only launch configuration schema with no arbitrary command fields.
- [x] T072 Prove launch source is clean exact local and remote `main` before deterministic archive creation.
- [x] T073 Implement one bounded launch orchestration that delegates to the existing guarded launcher.
- [x] T074 Fail closed into exact lease cleanup when post-launch expiry arming or verification fails.
- [x] T075 Make the expiry execution target stable across branch deletion and checkout switching.
- [x] T076 Add exact provider-inventory reconciliation before launch and after destruction.
- [x] T077 Add bounded rate-limit classification and retry-after evidence without unbounded retry.
- [x] T078 Add cost ceiling, estimated usage, and final cleanup receipt fields.
- [x] T079 Add a private durable notification/outbox receipt for lifecycle and visual failures.
- [x] T080 Add bounded evidence retention and cleanup that never deletes provider state or approved baselines.
- [x] T081 Add hostile launch-config, dirty-main, divergent-main, timer-arm failure, and cleanup-reconciliation tests.
- [x] T082 Add checkout-switch, expired-offline, and post-reboot persistent timer tests.
- [x] T083 Add output secret-pattern, control-character, oversized-message, and HTML-injection tests.
- [x] T084 Add source, timestamp, expected-address, TTL-availability, and digest provenance to DNS observations.
- [x] T085 Add a pre-mutation launch-intent journal and exact-tag interrupted-launch reconciliation.
- [x] T086 Add explicit primary/backup/offline cleanup-controller coverage reporting.
- [x] T087 Add bounded teardown rate-limit recovery that preserves resumable lease state.
- [x] T088 Add representative PR and expanded release visual-matrix definitions.
- [x] T089 Add font readiness, animation stability, lazy-content readiness, and screenshot size bounds.
- [x] T090 Add Chromium, Firefox, and WebKit release-contract coverage where supported.
- [x] T091 Add 200% text, keyboard-only, touch, reduced-motion, contrast, and accessibility release checks.
- [x] T092 Add SVG viewBox, script, external-active-content, and semantic-accessibility validation.
- [x] T093 Add a baseline-review sidecar contract with explicit pending/approved/rejected state.
- [x] T094 Add crash-before-lease, crash-during-DNS, all-controllers-offline, and next-boot recovery tests.
- [x] T095 Add deterministic contact-sheet generation and evidence-bundle integrity verification.
- [x] T096 Re-run complete traceability after all additional tasks and require zero uncovered requirements.
