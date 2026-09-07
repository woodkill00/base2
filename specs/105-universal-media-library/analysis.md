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
21. Fresh independent review correctly rejected closure despite the green
    matrices. Deployment did not activate or provision the required isolated
    inspector; governance attempted unbound mutations forbidden by its own RLS;
    legacy worker-bypass policies remained on assets and variants; transient
    inspector failures had no durable retry path; and client interleavings could
    duplicate upload attempts, lose cancellation control, apply stale detail
    responses, permit stale metadata saves, or lose focus after confirmation.
    Compact and alternate-theme modal proof was also incomplete. B039 was
    reopened, and B041-B050 make remediation, real PostgreSQL/compose/browser
    proof, exact-head hosted checks, and repeated independent review mandatory.
22. The first post-remediation complete gate passed every product, database,
    browser, security, coverage, dependency, and visual check but correctly
    rejected the expanded task ledger because `validate_plan.py` still required
    exactly 40 identifiers. The validator now requires the complete ordered
    B001-B050 sequence and a matching total status count, preventing either an
    omitted remediation task or an undocumented extra task from passing.
23. The corrected exact-head gate then passed all 89 required checks, and 100
    consecutive runtime plus 100 consecutive client critical repetitions also
    passed. Hosted push and pull-request matrices passed every product check
    except one push-side smoke runner, which exhausted six retries before any
    container started because anonymous public ECR returned rate-limit errors;
    the duplicate smoke on another runner passed. E2E service images now use
    Google Cloud's documented Docker Hub mirror with exact PostgreSQL and Redis
    digests, image build arguments use the same mirror, and a CI-policy test
    forbids regression to the rate-limited endpoints. The remaining Node 20
    upload-artifact annotation was closed with the exact official v6 Node 24
    action pin.
24. The mirror-corrected hosted matrix passed all 37 applicable jobs with one
    intentional Storybook skip, but fresh exact-head review again rejected
    closure. Exact lifecycle replay was checked after stale-version rejection;
    scan discovery had no lease or attempt token, allowing duplicate delivery
    to consume retry budget; and the client discarded the inspector's permanent
    rejection code. Review also retained low-severity RTL English ordering and
    remaining anonymous public-ECR PostgreSQL dependencies. B051-B055 require
    each behavior and regression proof before the final B050 cycle can close.
25. Integration review caught a result-vocabulary mismatch after the first
    lease repair: the task's governed worker and the retained legacy worker did
    not return identical terminal labels. Completion now accepts both fixed
    vocabularies, atomically reconciles already-persisted governed state or
    completes a still-running legacy lease, and immediately releases unexpected
    exceptions into bounded durable backoff. Unit, task, and real-PostgreSQL
    checks cover clean, infected, transient, duplicate-token, concurrent
    scheduler, expired-lease, and recovery-storage-failure paths. The critical
    repetition runner now includes the late replay, marker, lease, duplicate,
    and recovery regressions rather than relying only on the original suite.
26. The first exact-head review after those repairs cleared UX but rejected
    code/security closure. A governance transition could race a claimed scan
    into an ineligible state and strand its running job; delayed exact replay
    after purge was unreachable. Reusable delivery grants lacked admission
    before whole-object reads, and unbounded unique export requests plus global
    FIFO discovery allowed resource exhaustion and tenant starvation. The
    inspector build also retained mutable upstream package inputs without a
    built-image SBOM/scan proof. B056-B060 convert all five findings—including
    the two low findings—into implementation, real concurrency/fairness, and
    supply-chain regression work before another exact-head review.
27. Remediation now terminally supersedes and audits an ineligible claimed scan,
    preserves exact replay after purge, and denies changed or new purged-state
    mutations. Whole-object reads are admitted before materialization through
    principal/tenant rates, one slot per process, and a two-worker/150 MiB
    invariant; limiter loss fails closed with typed 503 responses. Export replay
    precedes an atomically locked tenant quota, while ranked discovery gives
    each tenant a first turn before a second. The inspector uses a digest-pinned
    base, dated Debian snapshot, exact apt versions, hash-required wheels, and a
    hosted built-image SBOM/blocking scan. Real PostgreSQL exposed and closed NUL
    advisory-key and psycopg percent-escaping errors; the first image smoke also
    exposed and closed an inaccessible user-site installation. B056-B060 and
    their critical repetitions now cover every discovered path.
