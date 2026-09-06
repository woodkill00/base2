# Evaluation record

The initial design was evaluated repeatedly against architecture, security,
data integrity, accessibility, operations, and teardown concerns. Corrections
added mixed-format policy, scanner freshness, quotas and backpressure,
encryption/key identity, legal hold and data rights, eventual-consistency
reconciliation, abuse review, disabled-route absence, and explicit visual
review sidecars. The implementation pass then found and corrected legacy status
compatibility, generator one-shot choices, raw-SQL defaults for new non-null
fields, mixed-media legacy-size coupling, and derivative recipe provenance.

Known pending evidence is represented as unchecked work in `tasks.md`; it is not
silently classified as complete. Finite tests reduce specified risk but cannot
prove unknown defects impossible.

## Implementation evaluation cycles

1. The first complete gate found that the disposable checkout violated the
   existing `/home`-resident WSL admission boundary, that one interaction-pack
   test did not load the Media module's dependency closure, and that a combined
   media test used the FastAPI interpreter to collect a Django model test. The
   checkout was moved under `/home/woodkill/code`, the dependency fixture was
   closed, and the gate now uses separate FastAPI and Django interpreters.
2. The second complete gate found a hard-coded `1.0.1` lifecycle checkpoint
   upgrade that was not newer than Media `2.0.0`, plus a flaky stitched
   full-page capture of the real sticky application header. The checkpoint now
   derives the next semantic patch version. The visual test proves the header
   is sticky, then makes it static only for deterministic full-page stitching;
   the corrected compact and landscape baselines were visually inspected and
   repeated without drift.
3. The third complete gate found that generated child repositories retained an
   enabled Media module without its required `content-workspace` dependency.
   The factory now resolves the complete transitive dependency graph, writes
   the effective ordered inventory into provenance and the child profile, and
   has a direct regression test.
4. The persistence expansion added governance, processing, portability,
   encryption-envelope, and abuse-review models through migration `0015`.
   Disposable PostgreSQL acceptance proved forward, reverse, repeat-forward,
   forced-RLS, runtime-role isolation, and bounded worker-role access.
5. The governed workflow pass added collections, reference/consequence
   inventory, optimistic metadata revisions, jobs and bounded retry, replay-safe
   lifecycle actions, and expiring export status. Its first complete gate
   correctly failed because changed-line coverage was 82.93% against the fixed
   90% floor.
6. Added transaction, outbox, scope, failure-redaction, and domain-status tests
   raised changed-line coverage to 90.28%. The corrected complete gate passed
   all 86 required checks with zero skips at commit
   `f7aced8a4448aae3a43453ddb2159467e6657a70`; evidence digest
   `9c53496c17832f9442b2a4d9f13fdc261fbdb0f549befc8ae1ff12f3927fcb1b`.
7. The exact critical media lifecycle, replay, governance, worker, and policy
   suites then passed 100 consecutive repetitions.
8. The final gap pass added signed stable cursors, bounded metadata history, a
   reusable focus-trapped picker, exact collection assignment, consequence-aware
   confirmations, immutable replacement and rollback with grant epoch rotation,
   deterministic audio waveforms, and active-content/page-bounded document
   probes. The enlarged lifecycle, replay, governance, worker, policy,
   processor, and storage matrix passed another 100 consecutive repetitions.
   The reviewed branch contains 119 tracked files across 24 commits and no
   committed credential or provider state. Three local virtual-environment
   links and generated gate artifacts remain untracked and are excluded from
   publication.
9. Independent code review rejected the green implementation because private
   visibility was not enforced within a tenant, upload admission was detached
   from the governed worker path, export selection was not consumed, and cursor
   signatures were not query-bound. Corrective tasks B025-B034 make each runtime
   boundary explicit instead of treating helper-level tests as integration proof.
10. Independent security review additionally found whole-body upload buffering,
    unused quota/backpressure controls, missing recent-auth age enforcement,
    insufficient tenant-bound worker writes, stale scanner evidence, and
    in-process hostile parsing. B026-B030 and B034 require negative integration
    tests, disposable PostgreSQL migration proof, and measured runtime evidence.
