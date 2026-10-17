# Reliable integrations and efficient assurance

## Outcomes

Preserve the approved Volcano design while making failures diagnosable, verifying
real external integrations safely, broadening reviewed user-state evidence and
avoiding expensive CI work for proven narrative-only changes.

## Requirements

- R01 Preserve first failures and distinguish reproducible defects, startup
  transients, environmental faults and unexplained intermittency. Recovery never
  erases failure evidence or converts retries into an unqualified pass.
- R02 Bound diagnostic runs and retain sanitized stage, timing, resource and
  toolchain evidence. No raw credentials, email tokens or provider responses.
- R03 Verify real verification/reset/contact email only against explicitly chosen
  test recipients. Prove delivery and intended outcomes, expiry/replay and session
  boundaries; local SMTP capture alone must not be labelled external delivery.
- R04 Verify Google sign-in with a dedicated authorized test identity, correct
  redirect/state/nonce/PKCE behavior, denied consent, replay and safe session
  handling. Human consent/MFA remains human; missing credentials fail closed.
- R05 Expand reviewed visuals for public, auth, settings and content states,
  including narrow/wide viewports, RTL/long text, keyboard/zoom and errors.
  Preserve existing references; new references require inspection, not blanket
  baseline updates. Report representative coverage rather than exhaustive proof.
- R06 Exercise enabled optional content/event/booking capabilities with disposable
  data and real-backend checks in an isolated profile. Do not silently enable them
  on the reusable Base2 profile or mutate the owner's account.
- R07 Narrative-only CI must remain visible and blocking on its own validations.
  Changed executable inputs, fixtures, references, ambiguous paths, incomplete
  history or classifier changes must select full validation. Never label omitted
  browser tests as executed/passed. Preserve security and complete release gates.
- R08 Bind results to exact source, event comparison range, configuration and
  environment. Record measured duration/check counts; do not invent token savings.
- R09 After local and hosted acceptance, run only an explicitly bounded live
  trial through the supported entrypoint, verify public/protected behavior and
  cleanup. Staging TLS only; no unattended account consent or lease extension.

## Acceptance and scope boundaries

All five workstreams have reproducible evidence, tests and task traceability.
Known blockers remain open. Account/provider prerequisites and reviewed visual
references are separate from test passes. A successful live trial is not proof
that prior unexplained failures are fixed, nor a guarantee against unknown bugs.
No permanent deployment, billing changes, production certificate or unrelated
feature is authorized by this specification.
