# Analysis Log: Universal Content and Data Workspace

## Cycle 1 - Product, reuse, and compatibility

Findings:

1. A generic CRUD surface would not cover schema evolution, workflow, versions, review, saved views, media, or generated-site reuse.
2. Separate models for blogs, rentals, products, and listings would duplicate tenant, permission, migration, and UI behavior.
3. Base2 already has module manifests and capability handling; a second preset vocabulary would drift.
4. Existing `/api/items` and Items UI are placeholders but may still be referenced by tests or generated sites.
5. A free-form page builder would enlarge scope and introduce executable presentation risks.

Corrections:

- Defined one canonical structured-content kernel with versioned declarative presets.
- Added schema compatibility preview, immutable versions, workflow, search/views, media, import/export, and generated experiences.
- Required composition of existing module IDs and explicit disabled-capability tests.
- Added a narrow deprecated Items adapter, migration notes, and removal gate.
- Kept arbitrary code, HTML, templates, and page building outside the feature.

Remaining review areas: security of rich data, jobs, uploads, and tenant scoping.

## Cycle 2 - Security, privacy, and data-loss review

Findings:

1. Arbitrary JSON, query operators, relationships, rich text, and render hints could become mass-assignment, injection, XSS, overfetching, or denial-of-service paths.
2. Application-only tenant filters are vulnerable to a missed predicate.
3. Public records could leak private fields or unsafe attachments.
4. File extensions and client MIME values do not establish safe content.
5. Remote media ingestion would add SSRF risk.
6. Fuzzy deduplication could incorrectly merge distinct listings or posts.
7. CSV exports can execute formulas when opened in spreadsheet software.
8. Retried imports, exports, transitions, and schedules could duplicate mutations.
9. Logs, visual fixtures, and job evidence could expose submitted content or private download URLs.

Corrections:

- Added closed field/query/render/workflow vocabularies and explicit complexity bounds.
- Required tenant/site composite keys plus PostgreSQL RLS and deliberate UUID/slug collision tests.
- Added per-field public projection and asset-state/visibility publication gates.
- Added signature verification, quarantine, malware scanning, derivative isolation, hostile fixtures, and safe delivery.
- Excluded arbitrary remote fetch.
- Made exact identifiers authoritative and uncertain similarity matches review-only.
- Added CSV formula neutralization and corresponding hostile tests.
- Added digest-bound idempotency, optimistic versions, transaction ownership, checkpoints, and terminal replay tests.
- Added redacted evidence and repository/artifact/screenshot/export secret scans.

Remaining review areas: migration/restore honesty and complete user/visual behavior.

## Cycle 3 - Migration, reliability, accessibility, and visual review

Findings:

1. Editing published schemas in place would make old versions ambiguous and rollback unsafe.
2. Additive database migrations alone do not prove content-definition migrations, generated-site upgrades, or object-store restore.
3. Green container health does not prove workers, indexing, media processing, imports, or exports complete correctly.
4. Screenshot diffs alone do not prove focus, keyboard, announcements, overflow, targets, image fit, or interaction.
5. Running an unconstrained cross-product on every commit would waste resources and may hide skipped coverage.
6. “100% testing” cannot truthfully promise the absence of unknown future defects.
7. Planning could appear complete while a requirement lacks a real implementation, test, or evidence path.

Corrections:

- Made published definitions and record versions immutable and restoration append-only.
- Added content migration classification, compatibility preview, recovery windows, generated-site upgrade/downgrade, backup manifests, and isolated restore comparison.
- Added dependency/failure injection, restart, replay, terminal-state, and redacted worker evidence.
- Added behavioral assertions paired with screenshots and explicit visual review sidecars.
- Split representative pull-request coverage from expanded release coverage while forbidding silent required skips.
- Defined completeness as total specified traceability, direct critical-branch coverage, and regressions for discovered defects.
- Added a validator for exact requirement count, sequential tasks, completion honesty, traceability columns, boundaries, and unresolved markers.

