# Analysis and issue ledger

T020: PR75 frontend CI run38657973339 passed67/69 Volcano cases; both home
references failed. Downloaded actual/expected/diff captures show font metrics and
line-wrap differences, not missing menus or color changes. WSL has fonts-ubuntu
0.869+git20240321-0ubuntu1; hosted setup omitted it. Pin the frontend runner to
Ubuntu24.04 and install/verify the approved font package before capture. Do not
update approved images, relax pixel thresholds or change application typography.
Regression requires font setup before reference tests. Validate hosted output;
local passing alone cannot establish runner parity. System-font rendering on
other user operating systems remains outside exact screenshot parity guarantees.

T019: gate 20261014T232103Z-102769 retained an extension-platform coverage parser
segmentation fault, recovered on its permitted retry. Same duplicate-report class
as T013, on a different consumer. Audit found seven remaining API-only focused
checks inheriting whole-API coverage; clear only inherited options, preserve their
integration/perf exclusions and django-plugin exclusion, and disable duplicate cov.
The mandatory isolated full API coverage runner and thresholds remain unchanged.
Validate all affected test files together and regression-test every command.
Native runtime root cause remains unresolved; a clean retry is not a cure.

Continuation safety review: an unexpired launch receipt can outlive early teardown.
T018 binds browser admission to the existing private, schema/digest-validated lease,
requiring live-verified state, matching source/profile/expiry and bound root DNS IP
before owner credentials are read. Negative regressions retain sanitized failures.
This is point-in-time admission, not assurance against subsequent network/provider
changes. The existing expiry/teardown mechanism remains independent.

## 2026-10-15 authorized continuation

T013 analysis: site-content-api inherited pytest.ini's full coverage reporting,
although mandatory api-tests separately covers the same files in isolated shards.
Use the established focused-contract pattern: explicit addopts/no:cov/no:django
and unchanged integration/performance exclusions. Tests remain identical; coverage
policy and dedicated API coverage stay required. Three corrected focused runs
passed. This mitigates the observed redundant-report crash path, not an assertion
that all native-runtime instability is cured. Original failed log remains retained.

T014 analysis: add fixed browser dispatch to existing Bash/PowerShell entrypoints;
only load private bounded regular owner/receipt files, reject wrong run/source/
domain/profile, expired/restricted previews, hardlinks/symlinks/nonprivate files.
Propagate test exit status and never print credentials. Tests cover dispatch,
sanitized failure, unsafe inputs and child environment handoff; measured new-module
coverage 98%. Existing WSL browser helper updated directly (no notebook sync).
Read-only provider inventory reports zero previews and zero managed records.
No known blocking implementation gap remains before the final gate; publication,
live results and teardown evidence are still pending tasks.

Final status: A1–A6 are implemented and locally regression-tested. Live execution
remains gated on authorization/inputs. A7 is a residual infrastructure issue:
`site-content-api` exited -11 in coverage/bytecode.py during final gate reporting;
the built-in bounded retry passed. Cause is not established (do not infer hardware
failure). Evidence: final gate `site-content-api.log`, attempt 1 retained. Follow-up:
isolate coverage/runtime instability under the existing resource policy; do not
weaken coverage or silently erase first failures. Gate policy accepted the run.

Cycle 4: actual runner lifecycle review found A6, Playwright output deletion could
recreate the private evidence root with unsafe permissions. A real isolated worker
regression reproduced it; transient output is now a child directory. Required
inventory still rejects the fixture-only run. No browser/provider actions occur
in that regression. The first full gate passed but does not cover this later fix;
repeat exact-source validation is required. No known blocking code gap remains.

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
