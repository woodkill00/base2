# Session migration contract

## Approved behavior

Access credentials remain in module memory. On startup, remove legacy localStorage
`user`, `token` and `refresh_token` entries without reading, trusting or transmitting
them. Unrelated preferences remain untouched. Store only an allowlisted profile
in React state; never store the full authentication response.

Restore sessions through the existing HttpOnly refresh cookie and double-submit
CSRF header. A missing cookie leaves the visitor signed out. Private routes wait
for bootstrap before mounting their consumers. Interactive sign-in is guarded
against overlapping email, Google or MFA requests. Existing refresh single-flight
is extended with a same-origin Web Lock shared with interactive auth and logout.
The lock prevents cookie rotation and logout from racing one another across tabs;
no credential travels through the lock or tab messages.

Logout immediately clears memory and React state and increments an invalidation
epoch. Late network responses must not restore the prior session or private UI.
A non-secret signed-out barrier in localStorage blocks automatic cookie restoration
after failed logout or reload. Only an explicit successful sign-in clears it.
Other-tab logout and browser history restoration clear stale private state.
The login page reports unconfirmed server logout and offers an explicit retry.

Backend logout returns 503 when refresh-token lookup/revocation fails; it preserves
the cookie for explicit retry rather than claiming successful server revocation.
Absent/already-revoked sessions remain idempotent successes. Audit-event failure
is separate from actual revocation failure. No raw failure or credential is returned.

## Compatibility and limitations

- Deployment must use `AUTH_REFRESH_COOKIE=true`, HTTPS, Secure/HttpOnly refresh
  cookies, the expected SameSite/origin configuration and existing CSRF checks.
  A deployment preflight assertion is still required before release.
- Legacy browser-storage-only sessions will require a fresh sign-in. Do not migrate
  a JavaScript-readable refresh token back into an active session.
- Without browser storage, explicit memory-only sign-in works but automatic
  restoration fails closed. Without Web Locks, automatic refresh is disabled;
  sign-in remains possible. Test supported browsers before release.
- Refresh/logout errors and unsupported-browser states need full user-visible
  recovery acceptance; do not equate unavailable restoration with server revocation.
- Refresh revocation does NOT instantly revoke an already-issued stateless access
  JWT. This change makes no global immediate-revocation guarantee.
- Cross-tab account switching, delayed cookie writes, browser Back/bfcache and
  real-browser refresh behavior still require acceptance tests.
- Offline/unit API mocks are not real-provider, real-cookie or inbox acceptance.

## Rollback and release

No database migration or new domain model is needed for the session foundation.
Do not restore the old token-storage implementation as a security rollback. If
acceptance fails, hold deployment and repair forward; an emergency deployment
rollback needs its own reviewed decision. No account deletion or credential
rotation is implied. This working branch is not yet release-ready and remains
stacked on the unmerged Feature116 parent.
