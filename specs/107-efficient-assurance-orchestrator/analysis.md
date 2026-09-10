# Analysis: Efficient Assurance Orchestrator

## Cycle 1 — Initial completeness review

The first pass identified four risks common to test-selection systems: hidden transitive dependencies, forged or stale cache entries, optimization claims based only on omission, and a fast path that could accidentally replace release authority. The specification now requires an explicit transitive graph, exact input-bound private receipts, mutation-based escaped-fault proof, and unconditional delegation to the existing complete gate for release.

It also identified token reduction as a separate product requirement from runtime reduction. Output budgets, private full logs, deterministic summaries, and estimated token metrics are therefore first-class requirements rather than incidental formatting.

Finally, prior workstation instability makes unconstrained parallelism counterproductive. The plan orders cheap/high-signal checks first, defaults to conservative serialization, and permits concurrency only through explicit measured resource classes.

## Cycle 2 — Developer-state and trust-boundary review

Reviewing the tasks against real iteration exposed additional gaps. Developers need useful selection before committing, while release evidence must remain exact and reproducible. Planning and focused/standard execution may therefore admit a dirty worktree only by hashing every changed member and disabling reuse; full and release remain clean-HEAD only. The default comparison base must be a verified local merge-base and must never trigger a fetch.

The graph also needs self-protection: changes to tests, the orchestrator, graph, schemas, wrappers, coverage, or CI policy must select their own validators and raise the tier. Deletions and renames must account for both paths. Hosted-check validation consumes an explicitly supplied sanitized export and has no ambient network authority.

Finally, benchmark receipts must distinguish estimated avoided work from actually measured work so speed claims cannot be manufactured. T053-T060 close these gaps before implementation.

## Cycle 3 — Evidence recovery and coverage-impact review

The first implementation made selection visible but exposed five correctness gaps. Flat cache members can leave an orphan after power loss; status can select an incomplete lexically ambiguous run; a large change set can exceed the compact-output budget; cache identity must include the actual executable toolchain; and generic style/shared-component changes need a stronger visual floor than the Operations-only journey.

The correction uses atomic per-input cache directories, bounded recovery of private incomplete stages, nanosecond-ordered runs, current-source-aware status, reason count/digest with bounded examples, executable identity hashing, and explicit operations versus global visual surfaces. Failure and interruption receipts remain visible while ordinary application failures remain single-attempt. T061-T070 cover these boundaries.

## Cycle 4 — End-to-end waste review

Reviewing actual Feature 106 evidence showed that every hosted job ran twice: once for branch `push` and once for `pull_request`. That consumes time without independent assurance. Hosted workflows will keep pull-request checks and main-branch push checks while suppressing duplicate branch-push runs; superseded same-workflow runs will be cancelled safely. Required job names and branch protection remain unchanged.

The review also found that authentication, authorization, tenancy, and privacy paths need explicit full-tier mappings rather than relying on unknown-path escalation, and wall-clock run names are not strictly monotonic. T071-T078 add explicit sensitive mappings, integrity-bound sequence allocation, trigger tests, and a measured duplicate-run proof. This completes the pre-implementation task-analysis cycle with no unresolved requirement gap.

## Cycle 5 — Executable and path admission review

Implementation review found that relative managed-environment executables would resolve against a check-specific working directory and that an ambient `PATH` could select a different executable after its identity was recorded. The runner must resolve every fixed executable to an absolute regular file, bind that identity, execute that path, and provide only a reconstructed allowlisted tool path to children.

Git can also expose unusual filenames or decoding failures. All diff members and both rename paths must be normalized repository-relative printable POSIX paths before mapping or rendering. T079-T084 add these corrections and adversarial tests; no caller-controlled command or environment is introduced.

## Cycle 6 — Runtime dependency identity review

Executable hashing alone does not identify installed Python packages or frontend dependencies. A clean source with a mutated virtual environment or `node_modules` tree could otherwise reuse stale evidence. Cache bindings will include deterministic installed-package manifests for the exact managed Python runtime and the installed frontend lock, while non-cacheable Docker/security/release checks remain fresh.

The hermetic temporary HOME also needs an explicit private Playwright browser path on this workstation; otherwise visual checks can fail only because browser binaries become invisible. T085-T090 close dependency drift and browser-tool discovery without inheriting credentials or ambient configuration.

## Cycle 7 — Retry and measurement fidelity review

Final requirement reconciliation found that the initial executor correctly avoided broad retries but had not yet reused the existing exact native-corruption classifiers promised by FR-020. It now permits one additional attempt only for those code-owned classifiers; timeouts, launch failures, assertion failures, and all ordinary failures remain single-attempt.

The benchmark also needed a genuine routine-fixture median instead of one documentation sample, and traceability needed the tasks introduced by cycles 4-6. T091-T096 add the bounded retry proof, three-fixture measured median, complete traceability, and final static closure. No unresolved implementation gap remains before exact-commit acceptance.

## Cycle 8 — Publication-path integration review

The first publication attempt showed that the legacy pre-push hook still launched the complete Docker stream after exact release evidence had already passed. That duplicated work, emitted excessive output, and bypassed the new entrypoint. The hook now uses automatic compact assurance, and a clean exact-commit complete-gate receipt is admitted as stronger evidence with zero repeated checks. Dirty state, a different commit, tampering, missing checks, or failed checks cannot reuse it. T097-T100 close the real publication path and prevent this regression.
