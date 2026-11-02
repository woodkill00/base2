# Media textarea and lifecycle evidence follow-up

Separate from the frozen seven-file unit/partition correction. On head 696f7106,
independent native review found the Caption textarea retained its authored dark
surface in high contrast because the form-control system-palette rule omitted
textarea. Extend that existing forced-colors selector; ordinary themes stay intact.
Assert active forced mode and resolved system foreground/background plus all four
solid 1px borders using the existing paint/contrast helper. Existing axe checks
and comparison thresholds remain unchanged.

The high-contrast detail comparison failed before later lifecycle evidence. Make
only that snapshot comparison soft: Playwright retains its original fatal result
while subsequent hard assertions run. Preserve pending/top/completed captures;
add diagnostic restored-state capture after an explicit ready transition, version
advance, request precondition check, focus restoration, settled aria-busy and axe.
No new approved reference is generated. Later hard failures remain fatal too.

Native coverage remains six representative Chromium modal projects; the other
six modal combinations are declared skips. Static tests do not prove the textarea
render or restore interaction. Fresh native pixels and full matrix execution
are required; no baseline or accepted-manifest update is proposed here.
