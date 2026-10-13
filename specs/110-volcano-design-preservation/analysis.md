# Task → analysis → refinement

## Cycle 1 — Why green tests missed the rejected design

The previous suites required generic rails and reviewed newly generated screenshots,
not preservation of the original accepted menus. V002/V003 add original-state
references before repairs. Replacing controls with similarly functional controls
is explicitly insufficient. Keep negative structural checks and image comparison.

## Cycle 2 — Preserve working changes and approval boundaries

A blanket revert of PR #68 would discard account/privacy/security work. V004 is
limited to Home composition. All other code remains intact. V006 is a real owner
checkpoint; don't repeat the prior broad rollout before visual confirmation.
V007–V010 retain permission filtering, focus/modal behavior, real content readiness,
error states, profiles, locales and coverage. No baseline updates merely for green.

## Issue ledger

| Issue                                   | Cause                                            | Regression/evidence                                 | Status  |
| --------------------------------------- | ------------------------------------------------ | --------------------------------------------------- | ------- |
| VOL-01 Original side menus replaced     | Home selected SharedLayout/HomeSharedControls    | Original-menu screenshot and DOM contract           | Open    |
| VOL-02 Gradient and composition missing | New Home branch omitted original wrapper         | Original Home screenshot/background contract        | Open    |
| VOL-03 Visual identity unguarded        | Structural tests accepted new design as baseline | Freeze pre-edit original captures; owner checkpoint | Open    |
| VOL-04 Other pages need matching design | Generic shared panels not original menus         | V007–V009 after reference confirmation              | Pending |