11. Independent UX review found broken light-theme contrast, incomplete dialog
    focus management, cosmetic cancellation, incomplete picker integration, and
    stale screenshots bound to an ancestor. B031 and B035-B037 require real
    interactions and source-bound reviewed visuals across the existing matrix.
12. Dependency review found two React Router advisories with no corrected 6.x
    release. B038 requires the supported patched major and a zero-finding audit;
    B039-B040 prevent completion until integrated gates and fresh independent
    review agree on the exact head.
13. The corrective implementation enforced owner-scoped private mutations,
    tenant-bound references and workers, recent-auth checks, signed query-bound
    cursors, selected-asset exports, governed lifecycle and audit behavior, and
    truthful accessible client interactions. Negative API, repository, worker,
    PostgreSQL, React, Playwright, and visual tests now exercise those boundaries.
14. Upload completion now preflights an owner-bound grant before consuming a
    body, admits at most one memory-bearing request per process, clamps objects
    to 25 MiB, enforces idle and total read deadlines, verifies exact length and
    digest, throttles attempts, and releases capacity on every terminal path.
15. Hostile inspection moved into a dedicated networkless, read-only container.
    A disposable unprivileged child with no capabilities or inherited secrets
    runs ClamAV and format decoders under resource limits. Ed25519 receipts bind
    the job, object version, source digest, measured tool identities, verdict,
    derivative, and configured build identity; the worker can verify but cannot
    forge them.
16. Fresh code, security, and UX passes closed every reported critical, high,
    and medium finding. The corrected suites passed locally, including the full
    frontend matrix, source-bound browser visuals, an actual hardened inspector
    image probe, and 100 consecutive repetitions of critical media boundaries.
17. The first corrected complete gate exposed two honest integration defects:
    nullable dimensions rejected by full-project typing and a stale Vite process
    occupying the visual-test port. Both were corrected and the exact gate was
    rerun. Its only remaining failure was 87.49 percent changed-line coverage
    against the fixed 90 percent floor; additional behavioral inspector tests
    raised coverage to 90.96 percent without exclusions.
18. The next exact-head complete gate passed all 87 required checks at commit
    `c4920854badcf30a57d02b72dcbe7429db00457f`. Hosted checks then found that
    `package.json` and `package-lock.json` disagreed about the patched `uuid`
    override. The lockfile was regenerated and a mandatory dry-run `npm ci`
    check was added to the complete gate so this class of packaging drift fails
    locally before publication. The final exact-head gate and hosted checks
    remain B039-B040 evidence and are intentionally not predeclared complete.
19. The lockfile-corrected candidate passed all 88 required complete-gate checks
    with zero failures at commit
    `4ec57c3d12b1fe4be0e6e446b621688bef5128fe`. The run covered the complete
    local, PostgreSQL, browser, type, security, dependency, packaging, coverage,
    and visual matrix. Result SHA-256:
    `3400841143d83ffe1fbb3afa7f6c85a32b5529df56579be4a26db9a601a809b1`.
    Hosted checks and final exact-head independent review remain required by
    B020 and B040; merge and provider work remain separately gated.
20. Hosted push and pull-request matrices at `709f0dd7` completed with 37
    successful checks, one intentionally non-applicable Storybook publication
    skip, and zero failures or cancellations. Both frontend, E2E, audit,
    licensing, smoke, backend, integration, contract, repository, and security
    variants passed. The runs exposed one non-failing GitHub annotation: the
    former checkout pin used the deprecated Node 20 action runtime. Every
    workflow now uses the exact official `actions/checkout` v5 commit
    `fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09`; CI-policy and surface-drift
    validation passed before the next exact-head complete gate.

## Honest residual boundary

Repository evidence validates deterministic fakes, PostgreSQL RLS/migration
behavior, browser accessibility and visual contracts, and zero-provider local
gates. It does not establish hosted CI, independent review, live object-store or
scanner behavior, provider deployment, cost controls, teardown, or empty live
inventory. Those remain B019-B024 and require their separately approved source,
merge, and provider boundaries.