## Cycle 4 - Task graph and authority review

Findings:

1. The initial task graph did not make the constitutional Django -> FastAPI -> React order mechanically obvious.
2. Media/import/export worker work could be implemented before repository transaction semantics were proven.
3. Compatibility removal could happen before generated-profile migration evidence.
4. Publication, merge, or live provider operations could be mistaken as implied by implementation completion.
5. Numeric performance limits chosen without measurement would be arbitrary.

Corrections:

- Reordered phases so canonical Django blocks SQL/API, which blocks workers/generator and then React.
- Placed worker implementation after API transaction/RLS tests.
- Made Items navigation removal depend on adapter, migration, and profile evidence.
- Separated publication, merge, and live canary into guarded Phase 10 and reiterated they are not pre-approved.
- Added repeatable maximum-workload measurement before numeric limits close.

**Current planning result**: `NO_UNRESOLVED_PLANNING_FINDINGS`

Implementation has not started. T019-T150 remain pending, and further implemented-system analysis is mandatory before publication or live acceptance.

## Cycle 5 - Exact repository-structure reconciliation

Findings:

1. Base2 already has concrete `sitecontent.ContentRecord`, `ContentRevision`, `MediaAsset`, `MediaVariant`, search documents, public routes, and a PostgreSQL repository. The initial wording could be read as permission to create duplicate record and asset systems.
2. The current tenant middleware maps authenticated tenant context to canonical `site_id`; adding both `tenant_id` and `site_id` now would create competing ownership identities.
3. The draft API base omitted Base2's established `/api` prefix and did not explicitly retain existing `/api/content`, `/api/search`, and `/api/media` public reads.
4. One Django test path targeted a nonexistent `django/common/tests` directory.
5. Two traceability ranges used inconsistent two-digit end labels.

Corrections:

- Required in-place evolution of the existing `sitecontent` records, revisions, media entities, repository, and routes; shared primitives still begin in `common/models.py` as required by the constitution.
- Defined authenticated tenant equality to canonical `site_id` and prohibited a second parallel ownership identifier in this feature.
- Corrected the authenticated base to `/api/content/v1` and retained existing generated public-read surfaces during migration.
- Corrected test and implementation destinations to real repository paths.
- Normalized all task ranges to three-digit identifiers.

**Final planning result after repository reconciliation**: `NO_UNRESOLVED_PLANNING_FINDINGS`

Implementation remains unstarted. T019-T150 remain pending, and publication, merge, or live-provider work remains separately governed.

## Cycle 6 - Physical schema ownership review

Finding:

1. Base2's API test bootstrap explicitly declares that Django owns the database schema. The original Phase 3 wording could have caused an API SQL migration to create a second copy of workspace tables or conflict with Django's migration state.

Correction:

- Kept the Django `sitecontent` migration as the sole physical schema owner. FastAPI will consume those exact tables, and API parity tests will verify PostgreSQL constraints, indexes, RLS prerequisites, and migration inventory while expressly forbidding duplicate `api_content_*` domain tables.

**Cycle result**: `NO_UNRESOLVED_SCHEMA_OWNERSHIP_FINDINGS`

## Cycle 7 - Implemented-system evidence reconciliation

Implementation is active on the private feature branch. Django remains the sole physical schema
owner, including PostgreSQL row-level security policies, while FastAPI consumes that schema and
React consumes the authenticated API. Corrective tasks are appended contiguously after T150 so
each reproduced implementation defect retains a regression and evidence path. Publication,
merge, deployment, DNS, certificates, provider resources, and live acceptance remain unperformed
and separately governed.

**Current implementation status**: `IMPLEMENTATION_PUBLISHED_NOT_MERGED`

## Cycle 8 - Exact-head database isolation review

Finding:

