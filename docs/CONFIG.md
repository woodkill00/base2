# Configuration

This repo uses a single `.env` file (see `.env.example`) that feeds Docker Compose, Django, FastAPI, and deploy/test tooling.

## Core environment

- `ENV`: `development` | `staging` | `production`

- `DO_APP_BRANCH`: branch name used by UpdateOnly deploys to hard-reset the remote repo (e.g., `main`).
- `GIT_REMOTE`: repo URL used by orchestrator when performing update pulls.

In `ENV=staging` and `ENV=production`, services fail fast on startup if required environment variables are missing.

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
- `OAUTH_STATE_SECRET`: required for CSRF/state protection (required in `ENV=staging`/`ENV=production`).

## Email

Django and FastAPI support SMTP-style configuration (see `.env.example`). Production startup requires the `smtp` adapter and valid non-secret connection metadata. Only the dedicated `email-worker` receives owner-only SMTP credential files; production never silently marks disabled delivery as successful. The database outbox, claim token, and stable delivery key provide durable at-least-once delivery. SMTP itself cannot prove exactly-once delivery after a connection loss, so duplicate-tolerant templates and deterministic `Message-ID` values are required; a provider API with an idempotency key is required if a deployment needs provider-guaranteed deduplication.

## Feature flags

Feature flags are controlled by environment variables on the API service.

- `FEATURE_FLAGS`
  - Comma-separated list of enabled flag names.
  - Example: `FEATURE_FLAGS=NEW_SETTINGS_UI,ENABLE_BETA_PAYMENTS`
- `FLAG_<NAME>`
  - Overrides a single flag explicitly.
  - Allowed values: `true|false|1|0|yes|no|on|off` (case-insensitive).
  - Example: `FLAG_NEW_SETTINGS_UI=true`

The API exposes effective flags at `GET /api/flags`.

Frontend usage:

- `react-app/src/flags.js` provides `fetchFlags()` and `isFlagEnabled()`.
- If `window.__FLAGS__` is set (optional), the frontend will use it without making a network call.

## Deploy/Test flags policy

- Deploy flags are PowerShell parameters to `digital_ocean/scripts/powershell/deploy.ps1` (see `docs/DEPLOY.md`).
- Tests-only behavior (e.g., React Router warning suppression) is scoped to Jest setup and does not change production runtime.

## Frontend OAuth + CSP (Google)

If the React app uses `@react-oauth/google`, the browser must be allowed to load Google scripts/frames and make OAuth network calls.

Symptoms of a CSP issue:

- The app shows a blank screen or falls back to a generic "Something went wrong" error
- The browser console shows CSP violations (e.g. "Refused to load the script" / "Refused to frame")

Where to configure:

- Traefik CSP middleware in traefik/dynamic.yml (`security-csp`)

Minimum allowlist (typical):

- `script-src`: `https://accounts.google.com` and `https://apis.google.com`
- `connect-src`: `https://oauth2.googleapis.com` and `https://www.googleapis.com`
- `frame-src`: `https://accounts.google.com`
