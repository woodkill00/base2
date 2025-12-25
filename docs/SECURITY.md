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
- **Edge (Traefik)**: coarse rate limiting on sensitive endpoints (especially auth) to reduce burst abuse.
- **App-level (FastAPI)**: Redis-backed counters (e.g., keyed by IP + endpoint) for signup/login and other high-risk routes; returns HTTP `429` with a consistent `{detail}` JSON shape.

## Error Handling
- **Enumeration resistance**: authentication and signup errors must be generic and must not reveal whether an email exists.
- **Safe failures**: OAuth errors should not include provider tokens, codes, or internal stack traces.

## Logging & Auditing
- Record audit events (login success/failure, signup, logout, profile update, OAuth link) with request metadata.
- Never log secrets (passwords, verification tokens, OAuth tokens).