28. The first hosted built-image scan correctly rejected B060 rather than
    turning configuration presence into a false pass. Both push and pull-request
    variants found numerous high/critical vulnerabilities in the Debian 12,
    Python, ClamAV, FFmpeg, and transitive system package set. The other hosted
    jobs passed, but B060 is reopened until a supported/minimized immutable
    image passes the actual blocking hosted scanner without suppressions or
    allowlists. The downloaded SARIF/SBOM remain private diagnostic evidence;
    no vulnerable image was deployed or published.
29. A functional follow-up found that a green shell smoke would not have
    exercised the actual supervisor, signed spool protocol, runtime definition
    freshness, updater isolation, architecture, or representative decoder
    paths. It also found mutable APK resolution and insufficient cgroup
    headroom for authentic definitions. B061-B066 therefore require a
    digest-pinned non-root updater, a true main-loop/client/receipt E2E,
    24-hour fail-closed readiness, package-bearing immutable stages, an explicit
    amd64 boundary, measured resource headroom, representative formats and
    size boundaries, and another complete independent closeout cycle.
30. The immutable inspector follow-up replaces runtime package-manager
    resolution with digest-pinned package-bearing stages and checksum-bound
    artifacts, while enforcing linux/amd64 at build and runtime. The updater is
    separately digest-pinned, non-root, read-only, network-minimized, and
    resource bounded. A true networkless supervisor/client E2E now verifies a
    signed clean receipt, deterministic EICAR rejection, dropped-child key
    absence, no-new-privileges, zero effective capabilities, fresh authentic
    definitions, representative image/PDF/audio/video handling, a 100 MiB
    admission boundary, and measured cgroup headroom. Focused lint, typing,
    policy and runtime tests pass; the rebuilt amd64 image has zero critical or
    high Grype findings without suppression. B066 remains open for hosted and
    independent exact-head closeout rather than treating local evidence as a
    substitute.
31. Independent review found two final proof gaps despite the green container
    gate. The updater health could outlive a failed background freshclam
    process because PID 1 only tailed forever, and the child-isolation probe
    checked only its own sanitized environment rather than attempting access to
    the privileged supervisor. B067-B068 require foreground freshclam as the
    container lifecycle, exact command identity, detached-signature validation,
    embedded-date and monotonic-advancement bounds, writable-volume and failure
    drills, plus direct denied reads of supervisor environ, memory, and root-only
    signing-material paths from the actual dropped child.
32. The bounded offline updater acceptance now proves foreground freshclam is
    PID 1 with the exact expected arguments, authenticates all three detached
    CVD signatures, requires an embedded definition date no older than 24
    hours, persists monotonic advancement state, and fails for wrong volume
    permissions, non-advancement, command drift, and process death. The rebuilt
    inspector's actual dropped child is denied direct and supervisor-root paths
    to a root-only signer probe as well as `/proc` supervisor environment and
    memory, while retaining the established keyless/capability/no-new-privilege
    properties. B067-B068 are complete; B066 still requires hosted and
    independent exact-head closeout.
33. Final topology review found the least-privilege updater still shared the
    application bridge despite requiring only outbound definition retrieval.
    B069 moves it to one dedicated non-internal egress network and requires
    structural proof in both Compose profiles that no API, database, broker,
    proxy, worker, or other application service can become its network peer.
34. Both runtime profiles now attach only the updater to the dedicated
    `clamav_egress` bridge. It remains non-internal so freshclam can retrieve
    signed upstream definitions, while no application service shares its DNS,
    broadcast, or direct container-peer boundary. Structural policy tests,
    rendered Compose validation, and the complete offline updater failure drill
    pass, completing B069 without changing inspector or application networking.
35. The first exact-commit complete gate after B069 found one obsolete runtime
    assertion that still required the updater to join `app_network` with its
    former 3 GiB daemon allocation. B070 replaces that stale expectation with
    the digest-pinned, non-root, capability-dropped, read-only, 256 MiB
    updater-only egress contract. This was a useful fail-closed test-contract
    finding; no production code path failed. The same gate also recovered one
    host Python/coverage segmentation fault on its bounded retry, which remains
    recorded separately from the deterministic assertion failure.
