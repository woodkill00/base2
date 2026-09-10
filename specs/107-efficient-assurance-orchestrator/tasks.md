# Tasks: Efficient Assurance Orchestrator

## Phase 1 — Specification and analysis

- [x] T001 Write user scenarios, measurable outcomes, non-goals, and security boundaries in `spec.md`.
- [x] T002 Define architecture, constitutional compliance, and delivery strategy in `plan.md`.
- [x] T003 Record selection, caching, output, retry, concurrency, and mutation research decisions in `research.md`.
- [x] T004 Define graph, plan, receipt, and benchmark entities in `data-model.md`.
- [x] T005 Define native Bash and PowerShell CLI behavior in `contracts/cli.md`.
- [x] T006 Run analysis cycle 1 and add every identified closure task.
- [x] T007 Add requirement-to-task-to-test traceability and a deterministic plan validator.

## Phase 2 — Graph and selection foundation

- [x] T008 Write failing graph schema and closed-enum validation tests.
- [x] T009 Create `shared/schemas/assurance-orchestrator-v1.schema.json`.
- [x] T010 Create the versioned graph in `shared/config/assurance-orchestrator-v1.json`.
- [x] T011 Write failing normalized Git change-set tests for added, modified, deleted, renamed, staged, dirty, detached, shallow, and invalid-base cases.
- [x] T012 Implement clean exact-source and normalized diff admission.
- [x] T013 Write failing surface mapping, transitive dependency, minimum-tier, and unknown-path escalation tests.
- [x] T014 Implement deterministic selection and reason chains.
- [x] T015 Prove caller exclusions or tier requests cannot remove mandatory checks.

## Phase 3 — Private evidence and replay

- [x] T016 Write failing linked-parent, linked-member, hardlink, mode, owner, tamper, truncation, partial, failed, expired, and mismatch tests.
- [x] T017 Implement contained no-follow private evidence storage and atomic publication.
- [x] T018 Bind receipts to source, diff, graph, argv, inputs, toolchain, environment, status, and expiry.
- [x] T019 Implement exact safe replay and deterministic invalidation.
- [x] T020 Add a nonblocking private run lease and prove duplicate execution is impossible.
- [x] T021 Prove cancellation, exception, power-loss residue, and stale evidence recover safely.

## Phase 4 — Bounded execution and compact output

- [x] T022 Write failing fixed-command, dependency-order, fail-fast, timeout, unavailable-tool, and resource-admission tests.
- [x] T023 Implement fixed command registry execution without a shell or caller-supplied environment.
- [x] T024 Implement dependency scheduling and block downstream checks after prerequisite failure.
- [x] T025 Reuse the existing narrow native-failure classifier and retry ceilings without retrying ordinary failures.
- [x] T026 Enforce conservative CPU, memory, Docker, and browser resource classes.
- [x] T027 Write failing success/failure output-budget and redaction tests.
- [x] T028 Implement compact text and JSON summaries with private full logs.
- [x] T029 Record wall/process time, reuse, retries, output bytes, and deterministic token estimates.

## Phase 5 — Tiers, visual scope, and release boundary

- [x] T030 Define exact `auto`, `focused`, `standard`, `full`, and `release` tier contracts in graph tests.
- [x] T031 Map visual dependencies through journeys, browsers, viewports, locales, directions, themes, and interaction states.
- [x] T032 Prove automatic visual selection cannot update baselines and release retains the full matrix.
- [x] T033 Integrate release mode with the unchanged existing complete gate.
- [x] T034 Prove focused or cached receipts cannot satisfy release-mode evidence.
- [x] T035 Validate exact trusted hosted-check evidence without granting network or merge authority.

## Phase 6 — Entrypoints, CI, and generated children

- [x] T036 Add native `scripts/bash/assure.sh`.
- [x] T037 Add behaviorally equivalent `scripts/powershell/assure.ps1` without cross-shell calls.
- [x] T038 Add wrapper parity and hostile-argument tests.
- [x] T039 Integrate standard-tier planning into pull-request policy without duplicating existing hosted jobs.
- [x] T040 Make generated child sites inherit public graph/config/entrypoints but never private evidence or history.
- [x] T041 Update `docs/TESTING.md` and generated-site guidance with tier and escalation rules.

## Phase 7 — Effectiveness and efficiency proof

- [x] T042 Create fixed routine, cross-surface, and high-risk change fixtures.
- [x] T043 Create seeded security, tenancy, migration, contract, visual, workflow, and release-policy mutations.
- [x] T044 Prove every mutation selects or escalates to a detecting check.
- [x] T045 Benchmark optimized versus legacy selection, runtime, output bytes, and token estimate.
- [x] T046 Prove the ≥50% median routine-time and ≥90% successful-output reductions without counting unsafe skips.
- [x] T047 Run focused tests, exact replay, concurrency, interruption, and shell-parity acceptance.

## Phase 8 — Review and closeout

