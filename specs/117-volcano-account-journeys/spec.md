# Volcano account journeys

## Outcomes

- R01: Login, signup, reset, verification and MFA share the existing Volcano
  composition, spacing, status treatments and accessible controls. No redesign.
- R02: Password entry supports visibility, autofill, paste, Caps Lock guidance,
  and live creation requirements without errors on untouched fields.
- R03: Email and Google entry points cannot start overlapping sign-in work.
  Preparation, cancellation, processing, error and retry states are understandable.
- R04: Reset/verification success remains until the user chooses to continue.
  Invalid, used or expired links offer safe recovery. Base2 versus Google
  password scope is explicit.
- R05: Verification recovery has a working, enumeration-safe server path,
  server-enforced abuse limits and accessible resend feedback. Inbox guidance
  must not imply delivery merely because a provider accepted a request.
- R06: Logout distinguishes confirmed server termination from local cleanup
  after failure. Private UI clears across tabs and history navigation.
- R07: Session expiry clears stale authenticated UI and offers safe internal
  return navigation without retaining credentials or sensitive query parameters.
- R08: MFA copy is method-neutral, expiry/recovery guidance is clear, and code
  paste/autofill remains supported.
- R09: Tests cover real states, accessibility, mobile/desktop/zoom/preferences,
  visual preservation, backend rate limits, failure recovery and exact-source CI.

## Approved session security scope

The audited implementation persists access tokens (and fallback refresh tokens)
in localStorage, contrary to the constitution. Removing this requires a session
storage/bootstrap migration across the API client, AuthContext and test fixtures.
Do not add session guarantees over that unresolved design or claim it safe.
The owner approved including this migration. Existing stored credentials must be
removed, not imported or trusted. Session restoration must verify server state.
Local logout must remain effective even when server logout fails; the UI must
report that distinction. Browser storage may carry non-secret invalidation state,
never credentials, auth payloads or personal profile data.

## Boundaries

No passkeys, new providers, automatic email-based account linking, Google-password
changes, real email sends, paid previews or production certificates. No evidence
of credential compromise was established by this code audit.
