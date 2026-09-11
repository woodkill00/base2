# Task analysis and refinement

## Live repair refinement (2026-09-11)

R10-R15 in `repair-ledger.md` now bind the observed export failure to both real
repository transaction regressions and missing deployment prerequisites. Tasks
T019/T024/T026/T027 have explicit repair substeps. Restricted PostgreSQL exercises
the actual dispatcher, export snapshot, tenant bootstrap and replay; composition
tests require bootstrap before serving and the exact read-only probe catalog.
Existing ownership/revision/lifecycle conflicts fail closed; no suspended tenant
is automatically resumed. No known blocking planning gap remains for this batch.
Final release and live verification remain execution gates, not assumed passes.

## Cycle 1 — Initial 21-task plan

Reviewed requirements against observed signup/RLS failures, route source, security
boundaries and deployment lifecycle. Findings and task additions:

| Finding                                                            | Resolution                                             |
| ------------------------------------------------------------------ | ------------------------------------------------------ |
| Single-request RLS tests miss pooled context leakage               | T019 alternating/concurrent/rollback tests             |
| Idempotency alone misses inactive/MFA/collision semantics          | T020 explicit preservation and conflict fixtures       |
| Stable login can be confused with data restoration/default account | T021 opt-in activation and recreation/restore contract |
| Screenshot inventory could pass by omission or blank animations    | T022 negative checker tests and visual review status   |
| Recovery tests could email real users or modify owner              | T023 provider isolation and owner mutation guard       |
| Cleanup could mask failure; failed alert or expiry could be lost   | T024 exit/queue/expiry fault injection                 |
| Vendor/application roles might be conflated                        | T025 separate authorization and credential checks      |

Result: added seven tasks, renumbered release/acceptance/closeout to T026–T028,
and made all repair work a prerequisite of release.

## Cycle 2 — Consistency and scope review

Checked all 16 requirements against 28 ordered tasks, predecessor dependencies,
user stories, tests, deployment and credential boundaries. Confirmed UI repairs
do not weaken password/RLS policies, owner login does not imply superuser or
restored data, and live acceptance cannot be claimed from mocked checks. Updated
traceability and added machine validation of IDs, coverage and dependency order.

No unresolved planning inconsistency identified in this review. Implementation
may discover further gaps; reopen tasks and rerun analysis rather than declaring
unknown errors impossible. This is a single-agent review, not independent audit.

## Remaining execution gates

All implementation tests and tasks are pending. Exact private owner credential
reference, verification handoff and environment configuration are activation
prerequisites. Human screenshot acceptance and authorized bounded live preview
are release prerequisites. No account, provider resource or runtime changed.

## Planning validation

- validate_plan.py passed: 16 requirements, 28 tasks, two recorded cycles;
  checks contiguous IDs, preceding dependencies and exact traceability coverage.
- git diff --check passed.
- scripts/bash/assure.sh run --tier auto passed diff-check and feature-plan.
- Complete release and application suites intentionally not run for planning-only
  changes. These checks do not establish that the live signup/settings are fixed.