36. Final independent review found one low defense-in-depth availability gap:
    the privileged inspector followed producer-controlled spool paths and read
    them before enforcing size. B071 requires directory-descriptor-relative
    `O_NOFOLLOW` admission, regular-file type, owner, mode, and size checks
    before a bounded read, plus live supervisor proof that `/dev/zero` symlinks
    and FIFOs fail immediately without blocking, leaking, or killing service.
37. B071 now opens the root, job directory, claim, and every input relative to
    already-validated directory descriptors with `O_NOFOLLOW`; it requires the
    configured producer UID, restrictive modes, regular-file type, and bounded
    `fstat` size before any read. Unit tests reject symlinked and unsafe job
    directories, `/dev/zero`, FIFO, and oversized sparse content in under one
    second. The rebuilt networkless supervisor rejects the same hostile inputs,
    remains alive, then completes the signed clean/infected representative-media
    E2E. The prior low finding is closed.
38. Independent review of B071 found that a Docker-created named volume starts
    root-owned and therefore denied the fixed UID-1000 producer, while terminal
    files created by the root signer were not constrained to that producer.
    B072-B073 require a real fresh-volume, two-identity acceptance boundary:
    one bounded initializer may hold only `CAP_CHOWN`, and the long-lived
    supervisor must create claims and terminal files as the producer rather
    than granting world or broad discretionary-access permissions.
39. Both Compose profiles now gate the inspector and worker on a networkless,
    read-only, one-shot spool initializer that changes the empty volume to
    exact owner `1000:1000` and mode `0770` using only `CAP_CHOWN`. The
    long-lived root signer retains only its existing identity-drop capabilities,
    traverses producer input through supplementary group 1000, and temporarily
    adopts UID 1000 only for atomic claim/terminal creation at mode `0600`.
    A fresh named-volume E2E proves exact ownership and modes, signed clean
    success, deterministic infected permanent failure, crash residue blocking,
    bounded retry after residue removal, and supervisor survival. No network,
    writable root filesystem, world access, or signing-key access was added.
40. Review of the two-identity boundary found that its initializer would repair
    arbitrary pre-existing ownership/modes and that a crash-created `claimed`
    or atomic-write temp file had no production recovery path. B074-B075 narrow
    initialization to one auditable fresh-state transition and require bounded,
    age-safe local recovery whose stale threshold exceeds both the maximum
    client wait and maximum inspection runtime.
41. Provisioning now no-ops only at exact `1000:1000/0770`, converts only an
    exact fresh `0:0/0755` named-volume root using chmod-before-`CAP_CHOWN`, and
    rejects every other state. Recovery scans at most 256 entries and executes
    at most one claimable job per poll, waits 180 seconds (60-second client maximum plus 60-second
    processing maximum plus a 60-second margin), and unlinks only exact stale
    producer-owned `0600` regular claims and four named size-bounded temp files.
    Active, symlink, FIFO, oversized, foreign-owner, terminal, and unknown-temp
    states remain untouched. A fresh-volume test runs initialization twice,
    rejects a third state, persists crash residue while the supervisor is down,
    restarts it, observes automatic retry without client unlink, and proves the
    supervisor survives both valid and hostile residue.
42. Final availability review found that slicing the first 16 ready entries
    before claim admission let preserved terminal or unrecoverable claimed jobs
    consume the candidate budget forever. B076 separates the raw-entry window
    from execution: one process-local descriptor-relative scandir cursor reads
    at most 256 raw entries per poll, advances across non-actionable entries,
    closes and resets at EOF or root replacement, and permits only an actually
    claimed job to consume the single execution slot. More than 256 preserved
    terminal entries now coexist ahead of a valid stale recovery without
    starvation. Focused tests also cover continuous arrivals, deletion under an
    open cursor, EOF reset, simulated process restart, and descriptor cleanup.
43. The next exact-head security review found that stale-claim recovery still
    materialized every name inside one producer-controlled job before checking
    its 16-entry bound. B077 replaces that allocation with descriptor-relative
    streaming iteration, rejects as soon as entry 17 is observed, and requires
    iterator closure plus live cgroup-contained supervisor survival with a
    4,096-entry hostile job followed by valid recovery work.
