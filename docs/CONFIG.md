# Configuration (Base2)

This repo uses a single `.env` file (see `.env.example`) that feeds Docker Compose, Django, FastAPI, and deploy/test tooling.

## Core environment

- `ENV`: `development` | `staging` | `production`

## FastAPI auth (Option A)

- `JWT_SECRET`: required for signing access tokens.
- `JWT_EXPIRE`: access-token TTL in minutes.
- `REFRESH_TOKEN_TTL_DAYS`: refresh-token TTL in days.
- `TOKEN_PEPPER`: secret pepper used for hashing refresh and one-time tokens (required in `ENV=production`).
- `AUTH_REFRESH_COOKIE`: when `true`, refresh token is stored in an `HttpOnly` cookie; when `false`, it is returned in JSON.

## Cookies + CSRF

- `SESSION_COOKIE_NAME`: session cookie name.
- `CSRF_COOKIE_NAME`: CSRF cookie name.
- `COOKIE_SAMESITE`: `Lax` | `Strict` | `None`
- `COOKIE_SECURE`: `true` in TLS environments.

## OAuth

- `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI`
- `OAUTH_STATE_SECRET`: required for CSRF/state protection (required in `ENV=production`).

## Email

Django and FastAPI both support SMTP-style env vars (see `.env.example`). If SMTP is not configured, the system may fall back to local/outbox behavior depending on the service.
