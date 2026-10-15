# Analysis and issue ledger

## Cycle 1 — discovery

- F114-01: repeated full frontend CI for narrative-only closeout. Reproduction:
  PR #79 changed only feature documentation but ran the full browser matrix.
  Fix boundary: allowlisted narrative Markdown only, not all specs files (JSON
  coverage inventory and executable validators are test inputs). T005-T011.
- F114-02: earlier Django ModelBase TypeError remains unexplained. Original
  Feature113 gate 20261015T054038Z-558679 failed; isolated diagnostic and later
  full gates passed. No evidence yet supports a product-code patch. T012-T016.
- F114-03: first live bootstrap failed before useful diagnostics were retained.
  Feature113 now persists allowlisted stage/reason metadata. Next trial showed
  two updater health timeouts then recovery with fresh definitions; this does
  not establish the original root cause. T012-T016, preserve incident history.
- F114-04: real email/OAuth tests require approved recipient, dedicated account,
  correct credential type and callback configuration. Calendar OAuth must not
  be reused as sign-in credentials. T017-T022 remain blocked pending discovery
  and owner input, not mocked into acceptance.

## Cycle 3 — first implementation and integration prerequisite review

CI classifier initially failed its new tests because implementation was absent.
After implementation, 26 classifier/workflow tests plus 19 adjacent CI policy
tests passed (45 total, 6.67 seconds). CI policy, shell parity and diff checks
also passed. Evidence: `.artifacts/feature114-ci-adjacent-final.log`.
Selection is based on immutable base policy; only exact allowlisted narrative
Markdown, regular nonexecutable added/modified files and complete comparison
qualify. JSON coverage inventory, unknown paths, deleted/renamed files and policy
changes still require full validation. Required frontend job remains present;
security scanning is unchanged. Hosted behavior and release acceptance pending.

Original Django traceback fails inside ModelBase while unpacking attrs.items()
when rendering historical RedirectRule. One bounded current reproduction with
sysmon coverage, PYTHONHASHSEED=0 and PYTHONMALLOC=malloc passed. Evidence:
`.artifacts/feature114-migration-diagnostic.log`. Classification remains
unexplained intermittent runtime failure, not fixed. No dependency change or
ordinary-error retry was introduced to hide it.

F114-06: configured Google redirect is /api/oauth/google/callback, but the inspected
route accepts POST JSON, while no matching frontend callback consumer was found.
The separate Google credential endpoint is a different flow; real-account testing
must first reconcile this mismatch. No code_verifier/code_challenge was found in
the inspected authorization-code path. Add T036/T037; provider validation is
blocked until flow selection, callback configuration and test identity are known.

F114-07: full-preview environment renderer has no explicit SMTP/OAuth secret
handoff for these tests. Add T038, with disabled-by-default behavior and exact
private references, not blanket .env or vault copying. Await owner inputs before
selecting the real integration configuration or sending external messages.

- F114-05: current visual inventory contains capture-only and representative
  coverage; optional modules were isolated UI fixtures, not live enabled packs.
  T023-T029 must distinguish backend, UI and live layers explicitly.

## Cycle 2 — task refinement

Added explicit immutable-base policy, rename/delete, incomplete-history and
classifier-tamper cases to T006/T008; conditional artifact handling and visible
required check to T010; no automatic claim of savings to T011; prerequisite
authorization and privacy protections to T017-T022. Full release/security checks
must not be removed by narrative-only optimization. No provider operation is
allowed before T017 and local/hosted readiness. Initial planning is ready for
bounded implementation; integration prerequisites remain genuine open blockers.