1. The exact-head complete gate passed, but the workspace RLS check remained a static migration inventory. The deployed compose contracts still supplied the table-owning PostgreSQL role to FastAPI and Celery. PostgreSQL owners bypass ordinary RLS, so this could not truthfully satisfy the planned second tenant boundary or T038 even though repository predicates and transaction-local tenant binding were present.

Correction:

- Added T193 to split migration ownership from API/worker runtime, provision a least-privilege no-`BYPASSRLS` role, grant it only the workspace access it needs, and prove real cross-tenant behavior against PostgreSQL including pool reset and rollback paths.

Evidence:

- The disposable PostgreSQL acceptance passed twice with synthetic credentials and exact-owned teardown.
- The exact-head complete gate at `e2f94d8b5635d94f92c3ab464377918e6ab050ef` passed all 80 required checks with no failure; changed-line coverage was 90.84%.

**Cycle result**: `IMPLEMENTATION_FINDING_T193_CLOSED`

## Cycle 9 - Remaining acceptance-depth review

Findings:

1. Repository and bound-limit tests exist, but the disposable PostgreSQL evidence does not yet prove tenant-leading execution plans, fixed-query relationship expansion, or all planned two-connection conflict classes.
2. Export expiry exists, while complete workspace retention, exact-owned media cleanup, and integration into the existing privacy/data-rights flow are not yet evidenced.
3. Migration round trips cover the current workspace schema, but the planned current-main/populated/prior-profile/interruption matrix and runtime-role grant rollback are incomplete.
4. Component accessibility and global Base2 visual matrices pass, but there is no dedicated workspace screenshot corpus covering every planned state, viewport, input mode, theme, engine, manifest, and review sidecar.

Corrections:

- Added T194-T197 as contiguous corrective tasks. T105-T132 and implemented-system closeout remain open until these deeper acceptance contracts pass.

**Cycle result**: `IMPLEMENTATION_FINDINGS_T194_T197_OPEN`

T194 progress: the disposable PostgreSQL matrix now retains an actual planner
assertion showing tenant/type access through `sitecontent_type_version_uq`, and
the relationship repository is regression-tested to return 25 expansions with
one bounded `LIMIT 200` query. T105 is closed; the multi-connection mutation
matrix remains open under T106/T194.

T194 closeout: the disposable PostgreSQL matrix now launches two physical
least-privilege runtime-role sessions through a bounded barrier for each of six
critical collision classes. Definition publication, record mutation, workflow
transition, saved-view edit, import commit, and due-schedule firing each produce
exactly one affected-row winner and one zero-row loser. The disposable database
is destroyed even on failure, and the static contract locks the race classes,
physical barrier, and winner/loser assertion into the required gate.

**Cycle result**: `IMPLEMENTATION_FINDING_T194_CLOSED_T195_T197_OPEN`

## Cycle 10 - Retention prerequisite review

Finding:

- The workspace-role split accidentally placed the ordinary API pool's locked
  construction block after an unconditional workspace-pool return. Cached-pool
  tests passed, but a fresh ordinary process would receive `None` and fail at
  first database checkout.

Correction:

- Added T198 to restore the ordinary initializer in its own function and lock
  fresh construction with a regression that invokes the uncached path.

Evidence:

- The uncached constructor regression passed with the full 22-test tenant
  boundary module; the ordinary and workspace pools remain separately closed
  and every checkout is reset before reuse.

Follow-up finding:

- Celery workspace discovery still imports the owner-backed generic connection
  helper. Reusing the API runtime role for global discovery would either return
  no rows under RLS or require unsafe cross-tenant API visibility.

Correction:

- Closed T198 and added T199 for a distinct least-privilege worker discovery
  boundary followed by tenant-bound claims and disposable PostgreSQL proof.

**Cycle result**: `IMPLEMENTATION_FINDING_T198_CLOSED_T199_OPEN`

