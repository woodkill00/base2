# Research: Efficient Assurance Orchestrator

## Decisions

### Use risk-based test impact analysis, not naive filename filtering

Explicit surfaces and transitive dependencies are auditable and fail closed. Pure coverage-based selection is rejected because missing runtime coverage can silently omit security and migration behavior.

### Preserve one immutable release authority

The existing complete gate remains mandatory for release. The optimized orchestrator accelerates feedback and avoids redundant reruns but cannot redefine completion.

### Cache proof, not conclusions

Reuse keys bind the exact command and relevant source/tool/config identities. Time alone or a prior green SHA is insufficient. Negative, partial, interrupted, and native-crash evidence is never a reusable pass.

### Summaries are derived artifacts

Agents receive compact structured receipts. Full logs remain local and private. This cuts token use without discarding diagnostics.

### Optimize order before concurrency

Cheap policy and contract checks run before expensive Compose/browser checks. Concurrency begins conservatively because this workstation has demonstrated memory and hypervisor instability; resource-aware parallelism is permitted only with measured safety.

### Measure escaped-fault risk

Mutation fixtures for security, tenancy, migrations, contracts, visuals, workflows, and release policy prove narrowing still catches important defects. Speed without mutation detection is not accepted.

## Alternatives Rejected

- Always run everything: safe but too slow and wasteful for routine iteration.
- Let an agent choose tests ad hoc: unauditable and prompt-dependent.
- Cache solely by commit: ignores command, dependency, toolchain, and policy drift.
- Retry all failures: masks defects and wastes time.
- Upload logs to an external summarizer: adds cost, latency, and confidentiality risk.
- Broad parallel execution: increases memory contention and native crash frequency.