44. The same review found that production Compose declared a bare writable
    inspector `/tmp` even though CI exercised a bounded hardened tmpfs. B078
    applies `rw,nosuid,nodev,noexec,size=64m` in both runtime profiles and adds
    rendered-manifest assertions so production and acceptance cannot drift.
45. The first hosted B077 proof exposed a cleanup-only race: its producer
    recursively removed the crowded directory while the still-live supervisor
    could retain a scan descriptor. B079 leaves those final fixtures inside the
    exact disposable volume until the shell trap stops the supervisor and
    removes the whole volume, eliminating concurrent traversal mutation.
46. Because that primary E2E failure skipped image scanning, the always-run
    result adapter also received an empty SARIF path and emitted a misleading
    secondary traceback. B080 conditions media-inspector normalization on a
    real scanner output path; the primary step remains failed and visible while
    absent evidence is never fabricated or parsed as the repository root.
47. Exact-head re-review found B079 had removed only the final crowded-fixture
    cleanup while earlier producer phases still recursively deleted processed,
    recovery, hostile, and terminal directories under the live supervisor.
    B081 removes all producer-side recursive spool deletion and enforces its
    absence; the exact shell trap is now the sole cleanup owner and always stops
    the named supervisor before removing the disposable named volume.
48. Retaining every fixture then invalidated the crowded proof's one-window
    premise because the later recovery phase contains more than the 256-entry
    raw scan cap. B082 moves crowded-plus-sentinel validation before bulk
    recovery staging, where all existing terminal and proof entries fit in one
    window and explicit ready mtimes deterministically order crowded first.
49. Both clean-runner hosted security jobs then exhausted the updater test's
    ten-attempt readiness loop while the digest-pinned image initialized its
    fresh definition volume. B083 retains a finite fail-closed budget but raises
    it to 60 attempts and emits exact container logs on death or timeout, so
    slower first startup is admitted without silent or unbounded waiting.
50. Reproducing the delay under trace showed the authentic `sigtool` child was
    OOM-killed while verifying `main.cvd` inside the updater's 256 MiB cgroup;
    retry count could not repair that. B084 raises only this updater boundary to
    512 MiB, aligns the production health timeout at 30 seconds, and replaces
    attempt counting with a 120-second wall-clock deadline plus 30-second probe
    caps. Early death and deadline exhaustion retain explicit diagnostics.
51. A higher-memory trace then showed the next failure was the intended
    freshness check: the immutable embedded CVD crossed 24 hours during this
    work. B085 keeps production health on real time but lets the networkless
    acceptance pass one explicit numeric reference epoch derived from the
    signed CVD timestamp. Signatures, advancement, liveness, configuration,
    ownership, and stale-state rejection still execute unchanged.
52. Independent review found that the first and second scanner-identity reads
    were outside the stated readiness deadline and that a final fixed-length
    health probe could overrun it. B086 establishes one 120-second evidence
    ceiling before any updater operation, reserves six seconds inside it for
    five-second SIGKILL grace plus clock/sleep granularity, caps every evidence
    operation at the smaller of 30 seconds or the remaining operational budget, parses scanner identity only
    after successful bounded capture, and then gives exact container and volume
    teardown two separately bounded ten-second commands with five-second kill
    grace. The evidence phase cannot exceed 120 seconds; cleanup has an explicit
    maximum 30-second allowance rather than being misrepresented as part of
    that ceiling. A reduced-budget fake Docker client that ignores SIGTERM is
    killed and the whole script exits within its equivalent evidence ceiling
    plus explicit cleanup allowance. Expected negative health results remain
    distinct from timeout and cannot accidentally satisfy a rejection proof.
53. The exact-head complete gate then exposed a stale independent runtime-policy
    assertion that still required the superseded 256 MiB updater ceiling even
    though the measured signature-verification minimum and every other contract
    now require 512 MiB. B087 aligns that assertion while retaining its checks
    for explicit opt-in, updater-only egress, no published port, read-only root,
    capability drop, PID limit, CPU limit, and immutable health command.