T199 closeout: a separate validated worker-only role now owns cross-tenant due
work discovery while retaining `NOSUPERUSER` and `NOBYPASSRLS`; every claimed
mutation continues to set the exact tenant locally. Interactive API containers
receive only the tenant-bound runtime credential. The migration owns the fixed
table grants and worker-aware policies, with a reverse path that revokes the
worker grants and restores tenant-only RLS. Disposable PostgreSQL proved the API
role sees zero rows without context while the worker discovers both synthetic
tenants, and the full tenant-boundary module plus static deployment contract
passed.

**Cycle result**: `IMPLEMENTATION_FINDINGS_T198_T199_CLOSED_T195_T197_OPEN`

T195 closeout: the encrypted store now deletes only a server-derived exact
tenant/object key after authenticating its digest, rejects owner mismatch and
tamper, and treats a missing exact object as a replay-safe no-op only when the
retention caller explicitly requests it. Daily cleanup holds row locks, skips
active relationship/media bindings, enforces the 30-day record recovery window,
removes expired unbound media variants/originals and export artifacts, and
retains append-only audit evidence. Privacy export and correction use the
tenant-bound non-owner role to project only subject-created records and
`content.read` fields; deletion removes mutable owner references, pseudonymizes
job subject references, and leaves append-only audit events unchanged. The focused 52-test
storage, worker, task, and data-rights suite passed, including replay.

**Cycle result**: `IMPLEMENTATION_FINDING_T195_CLOSED_T196_T197_OPEN`

T196 closeout: current Base2 `main` contains only `sitecontent` migration 0001,
which is the executable BASE used by the populated legacy-profile round trip.
SQLite proves the complete model migration forward, reverse to exact current-main
state, and forward again without losing the legacy record. A new disposable
PostgreSQL interruption matrix begins from an empty database, migrates to latest,
populates two tenants plus records/jobs, reverses only the worker-role checkpoint
to 0009, verifies every worker table grant is absent while runtime grants and
exact data counts remain, then resumes 0010 and verifies the grants/policy and
data return exactly. Both migration tests and the physical matrix passed.

**Cycle result**: `IMPLEMENTATION_FINDING_T196_CLOSED_T197_OPEN`

## Cycle 11 - Dedicated visual-assurance review

Findings:

1. The first ordinary screenshot replay failed closed on the landscape-touch Imports surface.
   The capture inherited a scroll offset from the longer Schema surface, making fixed navigation
   placement depend on the preceding tab height.
2. The original viewport matrix represented 400% reflow only implicitly through a 320 CSS-pixel
   compact viewport; the task requires an explicit, named assurance case.
3. The initial visual manifest enumerated rendered surfaces but did not bind the complete planned
   field, record-state, job-state, media, relationship, error, long-content, and RTL fixture
   vocabulary.

Corrections:

- Every post-navigation capture now resets to the document origin before geometry and image
  assertions. The corrected matrix passed two complete ordinary no-update replays.
- Added the explicit `chromium-400-zoom` reflow project and increased the exact matrix to 48 PNG
  members across 12 projects and four primary workspace surfaces.
- Added an executable fixture-vocabulary contract and bound that coverage into the deterministic
  visual manifest. Baseline mutation is absent from the ordinary package command and the separate
  updater requires the exact Feature 104 branch, a clean tracked tree, and explicit local-review
  authority.
- The integrity-bound contact sheet and representative full-resolution records, 400% schema, and
  high-contrast imports were reviewed for hierarchy, clipping, reflow, directionality, focus,
  control size, contrast, density, and navigation. No unresolved visual or accessibility finding
  remains.

Evidence:

- Two consecutive 24-test Playwright runs passed across Chromium, Firefox, and WebKit with no
  network dependency and no baseline mutation.
- The eight visual-manifest regressions passed, including tamper, missing-member, false-review,
  private permissions, and ordinary-command mutation refusal.
- Private reviewed evidence is retained under
  `.artifacts/workspace-visual/20260903T-feature104-reviewed/` and is not a live-deployment claim.

