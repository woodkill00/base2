# Analysis and issue ledger

Cycle 1: inspected live suite/config, Volcano reference assertions, visual bundle,
lease/recovery tests and previous release evidence. No UI edits are needed.

| Issue | Severity | Reproduction / cause                                     | Regression                                           | Status |
| ----- | -------- | -------------------------------------------------------- | ---------------------------------------------------- | ------ |
| A1    | high     | missing live inputs invoke test.skip                     | prerequisite and skipped-result tests                | open   |
| A2    | high     | filtered run can exit zero without all required tests    | fixed inventory completeness tests                   | open   |
| A3    | medium   | live screenshots captured without reference comparison   | existing approved snapshot assertions on live assets | open   |
| A4    | high     | reusable owner login absent; signup fixture is not owner | distinct owner login/logout case                     | open   |
| A5    | medium   | public content only rejects 5xx, hiding 401/403          | response predicate tests                             | open   |

Cycle 2: added retry rejection, duplicate detection, clean source binding, no raw
secret/error fields, explicit design-fixture scope, nonmutating owner flow and
lifecycle separation. Live run requires an approved lease and private credentials;
local tests must not substitute fabricated live success. No known planning gap
remains for this bounded batch; execution may reveal additional issues.

Cycle 3: inspected actual mobile blog capture. It shows the expected disabled-module
fallback, exposing that existing shell-only assertions did not distinguish accidental
fallbacks. Added profile-aware route-state checks locally and live plus classifier
regressions. Detail content 404 is valid for unpublished pages; exceptions are now
restricted to known detail endpoint shapes, never collection/auth/server errors.
List-only execution was correctly blocked by the reporter; the initial regression
incorrectly expected exit zero and was corrected, without changing gate behavior.
Existing evidence directories and baseline/reporter overrides are rejected before
execution. Local/CI tests do not contact a provider or load private credentials.
