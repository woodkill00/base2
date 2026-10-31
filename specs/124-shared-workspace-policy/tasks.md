# Feature 124 task ledger

Status: implementation and local verification in progress. No PostgreSQL, native-browser
or release acceptance is claimed; unchecked tasks include those outstanding proof obligations.
Scope approved by user on 2026-10-31 after the four-capability recommendation. Preserve
unrelated dirty Feature 122 files and draft PR 89. Production work follows independent
review of this contract. Do not resume/delegate stopped Expat repair.

## A. Analysis and reproductions (before writers)

- [x] T01 Review spec/plan against constitution and source; inventory every publication,
      public-read/search/export/asset and notification consumer, identity realm and migration
      owner, human authorship provenance and supported local artifact transport. Record exact interfaces, lock order, capability dependencies and evidence paths.
- [ ] T02 Add failing notification tests: two-tab lost update, first-insert race, mandatory
      row omission, returned committed snapshot, timeout/reload, tenant/user isolation (AC1).
- [ ] T03 Add failing review/visibility journeys: direct/scheduled bypass, self approval,
      stale semantic revision (including restore/import/relationship/media mutation),
      public excerpt/body/metadata/flags and asset-version replacement, native Django writes,
      state-only approval carry-forward, permission revocation, policy race, existing content transition, stale
      public projection/export/grant, disabled module and missing policy (AC2/3/5).
- [ ] T04 Add failing consumer tests: transactional enqueue, preference suppression,
      immediate/digest, duplicate/restart, changed recipient access, stale review, local-only
      adapter boundary and failure observability (AC4/6).

## B. Canonical Django foundation (first implementation stage)

- [x] T05 Define common canonical scope/policy/set/approval/intent primitives, closed
      validation and constraints; adapt existing users/sitecontent runtime models without
      conflating Django operator identities with API public identities (AC1-6).
- [ ] T06 Implement additive migrations/backfill and runtime schema mirrors, with genuine
      PostgreSQL migration/restore and restricted request/worker RLS tests. Prove defaults,
      existing-row preservation, mixed-version safety and rollback boundary (AC5/8).
- [ ] T07 Implement canonical CAS and effective-policy/approval decisions with lock-order,
      concurrency and author/reviewer tests; approve Django contracts before API stage.

## C. FastAPI, repositories and workers (second stage)

- [ ] T08 Mirror notification-set read/write contracts, mandatory-row preservation,
      expected-version errors, atomic audit and same-transaction response; document old
      writer rejection and compatibility. Pass focused + real PostgreSQL tests (AC1/6).
- [ ] T09 Implement authorized shared-policy GET/PUT and discovery metadata; exercise all
      roles, tenant tampering, unknown fields, CSRF, disabled dependencies and first save.
- [ ] T10 Implement exact-revision independent approval and shared enforcement in content
      edits, transitions and scheduler. Existing published content remains until edited;
      scheduled unauthorized records block visibly. Prove concurrency/revocation (AC2).
- [ ] T11 Enforce visibility at every inventoried read/search/export/asset boundary;
      reauthorize jobs/downloads and stale grants. No control activated with a known leak
      or asynchronous-only privacy enforcement (AC3).
- [ ] T12 Implement transactional review intent and bounded local-only consumer, UTC daily
      digest and idempotent sink. Recheck live permissions/preferences/state; expose safe
      suppressed/failed/pending outcomes, test outage/restart/replay (AC4/6).
- [ ] T13 Independent backend security/interface review; resolve findings and freeze
      mirrored response shapes before React integration. Record issue ledger and coverage.

## D. React and complete journeys (third stage)

- [ ] T14 Extend service/parser/registry with typed versions, scoped policy controls,
      accessible deep links and existing Save/Cancel/conflict/uncertainty conventions.
- [ ] T15 Integrate review actions/status and local delivery status without claiming
      unwired channels/providers. Test dirty drafts, account changes, navigation, duplicate
      clicks, interrupted requests and keyboard focus (AC1/2/4/7).
- [ ] T16 Run real-service multi-user journeys for AC1-6; verify DB persistence after
      reload/restart and negative direct calls, not only mocks. Test representative existing
      publishing/docs/portfolio profiles; no claim of all-family maturity.
- [ ] T17 Inspect responsive/light/dark/forced-color/accessibility captures against
      approved Obsidian/Volcano references; no baseline laundering (AC7).

## E. Acceptance and delivery

- [ ] T18 Review >=90% changed-line coverage and unchanged floors, critical branch
      evidence, migrations/restore and regressions across settings/content/media consumers.
- [ ] T19 Run supported complete release gate on frozen source after focused repairs;
      list passed/failed/blocked/not-run separately. Baseline image security remains an
      independent blocker until legitimately resolved; no prohibited repair attempt.
- [ ] T20 Produce exact-source release summary and update truthful scope documentation,
      requirement/test map and backlog states. Request applicable publication authority;
      no merge/deploy or push as part of these tasks without that authority.

## Implementation checkpoint (2026-10-31)

- Contract and canonical-model source reviews completed before API/React work.
  Canonical focused tests passed (48), including fresh-install conservative defaults,
  legacy preservation and explicit identity-realm separation. Actual PostgreSQL
  migration, RLS and concurrency remain unverified.
- Notification API local full-suite checkpoint passed 1,441 tests before the later
  policy integration. This is historical local evidence, not the final combined gate.
- Notification/navigation React checkpoint passed 586 tests plus 27 tooling tests,
  lint, types and build. A modal stacking/focus defect was reproduced and repaired;
  actual native browser histories, inert behavior and visual captures remain unrun.
- Policy/review UI and backend integration are implemented and undergoing expanded
  local regression checks. New real PostgreSQL proof cases are wired for the
  disposable integration runner; collection is not execution.
- The database-only review notification consumer passed 50 focused tests. Its
  PostgreSQL delivery/digest proof cases remain unrun. No live email is activated.
- Retention/privacy compatibility, native mutation guards and media transaction
  integration are necessary supporting work for the shared policy boundary. Their
  source reviews and unit tests do not replace restricted-role database evidence.

## Supporting obligations discovered during implementation

- [ ] T21 Enforce native/queryset/raw semantic invalidation, immutable schema and
      independent review-cycle binding. Prove advisory-before-row locking in supported
      Django/API/worker paths; test revocation, contention and transaction rollback.
- [ ] T22 Preserve supported retention and claim-fenced data-rights operations for
      review records through narrow audited helpers, without granting ordinary runtime
      access to erase approval history or exposing personal preferences to organizations.
- [ ] T23 Keep media inspection outside policy critical sections, fence immutable
      results and expired claims, and use a committed exact purge plan before deleting
      local artifacts. Prove partial-failure recovery and prevention of restore/rebinding.
      Remote transport and cross-version orphan limitations must stay explicit.

Draft publication and tested follow-up commits were authorized separately on
2026-10-31. No new feature commit,
merge, deployment, provider activation or complete-gate pass is claimed here.

- [ ] T24 Preserve optional-policy draft/in_review/publication compatibility, including
      a sole owner. Required review remains fail-closed for unknown authorship or no
      independent reviewer. Verify both delivery-policy transition directions, truthful
      zero-recipient status and no automatic audience backfill.