**Cycle result**: `IMPLEMENTATION_FINDING_T197_CLOSED_NO_UNRESOLVED_VISUAL_FINDINGS`

Follow-up finding:

- The dedicated workspace visual pack passed independently but was not a required node in the
  fixed complete-gate graph, so a future release could omit it while the older shared visual
  matrix remained green.

Correction:

- Added and closed T200. The complete gate now requires the workspace manifest/tamper contract
  and then the ordinary no-update 12-project browser matrix. Any missing dependency, image drift,
  unavailable browser, or nonzero test result remains explicitly non-successful.

**Cycle result**: `IMPLEMENTATION_FINDINGS_T197_T200_CLOSED`

## Cycle 12 - Exact-head complete-gate review

Findings:

1. The 82-check complete gate failed the API partition because a static policy assertion still
   required the pre-T199 API-only RLS object and therefore rejected the intended separate worker
   role fields.
2. The fail-closed surface inventory correctly rejected three changed configuration members:
   `.env.example`, the complete-gate graph, and the shared tenant-security policy.

Corrections:

- Added and closed T201. The regression now requires both least-privilege role boundaries and
  their combined fixed scope. The locked surface inventory is refreshed only after the focused
  policy, graph, and hostile-drift tests pass.

**Cycle result**: `IMPLEMENTATION_FINDING_T201_CLOSED_PENDING_GATE_REPLAY`

Gate replay evidence:

- The fixed complete repository graph passed all 82 required checks at exact source
  `c823d18a8cdb47341e38af9e413635d3fe5819ff`; there were zero failed, blocked, unavailable,
  skipped, or not-run checks. Changed-line coverage passed at 90.87% without lowering the 90%
  floor.
- The separately executed disposable PostgreSQL acceptance passed RLS/API/worker separation,
  query-plan and two-physical-session conflict assertions, reverse grant removal, forward grant
  restoration, and exact-owned container teardown.
- Backup/restore, retention, privacy, public projection, cursor/cache/export binding, redacted
  failure behavior, tenant/object authorization, replay, injection, unsafe-input, and formula
  neutralization are green through their required API, Django, React, recovery, identity,
  public-content, and workspace partitions.
- The repository's full Semgrep, Gitleaks, Syft/Grype, license, and expanded secret-history scans
  remain intentionally open as T122-T123 because those executable tools run in the separately
  governed publication CI; local contract validation is not misreported as their execution.

**Cycle result**: `LOCAL_IMPLEMENTATION_GATES_PASS_T122_T123_AWAIT_PUBLICATION_CI`

## Cycle 13 - Publication startup admission

Finding:

- The first authorized push failed closed because the pre-push hook requires the local Compose
  stack, while the documented startup command rejected a valid `.env.local` override by checking
  the default `.env` before parsing command-line arguments.

Correction:

- Added and closed T202. Startup now parses fixed command-line options first and validates only the
  selected environment file. It no longer creates `.env.build` as a side effect of a missing
  unrelated default file. The service-health contract locks this ordering before the local stack
  is admitted for a publication retry.

**Cycle result**: `IMPLEMENTATION_FINDING_T202_CLOSED_PENDING_LOCAL_STACK_REPLAY`

Follow-up finding:

- The selected historical `.env.local` lacked both workspace role bindings. Review of the setup
  generator found that its password-default allowlist referenced the two workspace secrets, but
  its authoritative generated-secret list omitted them, so untouched placeholders could survive
  setup.

Correction:

- Added and closed T203. Both workspace database passwords are generated as independent random
  secrets by default or deliberately inherit the operator's password default when that option is
  selected. The setup-input regression requires both resolved outputs.

**Cycle result**: `IMPLEMENTATION_FINDING_T203_CLOSED_PENDING_LOCAL_ENV_REFRESH`

Follow-up finding and correction:

- After the owner-only local environment received distinct generated role secrets, startup reached
  configuration synchronization but failed because the repository intentionally tracks
  `sync-env.sh` without an executable bit. Added and closed T204 by invoking that fixed internal
  script through Bash and locking the call in the service-health contract.

