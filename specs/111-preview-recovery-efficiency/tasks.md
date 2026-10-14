# Tasks

- [x] T001 Define scope, budget, source and acceptance.
- [x] T002 Perform initial analysis and add adjacent recovery tasks.
- [x] T003 Reproduce missing prepared/compute-bound leases on interruption.
- [x] T004 Persist lease before create and bind compute before wait/deploy.
- [x] T005 Reject reused lease IDs before provider mutation; preserve fixed expiry (serial callers; T010 covers concurrency).
- [x] T006 Prevent unbound leases falsely claiming destruction with owned inventory.
- [x] T007 Retain sanitized failure state and regression-test cleanup errors.
- [x] T008 Journal DNS record mutations and rollback progress before each next action; interrupted rollback remains explicitly blocked, not automatically resumed.
- [x] T009 Test ambiguous create responses and provide bounded read-only reconciliation without blind retries; ambiguous ownership requires owner direction.
- [x] T010 Serialize launch/expiry operations per lease root; test contention, unsafe lock files and process-kill recovery (cross-root admission is T019).
- [x] T011 Implement persistent schedule admission; migrate approved WSL launcher and native wrapper parity. PowerShell runtime unavailable locally (disclosed).
- [x] T012 Provider-free restart/rearm, install-failure, expiry, retry and retirement tests; actual unit syntax verification; offline limit documented.
- [x] T013 Shared fixture validator used by both approved WSL consumers; hostile-input tests pass.
- [x] T014 Shared rendered-dashboard readiness helper; two real Chromium negative/positive tests added to the complete gate.
- [x] T015 Supported preflight command validates existing evidence without generating passes; standalone and negative tests pass.
- [x] T016 Three analysis cycles plus final integration review; known scope gaps addressed, limitations explicit.
- [ ] T017 Validate changed-line coverage, affected integrations and required complete gate.
- [ ] T018 Document residual risks and operational handoff; report release status accurately.
- [x] T019 Prevent same-operator concurrent previews in distinct lease roots from mutating the same DNS zone; test admission before create. Independent operator accounts remain unsupported.
- [x] T020 Bind failure cleanup to persisted compute identity and reject malformed/drifted provider identities before deletion.
- [x] T021 Add periodic cleanup retry after busy windows, terminal timer retirement without credential reads, and launch-expiry checks; provider-free boundary tests pass.
- [x] T022 Reject missing/paginated provider list inventories as unknown rather than absent before launch/cleanup.

Owner approved the narrow direct edit to exactly three WSL helpers. They are now
migrated; no notebook sync ran. Syntax, AST/consumer checks and hashes were recorded
without executing a live helper. T017/T018 remain open until final release evidence.

Traceability: R1=T003–T007,T009,T010; R2=T011,T012; R3=T008–T010;
R4=T013,T014; R5=T015,T017; R6=T016,T018.
