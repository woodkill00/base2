# Owner-approved restricted preview

2026-09-11: owner approved a temporary preview with uploads/media processing
disabled, not acceptance of stale antivirus definitions. No production release,
certificate change, administrator bypass, or lease extension is authorized.

## Tasks and analysis

- [x] Add explicit opt-in deployment mode, defaulting to full protected operation.
- [x] Deny media/content API routes before body consumption and block media jobs.
- [x] Propagate the restriction to every API/Celery consumer; omit scanner services
      from the restricted Compose profile without weakening normal scanner checks.
- [x] Bind the mode to remote bootstrap and report restricted acceptance honestly.
- [x] Test default behavior, negative admission, request-body non-consumption,
      worker non-execution, deployment mode propagation and normal-mode preservation.
- [ ] Run affected checks and mandatory release validation before deployment.
- [ ] Deploy exact source with bounded teardown; verify owner login, non-media
      journeys and direct media rejection. Record media functionality as blocked.

Analysis: blocking only a UI button is insufficient. Both modern media and legacy
content asset routes must be blocked, including imports, grants and raw bodies.
Disable the entire content API during this preview to avoid indirect media writes.
Queued jobs must fail before repository/storage access. Missing mode defaults to
normal; malformed values fail closed. Never claim restricted acceptance proves
media acceptance. No existing definitions/freshness policy is altered.

Review cycle 2: added real application wiring verification (not only isolated
middleware tests), all six API/Celery environment consumers, receipt mismatch
rejection, and a required mobile/desktop visual gate with an explicit visible
restriction notice. Initial targeted deployment/API tests and notice unit/browser
tests pass. Full release and live acceptance are still outstanding. No feature
closeout or media acceptance is claimed.
