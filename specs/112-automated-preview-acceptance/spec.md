# Automated preview acceptance

Preserve the approved Volcano design. Routine acceptance must not depend on an
owner spotting regressions. Missing, skipped, filtered, flaky or failed required
checks must never produce a passing live acceptance result. Captures alone are
not visual comparisons. Intentional design changes still require owner approval.

Required outcomes: complete live browser coverage, actual reusable-owner login,
public-content HTTP failure detection, approved-reference pixel comparisons,
private source-bound machine-readable results and negative tests for the gate.
Existing lifecycle, security and recovery tests remain required; browser success
does not imply teardown success or authorize provider actions.

No design/baseline changes, paid resources, credentials, publication or deployment
are authorized by this implementation. Live acceptance remains blocked until an
approved preview and all private inputs are available.
