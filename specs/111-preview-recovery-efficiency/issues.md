# Issue ledger

| ID      | Severity/type       | Reproduction / cause                                    | Consumers / regression                                            | Status                                                          |
| ------- | ------------------- | ------------------------------------------------------- | ----------------------------------------------------------------- | --------------------------------------------------------------- |
| P111-01 | High recovery       | interrupt remote deployment; no saved lease             | launch/expiry; crash fixtures                                     | Fixed locally; release blocked on concurrency                   |
| P111-02 | High recovery       | prepared lease with owned compute marked destroyed      | expiry; unbound inventory negative test                           | Fixed locally; uncertain identity still requires reconciliation |
| P111-03 | High recovery       | interrupt DNS migration between API and journal         | DNS/cleanup; stage interruption tests                             | Open                                                            |
| P111-04 | High infrastructure | restart removes transient cleanup timer                 | workstation launcher; restart simulation                          | Open                                                            |
| P111-05 | Medium fixture      | revision mismatch / URL before rendered heading         | media/settings; identity/readiness tests                          | Open                                                            |
| P111-06 | Medium efficiency   | stale repetition evidence found late                    | assurance; preflight tests                                        | Open                                                            |
| P111-07 | High security       | launch exception deleted latest unvalidated provider ID | launch cleanup; malformed/drifted identity tests                  | Fixed locally                                                   |
| P111-08 | High concurrency    | per-write lock does not exclude launch and expiry       | operation lock; contender and killed-process tests                | Fixed per root; cross-root T019 remains                         |
| P111-09 | Medium fixture      | old expiry fake forbids needed read-only inventory      | scanner; empty-inventory fixture rejects all other provider calls | Fixed; first failure retained                                   |

Detailed evidence: `.artifacts/feature111/`. Keep first failures alongside fixes.
No live provider run is authorized or needed for initial reproduction.
