# Feature Specification: Efficient Assurance Orchestrator

**Feature Branch**: `vscode-codex/107-efficient-assurance-orchestrator`  
**Created**: 2026-09-10  
**Status**: Draft  
**Input**: Reduce Base2 test time and agent-token consumption dramatically without losing effective security, visual, integration, or release assurance.

## User Scenarios & Testing

### User Story 1 — Fast trustworthy feedback (Priority: P1)

As a developer, I want one command to select the smallest sufficient test set for my exact change so ordinary work finishes quickly without silently skipping relevant risk.

**Independent Test**: Known change fixtures select their expected checks; unknown or high-risk changes escalate rather than pass narrowly.

**Acceptance Scenarios**:

1. **Given** a documentation-only change, **when** automatic assurance runs, **then** it avoids Docker and browser suites and returns a bounded explanation.
2. **Given** an authentication, migration, dependency, workflow, deployment, test-policy, or unknown change, **when** assurance runs, **then** it escalates to the configured stronger tier.
3. **Given** a selected check fails, **when** the run ends, **then** the user sees the cause and evidence location without receiving the full log unless requested.

### User Story 2 — Low-token operation (Priority: P1)

As an operator, I want agents and CI to exchange compact machine-readable receipts instead of repeatedly streaming large test logs.

**Independent Test**: Successful output stays within its line/byte budget; failure output is sanitized, bounded, and links to private evidence.

**Acceptance Scenarios**:

1. **Given** a successful run, **when** an agent consumes its result, **then** it receives a compact status, selection rationale, timings, hashes, and evidence path.
2. **Given** a failure, **when** the result is summarized, **then** secrets and bulk logs remain private while actionable diagnostics remain available.

### User Story 3 — Safe evidence reuse (Priority: P1)

As a maintainer, I want unchanged checks to reuse exact, current evidence so restarts and review cycles do not repeat expensive work.

**Independent Test**: Exact-input replay is a no-op; source, command, dependency, toolchain, configuration, environment, expiry, or prior-status drift invalidates reuse.

### User Story 4 — Full release confidence (Priority: P1)

As a release owner, I want the optimized workflow to preserve the existing complete production gate and mandatory hosted checks at release boundaries.

**Independent Test**: Release mode invokes the existing complete gate unchanged and cannot substitute focused or cached evidence where policy requires fresh full evidence.

### User Story 5 — Measurable optimization (Priority: P2)

As an operator, I want private metrics showing wall time, compute time, selected versus avoided checks, cache reuse, retries, output bytes, and estimated agent tokens.

**Independent Test**: A before/after benchmark uses fixed change fixtures and proves safety mutations remain detected.

### Edge Cases