- [x] T048 Run tasks → analysis → additional-tasks cycles until no gap remains.
- [ ] T049 Run one fresh complete gate at the final exact commit; do not repeat it unless relevant source changes or it fails.
- [ ] T050 Require all hosted checks and independent code/security/UX/data/operations review with no critical, high, or medium finding.
- [x] T051 Produce a concise before/after report, residual-risk statement, and evidence inventory.
- [ ] T052 Obtain separate exact-head approval before publication, merge, deployment, or any external action.

## Phase 9 — Analysis cycle 2 corrections

- [x] T053 Permit dirty state only for planning and focused/standard development runs by binding every changed-member digest, disabling reuse, and forbidding dirty full/release runs.
- [x] T054 Resolve the default base from a verified local merge-base without fetching, and reject missing, unreachable, forward, ambiguous, or caller-malformed bases.
- [x] T055 Treat both sides of renames and deletions as impact inputs and escalate changes to tests, graph, schemas, wrappers, coverage, orchestration, or CI policy.
- [x] T056 Make command IDs resolve through a closed code-owned registry and reject shell operators, relative escape, environment injection, duplicate IDs, cycles, and undeclared tools.
- [x] T057 Validate hosted-check metadata only from an explicit sanitized exact-SHA export with no ambient network call or authority.
- [x] T058 Distinguish measured duration from historical estimates and forbid estimated avoided work from satisfying performance claims.
- [x] T059 Prove dirty-state, base-resolution, rename/delete, self-protection, hostile graph, and offline hosted-metadata boundaries.
- [x] T060 Re-run traceability and task analysis after cycle 2 and add any remaining missing work before implementation.

## Phase 10 — Analysis cycle 3 corrections

- [x] T061 Replace flat cache publication with private atomic per-input directories and bounded owned-stage recovery.
- [x] T062 Record started, interrupted, and terminal run state so status skips no failure and never mislabels incomplete work as passed.
- [x] T063 Order run identities monotonically and make status report whether its source and diff still match current state.
- [x] T064 Bind cache input to the resolved executable identity and invalidate executable, command, policy, graph, source, diff, or environment drift.
- [x] T065 Bound large-change explanations with total count, digest, and representative examples while preserving the complete plan digest.
- [x] T066 Split Operations-specific visual impact from shared/global visual impact and require the full visual matrix for global tokens, CSS, shell, or shared glass changes.
- [x] T067 Store only redacted bounded logs and prove secrets, binary output, and oversized output cannot escape.
- [x] T068 Handle timeout, cancellation, ordinary failure, native failure, concurrent invocation, and recovery without broad retry or silent status loss.
- [x] T069 Add adversarial tests for cache stages, latest-run ordering, source drift, toolchain drift, large diffs, and global visual escalation.
- [x] T070 Re-run task and traceability analysis after cycle 3; implementation begins only if no unresolved gap remains.

## Phase 11 — Analysis cycle 4 corrections

- [x] T071 Explicitly map authentication, authorization, identity, tenancy, privacy, session, CSRF, and security paths to the full security tier.
- [x] T072 Allocate run sequence numbers under the private lease with integrity validation so latest status remains monotonic across clock changes and restarts.
- [x] T073 Preserve pull-request and main-branch push workflows while eliminating duplicate feature-branch push workflow executions.
- [x] T074 Add bounded per-workflow concurrency cancellation for superseded commits without sharing cancellation groups across branches or workflows.
- [x] T075 Prove every required hosted job name and main/pull-request assurance boundary remains unchanged after trigger optimization.
- [x] T076 Prove branch-push duplication is removed across every required workflow and no workflow becomes pull-request-only or main-push-only accidentally.
- [x] T077 Measure the previous and optimized hosted job count for one feature commit and include it in the efficiency report.
- [x] T078 Complete the fourth task-analysis cycle with no unresolved security, coverage, evidence, timing, or token-output gap.

## Phase 12 — Analysis cycle 5 corrections

- [x] T079 Resolve each code-owned executable to one absolute admitted launcher and separately hash its regular target, including managed virtual environments and check-specific working directories.
- [x] T080 Reconstruct child `PATH` only from resolved approved tool directories and exclude ambient repository, temporary, relative, empty, and unknown entries.
- [x] T081 Revalidate executable identity around execution and fail if its path or digest changes.
- [x] T082 Normalize every added, modified, deleted, copied, and renamed Git member as a printable repository-relative POSIX path before hashing, mapping, or output.
- [x] T083 Convert Git decoding, path-control, linked-member, and special-file failures into compact actionable assurance errors.
- [x] T084 Prove ambient executable shadowing, relative managed runtimes, tool mutation, hostile filenames, and rename-path attacks fail closed.

## Phase 13 — Analysis cycle 6 corrections

