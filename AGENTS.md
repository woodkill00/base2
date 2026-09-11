# Base2 agent instructions

Follow `.specify/memory/constitution.md` and the active feature's spec, plan and tasks.
This workflow supplements those requirements; it does not waive release gates or grant
publication, deployment, spending, credential, destructive-action or approval authority.
Keep repo work in the native WSL checkout and preserve unrelated/untracked work.

## Efficient failure-batching workflow

Use this instruction for implementation, diagnosis and repair, within the user's authorized scope:

> Work in bounded, evidence-driven repair batches. First map the changed code to affected features, consumers, trust boundaries, user states and tests. Gather and deduplicate related failures in one safe diagnostic sweep before editing. Refine the Spec-Kit tasks and analysis for the whole repair batch, add reproductions, implement the related fixes, and validate all affected areas together. Run the required full release gate only after targeted checks, coverage review and visual review are ready. Preserve security, rollback and evidence requirements; optimize redundant work, not assurance. Continue safe authorized work until acceptance is met or a real blocker requires user direction. Never equate passing tests with proof that no unknown defects exist.

### Required repair loop

1. **Establish scope and budget.** Read the active task ledger, current diff and latest
   compact result first; avoid rereading whole histories or large logs. Record the
   candidate source, environment, affected surfaces and a bounded test/run budget.
   Do not start unrelated features, agents, paid resources or provider actions.
2. **Discover before patching.** Check prerequisites first. Then run independent,
   relevant diagnostics to collect actionable failures rather than stopping at the
   first ordinary assertion. Skip dependent checks whose prerequisite failed and
   mark them blocked, not passed. Stop unsafe work immediately on possible secret
   exposure, unauthorized access, data corruption or destructive ambiguity.
3. **Keep one issue ledger.** For each unique failure, record severity, reproduction,
   evidence path, likely root cause, affected consumers, regression test and status.
   Group cascading symptoms by root cause without discarding individual failures.
   Distinguish product bugs, fixture/evidence drift, infrastructure faults and
   unavailable prerequisites. Preserve the first failure; passing a retry does not
   erase an intermittent defect.
4. **Refine one repair batch.** Use tasks -> analysis -> additional/fixed tasks ->
   analysis until no known blocking gap remains for that batch. Include adjacent
   consumers of shared components, negative/security cases and recovery behavior.
   Add failing regression tests first (or alongside a refactor). Do not chase
   unrelated issues indefinitely; record them and explain any release blockers.
5. **Validate in cost order.** Run static/contract and focused unit checks, then
   affected integration and browser checks, then the mandated complete gate.
   Check changed-line coverage before the expensive gate without lowering floors.
   Shared UI edits require relevant pages, generated profiles, responsive states,
   light/dark user preferences, accessibility, loading/error/disabled states and
   screenshots. Verify the test actually enters its named state.
6. **Review visuals before baselines.** Inspect actual captures and differences;
   fix layout, contrast, clipping, readiness and interaction defects first. Update
   baselines only for intentional reviewed design changes, never just to clear
   failures. Bind evidence to all relevant style/theme sources. Keep automated
   acceptance and any required owner visual approval separate.
7. **Reuse evidence only when valid.** Use the repository's supported assurance
   runner/cache. Reuse only evidence whose declared source/dependency, configuration,
   toolchain, fixture/profile and environment inputs remain valid. Otherwise rerun
   affected checks. Never hand-edit a pass receipt, weaken a gate, relabel a blocked
   test or substitute stale evidence where exact-source validation is required.
8. **Bound retries and concurrency.** Rerun a failed check only after a relevant
   correction, or one documented diagnostic retry when policy permits and the
   operation is safe/idempotent. If the same root failure recurs after repair,
   pause that loop and reassess the cause. Do not run heavy suites concurrently
   against shared builds, databases or browser outputs. Never edit tested inputs
   during a running suite. Follow existing resource and approval limits.
9. **Deploy once the candidate is ready.** Finish local validation before provisioning
   a paid preview. Use the supported deployment path, exact approved source,
   bounded TTL/cost, rollback and teardown. Keep a healthy authorized environment
   only when safe to reuse within its lease; rebuild only for a justified isolation,
   infrastructure or clean-deploy requirement. Never extend a lease or leave idle
   resources merely to avoid another setup.
10. **Report compactly and truthfully.** Per round, report unique issues found/fixed/
    remaining, passed/failed/blocked checks, evidence paths, elapsed time, full-gate
    and deployment counts, and the next action. Use measured token/cost data when
    available; label estimates and do not invent savings. Keep detailed sanitized
    logs outside chat and never expose secrets. Preserve failure exit status through
    cleanup, and use existing authorized notifications for actionable blockers.
    Completion requires current required evidence and explicitly listed residual
    risks, not a promise of 100% coverage of unknown problems.

This is an agent operating policy, not an installed scheduler or automatic enforcement.
Changes to test orchestration, caching, failure aggregation or notifications still
require their own scoped implementation and tests.
