# Security Guide

## Authentication
- Cookie-based sessions (HttpOnly, Secure, SameSite) are the primary credential.
- CSRF protection required for state-changing requests (double-submit CSRF cookie + `X-CSRF-Token` header or equivalent per-session token).

## Admin and Operational UIs
- Admin routes (Django admin), pgAdmin, Flower, and Traefik dashboard MUST be gated: basic auth + IP allowlist.
- Do not expose internal-only services publicly.

## TLS Policy
- Staging-only ACME (`le-staging`) is enforced; production issuance is disallowed.

## Rate Limiting
- Edge (Traefik) coarse rate limiting on auth endpoints.
- App-level rate limiting (FastAPI) backed by Redis counters.

## Error Handling
- Enumeration resistance: authentication errors should be generic; avoid revealing account existence.

## Logging & Auditing
- Record audit events (login success/failure, signup, logout, profile update, OAuth link) with request metadata.
- Never log secrets (passwords, verification tokens, OAuth tokens).
