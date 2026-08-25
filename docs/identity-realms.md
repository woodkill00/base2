# Identity realms

Base2 has two deliberately separate identity realms.

The public-account realm is owned by FastAPI. It authenticates visitors and
tenant members with short-lived access tokens and rotating refresh sessions.
It is the only realm accepted by `/api/auth`, `/api/identity`, and
`/api/privacy`. Tenant roles and permissions must be loaded from current
server-side membership state for every protected operation; role-like token
claims are not authorization evidence.

The operator-CMS realm is owned by Django and is restricted to the private
`/admin` surface. Its session cookie and CSRF controls are not accepted by the
public-account APIs, and FastAPI bearer tokens are not accepted by Django
administration.

There is no implicit mapping between the realms. In particular, email,
username, and display name are mutable attributes and must never be used to
join identities or inherit authority. A future linked-account feature requires
an immutable mapping table, proof of control in both realms, revocation tests,
and a reviewed migration and rollback plan.

This separation lets a site run without Django administration being public and
prevents a compromised visitor account from becoming a CMS operator. It also
means operator and tenant-member access are provisioned and revoked separately.

## Public-account controls

- Password and Google OAuth login both stop at the same TOTP/recovery challenge
  when MFA is active. No provisional access or refresh token is returned.
- Recovery codes are stored as keyed hashes, consumed atomically with the login
  challenge, and shown in plaintext only when generated.
- Authenticator secrets and data-rights payloads use the dedicated
  `IDENTITY_ENCRYPTION_KEY`; production startup fails if it is missing.
- Refresh-created access tokens are not recent-reauthentication evidence.
  Enrollment, recovery-code replacement, invitations, role changes,
  credentials, data-rights requests, and export download require a fresh login
  issued within five minutes.
- Organization membership and permission checks are loaded server-side and
  remain tenant-bound. Authorization failure uses a generic `not_found` result.
- First-owner bootstrap is disabled by default. It must be deliberately enabled
  for initial provisioning and disabled immediately after one owner exists.
- WebAuthn/passkeys remain truthfully disabled until a separate versioned
  ceremony, storage, origin/RP binding, recovery, and hostile test feature is
  implemented.

## Operator-CMS controls

Django administration remains the private operator surface and is absent from
the public URL configuration. It does not share cookies, bearer tokens, CSRF
state, membership rows, or recovery mechanisms with the public-account realm.