**Cycle result**: `IMPLEMENTATION_FINDING_T204_CLOSED_PENDING_STACK_START`

## Cycle 14 - Guarded publication integration

Findings:

1. The first complete local pre-push run executed API tests inside the production-shaped API
   container, where repository-crossing migration, documentation, Compose, and coverage contracts
   were correctly absent. Eight tests therefore failed on unavailable repository members, while
   adding the full source tree to the long-running service would unnecessarily widen its runtime
   read surface.
2. Physical PostgreSQL execution rejected a record lock combined with an outer join across the
   nullable definition relation. Four workflow/deletion tests failed before mutation.
3. The settings capability test inherited the enabled accounts module from the selected local site
   profile and therefore did not deterministically exercise its intended disabled case.

Corrections:

- Added and closed T205. The local API gate uses an ephemeral no-dependency test container and
  mounts only five fixed contract sources read-only. The running API container remains unchanged,
  and non-local Compose gates retain their prior execution path.
- Added and closed T206. Record mutation locks only the `ContentRecord` row; the immutable
  definition is resolved separately inside the same transaction, avoiding PostgreSQL's forbidden
  nullable-side outer-join lock.
- Added and closed T207. The capability regression now explicitly fixes the account-module state
  for both disabled and enabled assertions instead of depending on ambient profile configuration.

**Cycle result**: `IMPLEMENTATION_FINDINGS_T205_T207_CLOSED_PENDING_GUARDED_PUSH_REPLAY`

Follow-up finding and correction:

- The first ephemeral replay proved all fixed mounts were readable, but Pytest also discovered the
  mounted Django suite because the legacy API command relied on implicit root discovery. Added and
  closed T208 by naming `api/tests` on both API execution paths. This preserves cross-service
  contract reads while maintaining the documented service-local test partition.

**Cycle result**: `IMPLEMENTATION_FINDING_T208_CLOSED_PENDING_GUARDED_PUSH_REPLAY`

Follow-up finding and correction:

- After both backend partitions passed, the supported Node 24.20.0 process terminated with native
  SIGSEGV while 29 GiB remained available; no Vitest assertion failed and the kernel recorded the
  crash. Added and closed T209. The frontend runner now captures its result, visibly retries the
  exact command once only for exit 139, and still fails for a second crash or any ordinary nonzero
  test result. This does not downgrade Node, lower coverage, skip tests, or turn an assertion into
  success.

**Cycle result**: `IMPLEMENTATION_FINDING_T209_CLOSED_PENDING_REPEATED_GATE_PROOF`

## Cycle 15 - Publication CI static analysis

Finding:

- The first GitHub API job failed closed at Ruff F823 before tests. Its report exposed that the
  workspace API pool's construction block had been displaced below the worker initializer's
  terminal return. Injected-pool and physical acceptance paths were green, but no unit regression
  constructed both least-privilege pools from an empty process state.

Correction:

- Added and closed T210. The API workspace initializer again performs its own locked, double-checked
  construction using only the API workspace DSN and identity. A parameterized regression now
  constructs both API and worker pools from `None` and verifies distinct DSN builders and
  application-name boundaries. Publication remains blocked pending a green exact-head CI replay.

**Cycle result**: `IMPLEMENTATION_FINDING_T210_CLOSED_PENDING_EXACT_HEAD_CI_REPLAY`

Follow-up finding and correction:

- With Ruff green, the same API job advanced to Mypy and exposed six unchecked annotations across
  decimal validation, migration-preview accumulation, nullable derivative construction, and one
  mixed test fixture. Added and closed T211 by narrowing the already finite decimal exponent,
  explicitly typing the mixed result/fixture containers, and coupling safe-derivative use to both
  values being present. Runtime policy and accepted inputs remain unchanged.

