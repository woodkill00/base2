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

## Closeout disposition

P111-01/02/07/08: fixed and validated; cross-root same-account admission also passed.
P111-03: durable journaling, exact identity and read-only reconciliation validated;
unknown outcomes remain owner-reconciled by design, not silently retried.
P111-04: guarded launch now arms persistent cleanup; three approved helper migrations
are complete. Offline workstation and untested live power-cut limitations remain.
P111-05: both fixture consumers now use the shared validator; rendered readiness has
two required Chromium regressions. P111-06: standalone preflight passes on exact
evidence and rejects missing/stale evidence without running the expensive suite.
P111-09: corrected fixture retains required read-only inventory verification.
No known unresolved defect in the implemented scope; all 121 release checks passed.
This is not a guarantee against unknown defects or proof of live cloud behavior.
