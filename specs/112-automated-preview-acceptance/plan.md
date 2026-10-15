# Plan

Source: main 556b9603. Environment: native WSL, Node/Playwright and Python.
Budget: one focused test batch, one integrated validation batch, one full release
gate after prerequisites; no heavy suites concurrently, no paid deployments.

Add a fixed live test inventory and reporter which rejects partial runs, retries,
skips and duplicate/missing cases. Bind reports to source revision and dirty state;
do not record credentials or raw browser errors. Fail before browser launch on
missing private inputs. Add owner sign-in without changing the persistent account.
Compare deterministic live home/menu states against existing reviewed snapshots;
API fixture comparisons are explicitly design-only, not backend acceptance.
Keep real backend checks separate. Expand public response checks to unexpected
4xx/5xx (allow explicit detail-not-found only). Add contract and browser regressions
to the standard gate, with a traceable coverage matrix and operator instructions.

Existing lease/scheduler/DNS recovery suites remain authoritative for provider-free
recovery. Actual teardown remains a separate live lifecycle receipt. No aggregate
report may claim that browser tests prove successful resource destruction.