**Cycle result**: `IMPLEMENTATION_FINDING_T211_CLOSED_PENDING_EXACT_HEAD_CI_REPLAY`

## Cycle 16 - Publication CI dependency-license metadata

Finding:

- Exact-head publication CI generated Pillow 12.3.0 metadata with the SPDX identifier
  `MIT-CMU`, while the closed allowlist knew only the generic `MIT` identifiers. The Python
  license job therefore failed closed rather than silently accepting an unfamiliar value.

Correction:

- Added and closed T212. Pillow's upstream license and package metadata both identify the exact
  license as `MIT-CMU`; the policy now admits only that exact identifier. A regression proves the
  real generated row passes while a different unlisted MIT-like value remains rejected.

**Cycle result**: `IMPLEMENTATION_FINDING_T212_CLOSED_PENDING_EXACT_HEAD_CI_REPLAY`

## Cycle 17 - Publication CI full-stack and interaction timing

Findings:

1. Both E2E and smoke publication runs failed identically because their isolated Compose graph
   reached migrations without creating or naming the two new least-privilege workspace roles.
2. Both frontend publication runs completed 194 tests but two structured-media assertions raced
   browser-side SHA-256 and upload state. The local single-worker gate passed, while slower CI
   runners consistently observed the controls before the asynchronous operation completed.

Corrections:

- Added and closed T213. The E2E graph now runs the same confined, no-port role bootstrap before
  migrations, supplies distinct runtime and worker identities, and makes the worker wait for
  schema completion. A static regression locks role ordering, credential separation, and bootstrap
  confinement.
- Added and closed T214. The affected tests now wait for observable calls and controls produced by
  hashing, upload, and status refresh. They retain the same security assertions and application
  behavior while removing machine-speed dependence.

**Cycle result**: `IMPLEMENTATION_FINDINGS_T213_T214_CLOSED_PENDING_EXACT_HEAD_CI_REPLAY`

## Cycle 18 - Guarded push Django coverage runtime

Finding:

- The guarded corrective push passed all 522 API assertions, then Django's remaining Coverage.py
  7.15.4 process hit the same interpreter-level crash previously corrected for the API service.
  The hook retained the failure and refused publication even though the independently executed
  frontend suite completed all 196 tests.

Correction:

- Added and closed T215. Django now uses the same pinned Coverage.py 7.16.0 C tracer already proven
  by the API partition, and the complete-gate regression forbids 7.15.4 in either Python service
  lock. Publication remains blocked until the complete guarded hook passes.

**Cycle result**: `IMPLEMENTATION_FINDING_T215_CLOSED_PENDING_GUARDED_PUSH_REPLAY`

## Cycle 19 - Publication runner Web Crypto boundary

Finding:

- The corrected head passed all 196 frontend tests locally and on one publication runner, while
  the duplicate runner never reached the mocked upload API in both media tests. Its DOM remained
  at the pre-admission control, identifying the runner-provided Web Crypto primitive—not React
  state timing—as the remaining host-dependent unit-test boundary.

Correction:

- Added and closed T216. The component unit test now installs a deterministic Web Crypto digest
  boundary and asserts the exact SHA-256 algorithm and `ArrayBuffer` input. Production hashing is
  unchanged, and real-browser/E2E coverage remains responsible for the native Web Crypto path.

**Cycle result**: `IMPLEMENTATION_FINDING_T216_CLOSED_PENDING_EXACT_HEAD_CI_REPLAY`

## Cycle 20 - Native Python report crash recovery

Finding:

- The guarded T216 push completed all 522 API assertions, then Coverage.py 7.16.0 faulted while
  constructing its report. Django and all 196 frontend tests passed, and the hook correctly
  refused publication. The same partition had passed immediately beforehand, identifying a native
  runtime fault rather than an assertion or policy failure.

Correction:

- Added and closed T217. API and Django now match the existing frontend native-crash policy: exit
  139 retries that exact partition once, while a repeated crash or any other nonzero result remains
  fatal. Static regressions lock the one-retry ceiling and the combined backend fail-closed gate.

