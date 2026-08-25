# Identity and Security Contract

Base2 exposes one supported FastAPI account contract under `/api/auth/*` and one
Google Authorization Code contract under `/api/oauth/google/*`. The former
credential endpoint `/api/auth/oauth/google` remains a compatibility entrypoint,
but it obeys the same explicit provider switch and completion policy. No route
returns a placeholder `501`.

Google OAuth is disabled by default. Enabling it requires
`GOOGLE_OAUTH_ENABLED=true`, an exact client ID, client secret, callback URI, and
an OAuth state secret of at least 32 characters. Start requests accept only a
same-origin absolute path. State is signed, expires within five minutes, contains
an OIDC nonce, and is bound to an HttpOnly, Secure, callback-scoped browser
cookie. Callback processing clears that cookie before validation, exchanges the
authorization code over a bounded HTTPS request, validates audience and nonce,
and never stores Google access or refresh tokens.

`/api/identity/capabilities` is the public capability source. TOTP and single-use
recovery codes are versioned v1 capabilities. WebAuthn is versioned v1 but
disabled unless explicitly configured; disabled methods must fail closed rather
than imitate enrollment.

Authorization uses the fixed owner, admin, editor, and viewer roles. Unknown
roles and permissions are denied. Credential, membership, invitation, MFA, and
other sensitive changes require recent authentication (five minutes by default).
Invitation, recovery, session, and API credential values are retained only as
peppered hashes; TOTP secrets require an encrypted envelope at persistence.
Plaintext recovery codes and API secrets may be shown once at creation only.

Audit metadata is recursively redacted before insertion. Django model methods
reject update/delete, and database triggers also reject bulk or direct mutation.
Provider tokens were removed from the canonical OAuth model. Data-rights routes
authenticate before resolving or disclosing tenant context; their durable
asynchronous lifecycle is delivered by Feature 093 tasks T078-T079.

The following do not activate a provider, WebAuthn, tenant administration, or a
production deployment. Those boundaries remain explicit and separately tested.
