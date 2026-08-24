# Tasks: Base2 Universal Website Foundation

**Input**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`
**Task rule**: A checked task requires its validation evidence. Tests precede implementation. `[P]` means safe to run concurrently only after dependencies.

## Phase 1 - Spec-Kit package and baseline

- [x] T001 [US2] Create Feature 093 from current `main` and record exact source/design commits in `specs/093-base2-foundation-hardening/research.md` | Depends: none | Validate: `git merge-base --is-ancestor 5320d3fac8decfb77df75c10b4633821f91cea78 HEAD`
- [x] T002 [P] [US2] Write user outcomes, requirements, edge cases, success criteria, assumptions, and activation boundaries in `spec.md` | Depends: T001 | Validate: planning validator
- [x] T003 [P] [US2] Write architecture, constitution checks, migration strategy, risks, and DoD in `plan.md` | Depends: T001 | Validate: planning validator
- [x] T004 [P] [US3] Define domain semantics in `data-model.md` | Depends: T002 | Validate: planning validator
- [x] T005 [P] [US3] Define strict site/module/lease/gate JSON contracts in `contracts/` | Depends: T002 | Validate: JSON Schema tests
- [x] T006 [US2] Produce ordered tasks, traceability, analysis cycles, and quickstart | Depends: T002-T005 | Validate: `python3 scripts/python/validate_feature_093.py`
- [x] T007 [P] [US2] Capture machine-readable baseline test, coverage, audit, workflow, and deployment findings in `specs/093-base2-foundation-hardening/evidence/baseline/` | Depends: T006 | Validate: JSON parses and `SHA256SUMS` binds both redacted artifacts
- [x] T008 [P] [US7] Inventory the complete visual branch delta by token/component/route/hunk in `visual-port-map.md` without wholesale merging it | Depends: T006 | Validate: exact merge base, 231-commit/17-file delta, exclusions, and port decisions recorded
- [x] T009 [P] [US4] Inventory every visible route/control/data source and classify implemented/disabled/remove in `experience-inventory.md` | Depends: T006 | Validate: current router/source/manual ledger records every current route and known visible no-op; T060/T069 bind automated reconciliation

## Phase 2 - Honest complete gate (P0 blocker)

- [x] T010 [P] [US2] Write tests for Feature 093 planning validator covering placeholders, duplicate/missing IDs, bad dependencies, cycles, unmapped FRs, formatter-stable traceability, unchecked-evidence mismatch, and unsafe activation in `scripts/tests/test_validate_feature_093.py` | Depends: T006 | Validate: tests failed before T011 and now pass 8/8
- [x] T011 [US2] Implement `scripts/python/validate_feature_093.py` and same-shell wrappers `scripts/bash/validate-feature-093.sh`, `scripts/powershell/validate-feature-093.ps1` | Depends: T010 | Validate: T010 passes 7/7 and live package reports zero findings
- [x] T012 [P] [US2] Define versioned complete-gate manifest and policy in `scripts/config/complete-gate-v1.json` and `shared/schemas/gate-result-v1.schema.json` | Depends: T005 | Validate: strict manifest/result JSON contracts parse and enumerate explicit required checks/statuses
- [x] T013 [P] [US2] Write gate-runner tests for pass/fail/unavailable/not-run, dependency blocking, timeout, malformed graph, redaction, digest, atomic evidence, and portable isolated interpreters in `scripts/tests/test_complete_gate.py` | Depends: T012 | Validate: failed before T014 and now passes 7/7
- [x] T014 [US2] Implement complete gate runner and shell-parity wrappers in `scripts/python/run_complete_gate.py`, `scripts/bash/complete-gate.sh`, `scripts/powershell/complete-gate.ps1` | Depends: T013 | Validate: T013 passes 7/7; required unavailable checks produce overall incomplete
- [x] T015 [P] [US2] Generate self-contained root env fixtures and remove Linux `pwsh` assumptions from `scripts/tests/` | Depends: T007 | Validate: 28/28 applicable WSL env tests pass; 2 PowerShell-only tests explicitly platform-skipped
- [x] T129 [US2] Repair clean-WSL toolchain bootstrap by preserving executable Bash entrypoints/helpers and verifying exact Node/npm/Python versions through `scripts/bash/first-start.sh --skip-setup` | Depends: T007 | Validate: fallback/mode regressions pass 2/2 and first-start completes with Linux Node 24.13.1/npm 11.10.0/Python 3.12.3
- [x] T130 [US2] Isolate API, Django, and orchestration Python environments and resolve their interpreters portably in the complete gate | Depends: T013,T015 | Validate: clean first-start passes; API 35/35, Django 15/15, and orchestrator gate pass in distinct environments; portable manifest/PowerShell regression passes
- [x] T016 [P] [US2] Define whole-surface/change coverage floors and exception format in `scripts/config/coverage-policy.json` | Depends: T007 | Validate: six honestly labeled measured surfaces, strict schema, and 4/4 baseline/inflation/expiry/summarization regressions pass
- [x] T017 [US2] Wire frontend/API/Django/root/digital_ocean coverage into the gate with non-misleading labels | Depends: T014,T016 | Validate: 6/6 labeled surfaces and 34/34 changed executable lines pass; missing/regressed report fixtures fail in 8/8 coverage-policy tests
- [x] T018 [P] [US2] Write CI policy tests that detect `continue-on-error`, `|| true`, nonblocking scanners, mutable action tags, and missing required check mapping in `.github/workflows` | Depends: T007 | Validate: 5/5 fixtures pass and current repository scan reports all 41 pre-T019 findings
- [x] T019 [US2] Make required workflows blocking, pin actions/images, upload machine-readable results, and add controlled dependency update policy | Depends: T018 | Validate: 6/6 policy tests, zero workflow findings, YAML parse, immutable action/image refs, blocking scanners, gate integration, and existing Dependabot policy pass
- [x] T020 [P] [US2] Define dependency severity/SLA/exception policy with owner/mitigation/expiry in `docs/SECURITY_POLICY.md` | Depends: T007 | Validate: 5/5 SLA/high-severity/owner/expiry/duration fixtures and required gate policy pass with zero active exceptions
- [x] T021 [US2] Upgrade/replace vulnerable frontend dependencies and decide/migrate from legacy CRA using compatibility evidence | Depends: T020 | Validate: Vite production and Storybook builds pass; 46/46 suites and 86/86 tests pass; all six coverage surfaces and 34/34 changed executable lines pass; npm audit has zero high/critical findings
- [x] T022 [P] [US2] Add secret, SAST, dependency, SBOM, provenance, image, DAST, and IaC result adapters to complete gate | Depends: T014,T019 | Validate: 12/12 normalization/policy/integrity/failure-injection fixtures pass; required CI families retain raw plus normalized results; live npm audit adaptation is integrity-bound and high/critical clean
- [x] T023 [P] [US2] Write required/optional startup failure tests for API routes, E2E-only support-route production exclusion, flags, migrations, DB/Redis/Celery, and optional providers in `api/tests/` | Depends: T007 | Validate: 18 startup-contract cases plus focused OpenAPI/smoke/logging coverage pass; pre-implementation collection exposed the WSL signal-11 host fault and the contract then failed on absent startup primitives
- [x] T024 [US2] Replace broad startup exception suppression with typed fail-fast/explicit-degraded behavior, enforce test-support route exclusion, and expose redacted health detail | Depends: T023 | Validate: all 64 applicable API tests pass with 8 declared environment-dependent skips; focused 21/21 startup/profile/redaction/contract checks and Ruff pass
- [ ] T025 [US2] Run the local complete gate twice, reconcile flakes/skips, and store exact evidence under ignored private artifacts | Depends: T015,T017,T019,T021,T022,T024,T115,T116 | Validate: two consecutive complete results with no unexplained status
- [ ] T115 [P] [US2] Create a STRIDE/privacy/abuse threat model and misuse-case tests for public, tenant, admin, module, factory, and provider trust boundaries in `docs/THREAT_MODEL.md` | Depends: T007 | Validate: every boundary has prevention, detection, response, owner, and test task
- [ ] T116 [P] [US2] Add license, source provenance, generated-artifact, and forbidden-package policy to supply-chain gates | Depends: T020,T022 | Validate: forbidden/unknown license and unsigned fixture fail

## Phase 3 - Reliable, cost-bounded deployment (P0 blocker)

- [ ] T026 [P] [US1] Write image-build regression for React Nginx config under supported legacy/current builders | Depends: T007 | Validate: fail before T027
- [ ] T027 [US1] Replace Dockerfile heredoc config with checked-in `react-app/nginx/default.conf` copied into the image | Depends: T026 | Validate: both image-build fixtures and route fallback pass
- [ ] T028 [P] [US1] Write per-service health tests that inspect installed binaries and meaningful readiness | Depends: T007 | Validate: current curl/wget mismatch fails
- [ ] T029 [US1] Correct Compose/Dockerfile health probes and dependency conditions | Depends: T028 | Validate: all images healthy in production-like Compose
- [ ] T030 [P] [US1] Write TLS bootstrap tests for absent/file/dir/wrong-owner/wrong-mode/idempotent cases | Depends: T007 | Validate: fail before T031
- [ ] T031 [US1] Implement ACME storage bootstrap in sole orchestration path plus Bash/PowerShell wrappers | Depends: T030 | Validate: Traefik starts unprivileged with mode 0600
- [ ] T032 [P] [US1] Write strict env parser tests for quotes, whitespace, CRLF, comments, duplicate/unknown keys, malformed region/name/image, and secret redaction | Depends: T007 | Validate: fail before T033
- [ ] T033 [US1] Implement one strict env/config normalization library and route deploy/preflight through it | Depends: T032 | Validate: parser and existing env tests pass
- [ ] T034 [P] [US1] Write PreviewLease state/replay/integrity/atomic-write/interruption tests using `preview-lease.schema.json` | Depends: T005 | Validate: fail before T035
- [ ] T035 [US1] Implement lease store, ownership tags, TTL/renewal, and reconciliation in `digital_ocean/scripts/python/preview_lease.py` | Depends: T034 | Validate: state/property tests pass
- [ ] T036 [P] [US1] Write compare-before-delete tests for wrong ID/tag/digest, replacement resources, missing receipts, rate limits, and idempotent deletion | Depends: T035 | Validate: fail before T037
- [ ] T037 [US1] Integrate exact-owned cleanup and zero-resource verification into `orchestrate_teardown.py` | Depends: T036 | Validate: provider-fake teardown matrix passes
- [ ] T038 [P] [US1] Write transactional DNS tests for staged apply, health gate, exact prior values, rollback, SAN set, stale records, and interruption | Depends: T035 | Validate: fail before T039
- [ ] T039 [US1] Implement DNS transaction/reconciliation through orchestrator | Depends: T038 | Validate: provider-fake DNS matrix passes
- [ ] T040 [P] [US1] Define deployment evidence/redaction/cost schemas and failure-stage tests | Depends: T012,T035 | Validate: schema and secret fixtures pass
- [ ] T041 [US1] Integrate atomic deployment/teardown evidence and cost receipts into orchestrators | Depends: T040 | Validate: every stage emits terminal result
- [ ] T042 [US1] Add complete first-deploy, update, rollback, resume-after-interruption, and idempotent replay paths | Depends: T027,T029,T031,T033,T035,T037,T039,T041 | Validate: provider-fake lifecycle matrix
- [ ] T043 [P] [US1] Add TTL/idle sweeper with lock, bounded retry/backoff, notification, and no-active-lease no-op | Depends: T035,T037 | Validate: time/race/property tests
- [ ] T044 [US1] Add production-like providerless canary to required CI and document explicit live-canary authority | Depends: T042,T043 | Validate: CI canary creates no provider resources
- [ ] T045 [US1] Under separate live approval, run three deploy/verify/destroy canaries and reconcile provider/DNS/cost to zero | Depends: T025,T044,T118 | Validate: three integrity-bound zero-resource receipts
- [ ] T117 [P] [US1] Define provider quota, rate-limit, budget ceiling, resource-pressure, disk-full, OOM, and retry-storm tests with safe admission/degradation behavior | Depends: T035,T041 | Validate: injected exhaustion never creates excess resources or silent success
- [ ] T118 [US1] Implement bounded provider/resource admission, circuit breaking, and durable owner notifications | Depends: T117 | Validate: exhaustion/recovery matrix and deduplicated notification receipts
- [ ] T127 [P] [US1] Define state classification and teardown tests for ephemeral, retained, snapshot-before-destroy, restore-required, corrupt-snapshot, missing-key, retention-expiry, and interrupted snapshot cases | Depends: T035,T040 | Validate: destructive transition is denied without required verified preservation evidence

## Phase 4 - Site manifest and current-main visual system (P1)

- [ ] T046 [P] [US3] Write site-manifest schema/semantic tests for unknown keys, duplicate/canonical domains, locale, navigation, module compatibility, unsafe URLs, and secret values | Depends: T005 | Validate: invalid matrix rejected
- [ ] T047 [US3] Implement shared manifest loader/semantic validator and generate Python/TypeScript consumers | Depends: T046 | Validate: cross-language golden fixtures agree
- [ ] T048 [P] [US3] Add two fixture site profiles with distinct brands/modules/domains and no secrets in `site_profiles/` | Depends: T047 | Validate: both pass and digest differently
- [ ] T049 [US3] Thread manifest into Django/FastAPI/React/config generation with compatibility defaults | Depends: T048 | Validate: two brands build from same commit
- [ ] T050 [P] [US7] Formalize token/theme/component/state contracts and Storybook stories from `visual-port-map.md` | Depends: T008,T049 | Validate: token/component contract tests
- [ ] T051 [US7] Port volcanic/obsidian visual behavior onto current-main components without merging stale history | Depends: T050 | Validate: ancestry guard and reviewed component diffs
- [ ] T052 [P] [US7] Build hermetic visual harness freezing fonts/assets/time/locale/network/motion/theme/viewport | Depends: T050 | Validate: repeated screenshots byte/diff stable
- [ ] T053 [US7] Add reviewed component/page/state visual baselines and controlled update workflow | Depends: T051,T052 | Validate: intentional mutation fails
- [ ] T054 [P] [US4] Add automated WCAG/keyboard/focus/contrast/reduced-motion/responsive matrix | Depends: T051 | Validate: injected accessibility defect fails
- [ ] T055 [US3] Remove hardcoded Base2/Woodkill/SpecKit branding, navigation, social/legal links, metadata, and sample identity | Depends: T049,T051 | Validate: repository/UI brand inventory matches manifest
- [ ] T119 [P] [US4] Write and enforce CSP, HSTS, framing, content-type, referrer, permissions-policy, CORS, cache, WAF/CDN/bot, and preview-indexing policy tests | Depends: T049,T115 | Validate: header/edge-policy attack matrix

## Phase 5 - Core public website (P1)

- [ ] T056 [P] [US4] Define canonical content/media/form/search models and write Django model/migration tests | Depends: T049 | Validate: tests fail before T057
- [ ] T057 [US4] Implement Django models, constraints, revisions, lifecycle, admin adapters, and migrations | Depends: T056 | Validate: Django model/migration tests pass
- [ ] T058 [P] [US4] Define FastAPI mirror/OpenAPI/authorization contracts for content/media/forms/search | Depends: T057 | Validate: contract tests fail before T059
- [ ] T059 [US4] Implement FastAPI services/routes, tenant policy, pagination, error mapping, and outbox semantics | Depends: T058 | Validate: contract/integration/security tests pass
- [ ] T060 [P] [US4] Write React tests for core page inventory, loading/empty/error/permission/offline states, and every visible control | Depends: T009,T058 | Validate: fail before T061
- [ ] T061 [US4] Implement manifest-driven home/about/contact/privacy/terms/accessibility/search and branded 404/500 | Depends: T059,T060 | Validate: route/control E2E passes
- [ ] T062 [US4] Replace hero/docs/contact/social/dashboard/sample/no-op interactions with real behavior, explicit disabled state, or removal | Depends: T009,T061 | Validate: zero unexplained inventory entries
- [ ] T063 [P] [US4] Write abuse/security tests for CSRF, spam, replay, limits, hostile markup/uploads, MIME spoof, metadata, and retention | Depends: T059 | Validate: attack fixtures fail before T064
- [ ] T064 [US4] Implement hardened form/outbox and media validation/variants/quarantine/attribution flows | Depends: T063 | Validate: security/integration tests pass
- [ ] T065 [P] [US4] Write search authorization/freshness/tombstone and SEO/redirect/robots/sitemap tests | Depends: T059 | Validate: fail before T066
- [ ] T066 [US4] Implement tenant-safe search and manifest/content-driven canonical/robots/sitemap/OG/structured-data/redirect behavior | Depends: T065 | Validate: fixture-site search/SEO matrix
- [ ] T067 [P] [US4] Write consent/analytics/localization tests including tracker-before-consent and locale fallback | Depends: T049 | Validate: fail before T068
- [ ] T068 [US4] Implement disabled-by-default analytics/consent adapters and localization routing/content | Depends: T067 | Validate: network/locale E2E passes
- [ ] T120 [P] [US4] Add supported browser/device/input/network matrix and deterministic compatibility tests with documented minimum versions | Depends: T052,T061 | Validate: Chromium/Firefox/WebKit desktop/mobile matrix
- [ ] T121 [P] [US4] Add local-fake and disabled-default transactional email adapter tests for verification, reset, contact, invite, bounce, suppression, retry, and privacy | Depends: T059,T115 | Validate: no live email; delivery/dead-letter matrix
- [ ] T122 [US4] Implement transactional email adapter/outbox templates, suppression handling, status, and safe operator diagnostics | Depends: T121 | Validate: mail integration/accessibility/security tests
- [ ] T069 [US4] Complete public experience checkpoint including control ledger, accessibility manual checks, visual/browser matrix, performance budgets, and docs | Depends: T053,T054,T055,T061-T068,T119,T120,T122 | Validate: US3/US4/US7 acceptance bundle

## Phase 6 - Accounts, organizations, administration (P1/P2)

- [ ] T070 [P] [US5] Write Django tests/models/migrations for organizations, memberships, invitations, roles, authenticators, sessions, credentials, and audit events | Depends: T057 | Validate: fail before T071
- [ ] T071 [US5] Implement canonical Django domain, constraints, admin adapters, and migrations | Depends: T070 | Validate: Django tests/migration rollback pass
- [ ] T072 [P] [US5] Write FastAPI contract/security tests for account lifecycle, OAuth provider enable/disable/start/callback, TOTP/recovery, WebAuthn, invitations, RBAC, sessions, API credentials, audit, and data rights | Depends: T071 | Validate: fail before T073
- [ ] T073 [US5] Implement one supported account/OAuth contract, remove dead duplicate 501 routes, and implement services/routes/policies with reauthentication, secure secret handling, and append-only audit | Depends: T072 | Validate: API auth/OAuth/security tests pass
- [ ] T074 [P] [US5] Build hostile tenant-isolation matrix across models, API, caches, jobs, search, media, admin, and timing-safe not-found behavior | Depends: T071,T073 | Validate: fail before T075
- [ ] T075 [US5] Enforce tenant context/keys/policies and database constraints across all boundaries | Depends: T074 | Validate: isolation matrix passes
- [ ] T123 [P] [US5] Evaluate and test PostgreSQL row-level security/defense-in-depth, connection-pool tenant reset, transaction boundaries, and migration bypass behavior | Depends: T071,T074 | Validate: direct-query/pool-reuse hostile matrix and recorded decision
- [ ] T076 [P] [US5] Write React account/admin tests for MFA enrollment/recovery, passkeys, invites, roles, sessions, tokens, audit, content, errors, and accessibility | Depends: T073 | Validate: fail before T077
- [ ] T077 [US5] Implement manifest-aware account/admin UI with private routes and least privilege | Depends: T075,T076 | Validate: E2E/account/admin visual matrix
- [ ] T078 [P] [US5] Write export/correction/retention/deletion workflow and restore-integrity tests | Depends: T073 | Validate: fail before T079
- [ ] T079 [US5] Implement asynchronous data-rights workflows, receipts, retention jobs, and admin status | Depends: T078 | Validate: lifecycle integration tests
- [ ] T080 [US5] Complete identity/admin checkpoint with two-tenant hostile trial, session/token revocation, database defense, audit verification, and docs | Depends: T077,T079,T123 | Validate: US5 acceptance bundle

## Phase 7 - Module SDK and representative packs (P2)

- [ ] T081 [P] [US10] Write module schema/semantic/compatibility/dependency/route/permission/capability/lifecycle tests | Depends: T005,T075 | Validate: invalid fixture matrix fails
- [ ] T082 [US10] Implement module registry/validator/health/install plan with no dynamic code execution | Depends: T081 | Validate: module contract tests pass
- [ ] T083 [P] [US10] Write install/enable/disable/upgrade/export/removal/replay/rollback tests including persistent data and scheduled jobs | Depends: T082 | Validate: fail before T084
- [ ] T084 [US10] Implement deterministic module lifecycle, migration preview, receipts, and admin integration | Depends: T083 | Validate: lifecycle tests pass
- [ ] T085 [P] [US10] Create fixture module solely through public SDK and create hostile module fixtures | Depends: T084 | Validate: fixture installs; hostile fixtures fail closed
- [ ] T086 [US6] Implement portfolio/blog/docs packs in Django → FastAPI → React order with independent tests/docs | Depends: T084 | Validate: three pack acceptance suites
- [ ] T087 [US6] Implement forms/gallery/media packs in required build order with independent tests/docs | Depends: T084,T064 | Validate: three pack acceptance suites
- [ ] T088 [US6] Implement events/booking packs in required build order with timezone/capacity/race tests | Depends: T084 | Validate: two pack acceptance suites
- [ ] T089 [US6] Implement community/support packs with moderation, notification, privacy, and abuse boundaries | Depends: T084 | Validate: two pack acceptance suites
- [ ] T090 [US6] Implement membership/subscription, commerce/catalog, and marketplace/listing packs disabled-by-default with local fake providers | Depends: T084 | Validate: three pack suites; zero live provider calls
- [ ] T091 [P] [US6] Add payment/provider webhook signature, idempotency, replay, sandbox, credential, refund/cancel, and activation-boundary tests | Depends: T090 | Validate: hostile provider fixtures pass/fail correctly
- [ ] T092 [US6] Complete module checkpoint: all packs install/enable/disable/upgrade/export, route inventory, isolation, a11y, visual, performance, docs | Depends: T085-T091 | Validate: US6/US10 acceptance bundle

## Phase 8 - Production operations and recovery (P2)

- [ ] T093 [P] [US8] Define telemetry/redaction/SLO/alert contracts and fault-injection tests for logs, metrics, traces, health, queues, and external adapters | Depends: T025,T080,T092 | Validate: fail before T094
- [ ] T094 [US8] Implement structured telemetry, correlation, dashboards, alerts, and safe diagnostic bundle | Depends: T093 | Validate: injected incidents alert once and recover
- [ ] T095 [P] [US8] Write backup/restore/migration/rollback/DR/certificate tests for corruption, wrong target, stale schema, partial data, and secret exposure | Depends: T041,T092 | Validate: fail before T096
- [ ] T096 [US8] Implement encrypted backup, isolated restore validation, migration preflight, rollback, DR, and certificate-renewal drills | Depends: T095 | Validate: bounded drills pass with RPO/RTO
- [ ] T128 [US8] Integrate declared preview-state snapshot/restore/expiry receipts with lease teardown/recreation without exposing secrets or live production targets | Depends: T043,T096,T127 | Validate: stateful preview destroy/recreate drill preserves exact approved state
- [ ] T097 [P] [US8] Add image signing/provenance verification, immutable deploy identity, health-gated traffic, and rollback tests | Depends: T019,T022,T042 | Validate: tampered/unverified image rejected
- [ ] T098 [US8] Implement verified immutable release/update/observation/rollback path in orchestrator | Depends: T094,T096,T097 | Validate: three fault/restore cycles
- [ ] T124 [P] [US8] Define and run capacity/load/soak/resource-pressure/backpressure/cache-stampede/queue-drain tests against documented profiles | Depends: T092,T093,T117 | Validate: SLO, recovery, data-integrity, and budget evidence
- [ ] T099 [US8] Run operations checkpoint with chaos, capacity, alert, backup/restore, rollback, cert, and post-recovery complete gate | Depends: T098,T124 | Validate: US8 acceptance bundle

## Phase 9 - Website factory and upgrade path (P3)

- [ ] T100 [P] [US9] Define factory profile/transformation/provenance/compatibility schemas and hostile path/secret/state fixtures | Depends: T047,T084,T098 | Validate: invalid profiles fail before export
- [ ] T101 [P] [US9] Write immutable archive/generation tests for exact commit, no worktree/untracked/.git/secrets/logs/cache/receipts, interruption, and deterministic replay | Depends: T100 | Validate: fail before T102
- [ ] T102 [US9] Implement generator in `scripts/python/create_base2_site.py` with Bash/PowerShell parity wrappers | Depends: T101 | Validate: deterministic fixture repos and secret scan
- [ ] T103 [US9] Generate independent repo identity, manifests, module inventory, docs, CI, secret references, and provenance | Depends: T102 | Validate: child identity/provenance contract
- [ ] T104 [P] [US9] Write compatibility/upgrade/migration-preview/rollback tests across foundation versions and module constraints | Depends: T103 | Validate: incompatible upgrade blocks
- [ ] T105 [US9] Implement upgrade advisor and controlled patch generation without push/merge/deploy authority | Depends: T104 | Validate: compatible/incompatible fixture matrix
- [ ] T106 [P] [US9] Create blog/portfolio, SaaS, and marketplace fixture profiles and expected inventories | Depends: T103 | Validate: all generate differently from same commit
- [ ] T107 [US9] Run applicable complete gate in generated repos without executing input-supplied commands | Depends: T105,T106 | Validate: three child gates green
- [ ] T108 [US9] Under separate provider approval, deploy/verify/destroy/recreate one generated child preview with exact state/lease/cost/zero-resource receipts | Depends: T045,T107,T125,T128 | Validate: US9 acceptance bundle
- [ ] T125 [P] [US9] Add generated-repository policy checks for license/notice attribution, owner/codeowners, branch protection guidance, dependency update config, vulnerability disclosure, and secret/provider exclusion | Depends: T103,T116 | Validate: child repository governance fixture matrix

## Phase 10 - Closeout and production-readiness evidence

- [ ] T109 [P] [US2] Re-run requirements/task/contract/control/state/error/authority analysis and resolve every finding | Depends: T108 | Validate: planning validator zero findings
- [ ] T110 [P] [US2] Run complete local/CI gates twice and reconcile flakes, skips, unavailable tools, coverage, audits, and artifacts | Depends: T109 | Validate: two consecutive complete gates
- [ ] T111 [P] [US4] Run final route/control/a11y/visual/performance matrix for two fixture brands and every enabled pack | Depends: T109 | Validate: complete experience ledger
- [ ] T112 [P] [US8] Run final backup/restore/rollback/incident and three canary teardown observations | Depends: T109 | Validate: RPO/RTO and zero-resource evidence
- [ ] T126 [P] [US2] Add docs/config/OpenAPI/generated-client/module-inventory/route-inventory drift checks to required gate | Depends: T047,T082,T109 | Validate: injected stale artifact fails
- [ ] T113 [US2] Publish migration, operations, security, module, factory, cost, recovery, residual-risk, and activation docs | Depends: T110-T112,T126 | Validate: docs/link/config drift checks
- [ ] T114 [US2] Mark tasks complete only from evidence, confirm no known unresolved issue/silent failure, and prepare reviewed PR | Depends: T113 | Validate: DoD and traceability 100%

## Execution order

`Phase 1 -> Phase 2 -> Phase 3 -> Phase 4 -> Phase 5 -> Phase 6 -> Phase 7 -> Phase 8 -> Phase 9 -> Phase 10`.

P0 truth/deployment blocks all public/module/factory expansion. Persistent features must remain Django → FastAPI → React. Tasks marked `[P]` may run concurrently only when their dependency sets are satisfied and their output files do not conflict.

## Activation boundaries

Local tests and provider fakes are authorized by implementation work. Live DigitalOcean mutation (T045/T108), public DNS, production credentials, production payments, destructive module removal, permanent hosting, push/PR/merge, and production deployment require separately scoped approval. No prior approval is treated as indefinite authority.
