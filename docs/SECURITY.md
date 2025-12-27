# Security Guide

## Authentication
- Cookie-based sessions (HttpOnly, Secure, SameSite) are the primary credential.
- CSRF protection required for state-changing requests (double-submit CSRF cookie + `X-CSRF-Token` header or equivalent per-session token).

## Admin and Operational UIs
- Admin routes (Django admin), pgAdmin, Flower, and Traefik dashboard MUST be gated: basic auth + IP allowlist.
- Do not expose internal-only services publicly.

## TLS Policy
- Staging-only ACME (`le-staging`) is enforced; production issuance is disallowed.

## Security Headers (Traefik)
- Public routes (`/` and `/api/*`) are served with baseline security headers (HSTS, nosniff, frame-ancestors protection, referrer policy).
- A Content Security Policy (CSP) and Permissions Policy are applied at the edge via Traefik middleware.
- Deploy verification records observed headers in `meta/security-headers.json`.

## Rate Limiting
- **Edge (Traefik)**: coarse rate limiting on sensitive endpoints (especially auth) to reduce burst abuse.
- **App-level (FastAPI)**: Redis-backed counters (fixed-window) keyed by IP and/or identifier; returns HTTP `429` with a consistent `{detail}` JSON shape and `Retry-After`.

Current FastAPI defaults:
- `POST /api/auth/login`: 5 / minute / IP
- `POST /api/auth/register`: 5 / minute / IP
- `POST /api/auth/oauth/google`: 5 / minute / IP
- `POST /api/auth/forgot-password`: 10 / 15 minutes / IP + 5 / 15 minutes / email-hash

Override knobs (optional): `RATE_LIMIT_<SCOPE>_WINDOW_MS`, `RATE_LIMIT_<SCOPE>_MAX_REQUESTS` (e.g. `RATE_LIMIT_AUTH_LOGIN_MAX_REQUESTS`).

## Error Handling
- **Enumeration resistance**: authentication and signup errors must be generic and must not reveal whether an email exists.
- **Forgot password**: the forgot-password endpoint MUST always return HTTP 200 with a generic message, regardless of whether the email exists.
- **Reset password**: reset failures MUST not reveal whether the token corresponds to a real account (use a generic "Invalid or expired token" style response).
- **Safe failures**: OAuth errors should not include provider tokens, codes, or internal stack traces.

## Logging & Auditing
- Record audit events (login success/failure, signup, logout, profile update, OAuth link, email verification, password reset) with request metadata.
- Never log secrets (passwords, raw verification/reset tokens, OAuth tokens, OAuth codes).
