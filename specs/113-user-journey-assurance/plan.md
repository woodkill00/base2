# Implementation plan

Source: main 087fd4cc9d81e047f9f31e1c84bb36e6e4dbc068. Native WSL checkout.
Branch: 113-user-journey-assurance. Preserve Volcano styles and source-bound
review ancestry. No agents, paid resources or external messages in this batch.

Build a route/state evidence ledger first. Reuse existing settings, media,
workspace, operations, compatibility and live suites without treating mocked
responses as backend evidence. Add route-drift and ledger-schema regression tests.
Add browser journeys to the existing experience runner where appropriate and
targeted component/API regressions for defects discovered in those journeys.

Work in batches: public/auth; protected settings/dashboard; enabled content and
workflows; cross-browser/visual review; integration and release. Each batch gets
one diagnostic sweep and at most two correction reruns before root-cause review.
Do not run heavy suites together or edit their inputs while running. Use existing
assurance caching and entrypoints, followed by one complete gate after affected
checks and visual review. Budget does not authorize dropping required tests.

Real backend flows require supported local Compose topology and test-only mail
capture. Inspect prerequisites before attempting them. Native PowerShell and
external OAuth/delivery are explicitly separate from WSL/fixture acceptance.
Screenshots must contain synthetic content and no tokens or owner credentials.

## Separately approved live acceptance

Owner approved one Frankfurt droplet, staging certificates, maximum 60 minutes
and USD 0.25, followed by teardown. Provision only after local acceptance and CI
pass for the candidate source. Use the existing bounded deployment and cleanup
path; record resource identity, lease, live results and verified teardown. This
does not authorize a lease extension, production certificates or additional
resources. Final outcome: first trial failed and was destroyed; one additionally
approved trial passed 11/11 live checks and was destroyed with empty independent
provider inventory. See analysis cycles 9-10 for source-bound evidence and risks.

## Unchanged media reference renewal

After committing the candidate and reviewing its unchanged design, run
`bash scripts/bash/renew-media-visual-review.sh --confirm-reviewed-no-design-change`
(PowerShell counterpart: `scripts/powershell/renew-media-visual-review.ps1`).
The command refuses a dirty source or changed reference images, executes the fixed
full media comparison matrix without baseline updates, and only then renews the
source binding. Retain the private runner evidence and commit the generated review
as a descendant of the candidate. This does not approve new visual references.
