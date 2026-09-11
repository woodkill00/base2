# Acceptance boundaries

- Bootstrap is opt-in for the exact operator environment, never all generated sites.
  Conflicting email/name/tenant ownership blocks, never links accounts implicitly.
- Use canonical auth service and password hash/policy; no raw password insertion,
  superuser or RLS bypass. Keep email verification policy; no implicit verified flag.
- Resolve secrets inside process, never command arguments. Bound resolution and
  login attempts; MFA/rejected credentials pause rather than repeatedly retry.
- Test RLS with actual limited runtime role, pooled connections, multiple tenants,
  exceptions/rollback and parallel requests; context must not leak between requests.
- Signup associates safe server validation with fields and retains anti-enumeration.
- Screenshots use ready markers and settled fonts/layout. Include mobile/tablet/
  desktop/wide, zoom, keyboard focus, supported contrast and empty/error states.
- Synthetic test mail covers recovery/verification. Real outbound provider tests
  require scope approval; mock successes are labeled, not counted as live proof.
- Owner login/read/logout only; all changes, reset, lockout and deletion tests use
  isolated synthetic identities. Vendor and edge logins are distinct credentials.
- Failed tests return nonzero even if cleanup succeeds. Critical skipped checks
  block acceptance. Teardown expiry survives test failures and evidence collection.