54. Both hosted SBOM variants subsequently passed the updater lifecycle but
    failed when the separate immutable-image supervisor E2E applied today's
    clock to its intentionally frozen embedded CVD. Production does not use
    that isolated fixture: it mounts the updater-owned definition volume and
    waits for its no-argument, real-time health check. B088 gives only the
    networkless acceptance entrypoint an explicit numeric reference derived
    from the embedded CVD's parsed signed timestamp, binds supervisor receipts
    and client verification to the same historical instant, and asserts that
    neither production Compose profile can invoke the test entrypoint or pass a
    reference-clock argument. Freshness rejection remains covered separately,
    while the immutable scanner/decoder/spool E2E no longer expires with wall
    time. Review then found the test helper was present in the default image
    because its Dockerfile copied the full API tree. The final split explicitly
    copies only the inspector's production dependency closure into the
    production target, layers the three acceptance harnesses into a separate CI
    target, SBOM-scans only production, and executes an image-level absence
    assertion. Both the representative-media and real two-UID spool E2Es use
    the acceptance target and the same CVD-derived clock; no reference-clock
    code exists in the production artifact.
55. The exact B088 complete gate exposed two independent acceptance-only
    regressions: direct test monkeypatch assignments violated the strict mypy
    module contract, and one Chromium light-theme run observed focus before the
    nested confirmation dialog had committed its removal. B089 uses explicit
    dynamic `setattr` only in the isolated test harnesses, while production
    remains statically unchanged. The UI now records successful-return intent
    before closing the alert dialog and restores focus from an effect after the
    state commit, avoiding an animation-frame race with modal teardown. Focused
    type checking, unit coverage, and repeated light-profile browser execution
    prove both corrections before another exact-head complete gate.
56. Independent UX review of B089 found a deeper pending-operation edge: the
    confirmation remained dismissible and repeat-activatable while its request
    was unresolved, which could leave a stale focus-return flag and issue two
    transitions. Its success status also lived outside the modal subtree and
    was inert to assistive technology while asset detail remained open. B090
    adds a synchronous single-owner guard plus visible pending state, disables
    both confirmation controls and ignores Escape until the bounded request
    settles, and renders the completion live region inside the active detail
    dialog. A deferred-promise regression covers double activation, Escape,
    settlement, focus, and announcement. The exact visual-review manifest is
    then rebound to the committed UI source after the full matrix passes.
57. Re-review found native `disabled` removed the focused confirmation button
    from Chromium's focus order while a slow request was pending, leaving the
    nested modal with no focusable descendant. It also found that a failed
    attempt used the outer detail error and could survive a successful retry.
    B091 retains focusable buttons with truthful `aria-disabled` state while
    synchronous guards reject activation and dismissal, scopes transition
    failure to the alert dialog, and clears it before retry. A deferred browser
    route now holds the request while focus containment, Escape resistance,
    Axe results, and the pending visual are checked before settlement; a unit
    regression proves failure, guard release, successful retry, and removal of
    contradictory error copy.
58. Both hosted backend variants then rejected the B089 test-only `setattr`
    calls under Ruff B010 even though strict mypy required their dynamic typing.
    B092 documents the intentional test-module patch at each exact call site,
    retaining mypy safety without weakening B010 repository-wide. It also adds
    the same required `ruff check api` command to the local complete gate and
    surface-drift lock, closing the local/hosted parity gap that allowed the
    failure to appear only after publication.
59. Exact head `179edae87bab393d504e7df45ad3898f3424939f`
    passed the expanded 90-check complete gate with an empty failed list and
    then passed 100 consecutive critical media repetitions. Independent code,
    security, and UX reviews each reported C0/H0/M0/L0. Both hosted trigger
    variants passed API, Django, PostgreSQL integration, contract, E2E,
    frontend, smoke, repository, audit, license, leak, static-analysis,
    supply-chain, and production-image SBOM/vulnerability jobs. The two SBOM
    jobs completed in 3m49s and 4m06s, proving the immutable acceptance clock
    no longer expires while the scanned production image excludes acceptance
    helpers. This closes B020, B039, B040, B050, B060, and B066 without granting
    merge, provider, DNS, certificate, deployment, teardown, or live authority.

## Honest residual boundary

Repository evidence validates deterministic fakes, PostgreSQL RLS/migration
behavior, browser accessibility and visual contracts, isolated real scanner
containers, hosted CI, independent review, and zero-provider local gates. It
does not establish live object-store behavior, provider deployment, cost
controls, teardown, or empty live inventory. Those remain B021-B024 and require
their separately approved merge and provider boundaries.
