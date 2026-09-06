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

## Honest residual boundary

Repository evidence validates deterministic fakes, PostgreSQL RLS/migration
behavior, browser accessibility and visual contracts, and zero-provider local
gates. It does not establish hosted CI, independent review, live object-store or
scanner behavior, provider deployment, cost controls, teardown, or empty live
inventory. Those remain B019-B024 and require their separately approved source,
merge, and provider boundaries.