- Dirty, staged, untracked, renamed, deleted, submodule, generated, binary, or very large change sets.
- Merge-base unavailable, shallow history, detached HEAD, changed test-policy code, or invalid configuration.
- Expired, failed, partial, tampered, symlinked, hardlinked, public, or wrong-commit evidence.
- A focused test passes while a seeded downstream contract, migration, security, visual, or integration fault exists.
- Native process crashes, timeouts, cancellation, power loss, concurrent runs, and stale locks.
- Files belonging to multiple surfaces or no known surface.
- Hosted checks still pending, rerun at a different SHA, or produced by an untrusted workflow.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST provide one supported Bash command and one behaviorally equivalent PowerShell command for optimized assurance.
- **FR-002**: The system MUST support `auto`, `focused`, `standard`, `full`, and `release` tiers with documented, deterministic semantics.
- **FR-003**: Automatic selection MUST derive from an explicit versioned file-to-surface and surface-to-check dependency graph.
- **FR-004**: Unknown, ambiguous, policy, security, authentication, authorization, tenancy, migration, dependency, workflow, deployment, backup, restore, or release changes MUST fail closed or escalate.
- **FR-005**: Selection MUST include transitive dependent checks and explain every selected and avoided check.
- **FR-006**: User exclusions MUST NOT remove mandatory checks for the resolved risk tier.
- **FR-007**: Release mode MUST invoke the existing complete gate without weakening its manifest, retries, coverage, visual, integration, or evidence rules.
- **FR-008**: Full and release tiers MUST remain available explicitly at all times.
- **FR-009**: Evidence reuse MUST bind source SHA, diff digest, command, relevant input digests, graph version, toolchain identity, environment class, status, and expiry.
- **FR-010**: Failed, interrupted, partial, stale, mismatched, or unverifiable evidence MUST never be reused as a pass.
- **FR-011**: Security, migration, destructive-operation, backup/restore, and release checks MUST be non-cacheable unless an explicit policy marks exact replay safe.
- **FR-012**: Evidence storage MUST be repository-contained, private, no-follow, integrity-bound, bounded, and safe under concurrent processes.
- **FR-013**: One exact run lease MUST prevent duplicate execution while allowing read-only observation and later recovery.
- **FR-014**: Successful default output MUST be at most 40 lines and 4 KiB.
- **FR-015**: Failure output MUST be sanitized and bounded while identifying failed checks, reasons, attempts, and evidence paths.
- **FR-016**: Full logs MUST be retained privately and read only on explicit request.
- **FR-017**: The orchestrator MUST order checks using deterministic dependencies first and private historical timing only as a tie-breaker.
- **FR-018**: The orchestrator MUST fail fast after a blocking failure and MUST NOT run downstream checks whose prerequisites failed.
- **FR-019**: Independent checks MAY run concurrently only inside explicit CPU, memory, Docker, and browser limits.
- **FR-020**: Native-crash retry MUST reuse the existing narrow classifiers and attempt ceilings; ordinary failures MUST not retry.
- **FR-021**: Visual checks MUST map source dependencies to affected journeys, viewports, browsers, locales, directions, themes, and interaction states.
- **FR-022**: Release mode MUST retain the complete visual matrix; automatic narrowing MUST not update baselines.
- **FR-023**: Hosted evidence MAY be reused only for the exact SHA, trusted workflow identity, required job name, successful conclusion, and configured freshness.
- **FR-024**: Local evidence MUST NOT claim hosted, provider, deployment, or production authority.
- **FR-025**: The system MUST record wall time, summed process time, selected/avoided checks, reuse, retries, output bytes, and a deterministic token estimate.
- **FR-026**: Metrics MUST be private, bounded, redacted, integrity-bound, and excluded from source control.
- **FR-027**: The system MUST compare optimized and legacy runs over fixed representative change fixtures.
- **FR-028**: Mutation fixtures MUST prove relevant security, tenancy, migration, API-contract, visual, workflow, and release-policy failures are still detected.
- **FR-029**: The optimized default MUST reduce median routine feedback time by at least 50% and successful agent-facing output by at least 90% against the current full-gate baseline.
- **FR-030**: No optimization claim may be based solely on skipped tests; the system MUST report assurance tier and residual untested scope honestly.
- **FR-031**: Configuration and evidence errors MUST be actionable and non-silent.
- **FR-032**: The feature MUST add no credentials, network authority, provider spending, deployment, DNS, certificate, publication, or merge authority.
- **FR-033**: Generated child sites MUST inherit the graph and command contract without inheriting private history or evidence.
- **FR-034**: Documentation MUST explain when developers and agents use each tier and when a fresh full gate is mandatory.
- **FR-035**: All selector, cache, evidence, concurrency, failure, shell-parity, mutation, and benchmark behavior MUST have automated tests.

### Key Entities

- **Assurance graph**: Versioned surfaces, path rules, checks, dependencies, risk triggers, cache policy, resources, and output limits.
- **Change set**: Exact base/head identities, normalized changed paths and statuses, and digest.
- **Execution plan**: Resolved tier, selected checks, avoided checks, reasons, ordering, resources, and residual scope.
- **Check receipt**: Exact inputs, status, attempts, duration, bounded summary, private log member, and integrity digest.
- **Run receipt**: Aggregate plan and results with timing, reuse, token estimate, and evidence identity.
- **Benchmark report**: Fixed-fixture legacy/optimized comparison and mutation-detection result.

## Success Criteria

- **SC-001**: Documentation-only automatic assurance completes in under 90 seconds on the reference WSL machine without starting Docker or a browser.
- **SC-002**: Median routine fixture duration is at least 50% lower than the current complete gate.
- **SC-003**: Successful agent-facing output is no more than 4 KiB and at least 90% smaller than the current streamed output.
- **SC-004**: Every seeded safety mutation is detected by automatic escalation or a selected relevant check.
- **SC-005**: Exact replay performs zero check executions; any bound-input mutation invalidates reuse.
- **SC-006**: Release mode produces the same complete-gate requirement set and mandatory hosted-check policy as before this feature.
- **SC-007**: Concurrent duplicate invocation executes each admitted check at most once.
- **SC-008**: Automated tests cover every requirement and report no critical, high, or medium review finding before merge.