- [x] T085 Bind cache inputs for managed Python checks to the exact installed distribution manifest, not only the interpreter binary.
- [x] T086 Bind frontend and visual cache inputs to the installed package lock and exact Node executable.
- [x] T087 Keep Docker, security, migration, assurance-policy, and release checks fresh where environment state cannot be completely identified.
- [x] T088 Admit a private owned Playwright browser installation path explicitly without inheriting ambient HOME, credentials, or configuration.
- [x] T089 Prove Python distribution, installed frontend lock, browser path, and missing dependency drift invalidates or blocks reuse.
- [ ] T090 Complete cycle 6 traceability and retain one final full-gate execution only after the final source commit.

## Phase 14 — Analysis cycle 7 corrections

- [x] T091 Reuse the existing exact native-corruption classifiers for at most one additional attempt while every ordinary failure, timeout, or launch failure remains single-attempt.
- [x] T092 Prove exact native corruption can recover once and ordinary failures cannot consume a retry.
- [x] T093 Measure three fixed routine fixtures and use their actual optimized median against one actually measured legacy full baseline.
- [x] T094 Record the individual routine samples without treating estimated avoided work as measured execution.
- [x] T095 Extend requirement traceability through every task added in analysis cycles 4-7.
- [x] T096 Complete cycle 7 with no unresolved correctness, security, coverage, timing, or token-output gap before exact-commit acceptance.

## Phase 15 — Analysis cycle 8 corrections

- [x] T097 Replace the legacy pre-push Docker stream with the compact automatic assurance entrypoint.
- [x] T098 Admit an integrity-valid clean exact-commit complete-gate receipt as stronger evidence with zero duplicate execution.
- [x] T099 Reject dirty, mismatched, partial, failed, public, linked, malformed, or tampered release evidence and test the hook contract.
- [x] T100 Complete the publication-path analysis cycle with no unresolved local integration gap.

## Phase 16 — Analysis cycle 9 independent-review corrections

- [x] T101 Require exact current manifest inventory and artifact-integrity validation before complete-gate evidence can satisfy an automatic run.
- [x] T102 Ensure explicit release always invokes the complete gate and never consumes the automatic stronger-evidence shortcut.
- [x] T103 Revalidate the exact repository source before and after every process and forbid cache publication after drift.
- [x] T104 Make security-sensitive API, Django, and frontend path detection case-insensitive and cover token/auth context paths.
- [x] T105 Bound private run and cache retention and fail closed on linked, foreign, special, or unsafe members.
- [x] T106 Add bounded redacted failure attempts and honest nonzero reuse-output metrics without changing the resolved tier.
- [x] T107 Close the published nested JSON Schema and validate the production graph plus hostile unknown fields.
- [x] T108 Implement distinct compact human-text and explicit `--json` machine-output modes.
- [x] T109 Compare full and compact output for the same exact complete gate while retaining the separate measured routine-fixture median.
- [x] T110 Add adversarial regression tests for every cycle-9 correction and rerun the focused policy matrix.
- [x] T111 Obtain renewed independent code/security, operations, and UX/data acceptance with no critical, high, or medium finding.
- [ ] T112 Run one fresh final exact-commit complete gate, benchmark, hosted matrix, publication, and merge verification.

## Phase 17 — Analysis cycle 10 adversarial-review closure

- [x] T113 Require typed artifact, digest, size, attempts, and zero-exit evidence for every required complete-gate check.
- [x] T114 Escalate token, login, permission, credential, password, user, and account security paths conservatively.
- [x] T115 Re-enforce the cache ceiling immediately before every cache publication in a multi-check run.
- [x] T116 Recheck exact source after cache reads and immediately before cache and terminal result publication.
- [x] T117 Validate every replayed benchmark log and its referenced exact complete-gate receipt.
- [x] T118 Add private benchmark-directory retention with the same owned no-follow deletion boundary.
- [x] T119 Make human plan/explain output include selected, avoided, reason, and residual-scope information.
- [x] T120 Escape terminal controls from every human diagnostic while preserving compact redacted context.
- [x] T121 Report the current interrupted evidence path for errors that occur after run admission.
- [x] T122 Add adversarial regressions and complete the tenth task-analysis cycle with no unresolved static gap.

## Phase 18 — Analysis cycle 11 measurement derivation

- [x] T123 Bind the legacy benchmark duration exactly to the referenced complete-gate receipt’s elapsed time.
- [x] T124 Derive optimized duration exactly from the median of retained routine samples and avoided time from both measurements.
- [x] T125 Reject fully shaped and rehashed benchmark receipts whose performance claims differ from retained evidence.
- [x] T126 Complete the eleventh analysis cycle with no unresolved static correctness, security, operations, UX, or data gap.

## Phase 19 — Analysis cycle 12 live gate ordering

- [x] T127 Compare complete-gate inventories in the gate runner’s deterministic dependency order rather than declaration order.
- [x] T128 Share that exact ordering rule between automatic evidence reuse and benchmark admission.
- [x] T129 Prove reversed manifest declaration with valid dependencies accepts only the actual topological receipt order.
- [x] T130 Record the stopped duplicate attempt and complete the twelfth analysis cycle before replacement exact acceptance.
