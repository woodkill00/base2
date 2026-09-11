# Frontend configuration and evidence model

No domain table, credential storage or schema migration is introduced.

- RouteLayoutPolicy: route pattern/family, profile/module availability, public or
  guarded audience, left/right slot policy, narrow-screen behavior, nested navigation,
  scroll policy, exception approval reference. Unknown entries fail validation.
- LayoutTokens: rail/content bounds, gaps, header/footer/banner offsets, breakpoints,
  safe-area behavior. Existing themes override tokens, not duplicated structure.
- VisualCase: stable ID, route, synthetic identity/role, profile, locale/direction,
  viewport, theme/contrast, data state, expected slots, interaction and readiness.
- ReviewRecord: source, case ID, before/after evidence references, defect IDs,
  automated result, independent reviewer/owner decision, approved baseline digest.
- DefectRecord: severity, reproduction, affected families, expected/actual result,
  first-failure artifact, repair task and regression case, status and retest evidence.

Evidence remains private and sanitized; no real account tokens, passwords, user-upload
contents or auth traces in baselines. One new attempt directory per retry.
