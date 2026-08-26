# Requirement Traceability

| Requirements                   | Implementation area                             | Verification                           |
| ------------------------------ | ----------------------------------------------- | -------------------------------------- |
| FR-001, FR-019, FR-022         | unified control CLI                             | CLI contract tests                     |
| FR-002, FR-003, FR-004, FR-013 | lease inventory                                 | inventory/integrity tests              |
| FR-005, FR-020                 | control lock and existing lease-v2 lifecycle    | concurrency/replay tests               |
| FR-006                         | native runtime admission                        | runtime path/binary tests              |
| FR-007, FR-008, FR-009         | DNS convergence                                 | stale/split/IPv6/exact-address tests   |
| FR-010, FR-011, FR-012         | expiry planner                                  | timer plan/drift/extension tests       |
| FR-014, FR-015, FR-016         | visual evidence index                           | artifact/coverage/HTML tests           |
| FR-017, FR-018                 | asset and geometry policy                       | static policy and Playwright tests     |
| FR-021                         | read-only command boundary                      | credential/provider spy tests          |
| FR-023, FR-024, FR-025         | bounded launch orchestration                    | config/source/failure-cleanup tests    |
| FR-026                         | stable expiry runtime                           | checkout-switch and timer-target tests |
| FR-027                         | cost/retention/rate-limit/notification receipts | redaction and bounded-output tests     |
| FR-028                         | DNS provenance                                  | source/time/digest/TTL tests           |
| FR-029, FR-030                 | interrupted launch and cleanup coverage         | crash/offline/recovery tests           |
| FR-031, FR-032                 | tiered deterministic visual matrix              | PR/release/readiness/size tests        |
| FR-033                         | safe accessible SVG policy                      | asset parser tests                     |