**Cycle result**: `IMPLEMENTATION_FINDING_T217_CLOSED_PENDING_GUARDED_PUSH_REPLAY`

## Cycle 21 - Exact-head publication readiness

Evidence:

- The guarded push for exact head `fd340e539aee2c7859795995c9a8e3de8f8233a7` passed 522 API,
  69 Django, and 196 frontend tests.
- Both independent GitHub publication matrices passed API, Django, backend integration, contract,
  frontend, E2E, smoke, repository guards, dependency audits, Semgrep, Gitleaks, node and Python
  licenses, SBOM, and supply-chain policy. The optional Chromatic follow-up passed on its applicable
  run and skipped normally on the duplicate event.
- The fixed complete gate passed all 82 checks against that exact source commit with no failed
  checks. Its result is retained at
  `.artifacts/complete-gate/20260903T024654Z/result.json` with evidence digest
  `8ddc1e882b9bad8abf09f0cf6e756fa72c4ada4c34301babe4c78d9053c36aa3`.
- The implementation-analysis loop produced contiguous corrective tasks T151-T217 for every
  reproducible finding. Each correction has a regression or exact-gate result, and no finding was
  waived or converted into a silent success.

**Cycle result**: `NO_UNRESOLVED_IMPLEMENTATION_FINDINGS`

## Cycle 24 - Live one-shot service health admission

Finding:

- The first separately approved launch of merged commit
  `024e1efb9f1ab547637c8d3842c2d88e6b041687` built and started every service,
  including a successful `workspace-db-role` bootstrap container. The generic health loop treated
  its required `Exited (0)` terminal state as unhealthy, so it could never advance to DNS. The
  launch remained unexposed and its exact-owned Droplet was rolled back with zero managed DNS
  records left behind.

Correction:

- Added and closed T220. The remote gate now names only `workspace-db-role` as an admitted
  one-shot and accepts it only when Docker reports exact `exited` state and exit code zero. A
  missing, running, failed, or differently named service remains pending and ultimately fails
  closed; every ordinary service still requires running plus healthy.

**Cycle result**: `IMPLEMENTATION_FINDING_T220_CLOSED_PENDING_CORRECTIVE_PUBLICATION`

## Cycle 23 - Publication-runner detached DOM assertion

Finding:

- One duplicate frontend run passed 195 assertions but captured the `Hello` text node during a
  slow render transition; React replaced that node before `toBeVisible()` evaluated it. The other
  exact-head runner and local suite passed, and the failure reported a detached element rather than
  absent content.

Correction:

- Added and closed T219. The readiness assertion now re-queries the current DOM inside `waitFor`,
  so it still requires visible record content but cannot retain a transient detached node. No
  application behavior, timeout, or required assertion was weakened.

**Cycle result**: `IMPLEMENTATION_FINDING_T219_CLOSED_PENDING_EXACT_HEAD_CI_REPLAY`

Merge, provider admission, live canary, deployment, teardown, and final feature closeout remain
separately governed by T144-T150 and were not performed.

## Cycle 22 - Lifecycle-validator publication transition

Finding:

- Final lifecycle reconciliation correctly marked the authorized PR publication complete, but the
  planning validator still prohibited T142 forever and required the obsolete
  `IMPLEMENTATION_ACTIVE_NOT_PUBLISHED` status. It failed closed instead of accepting dishonest
  task state.

Correction:

- Added and closed T218. The validator now requires T142 and the
  `IMPLEMENTATION_PUBLISHED_NOT_MERGED` marker to transition together, and requires the
  evidence-backed implementation-closure marker before accepting that state. T144, T145, T148,
  and T149 remain unconditionally prohibited before their separate authority. Positive and
  hostile lifecycle-state regressions cover both boundaries.

**Cycle result**: `NO_UNRESOLVED_IMPLEMENTATION_FINDINGS`
