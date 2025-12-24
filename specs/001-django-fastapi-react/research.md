# Research (Phase 0): Full-stack Baseline

This document resolves planning unknowns and records key technical decisions with rationale and alternatives.

## Decision 1: Cookie-based auth format

**Decision**: Use HttpOnly, Secure, SameSite cookies as the primary credential carrier; implement CSRF protection for state-changing requests using a double-submit CSRF token (CSRF cookie + `X-CSRF-Token` header) or an equivalent per-session token strategy.

**Rationale**:
- Satisfies constitution requirements (no sensitive tokens in browser storage; cookie auth; CSRF enforced).
- Works naturally with a React SPA calling internal API routes.
- Avoids introducing a separate “frontend token store” or long-lived client credentials.

**Alternatives considered**:
- **Bearer tokens in localStorage/sessionStorage**: rejected due to constitution.
- **Pure server-side sessions only** (DB/Redis-backed with opaque session ID): viable, but requires careful cross-service session handling and may be higher integration cost for FastAPI/Django split.

## Decision 2: Rate limiting approach

**Decision**: Apply layered rate limiting:
- Coarse rate limiting at Traefik (already present middleware) for burst control.
- App-level rate limiting in FastAPI using Redis counters for credential endpoints.

**Rationale**:
- Defense-in-depth for auth endpoints.
- Redis is already present and healthchecked in `local.docker.yml`.

**Alternatives considered**:
- **Edge-only rate limiting**: rejected; cannot express all app semantics and may be bypassed internally.
- **In-memory rate limiting**: rejected for multi-process / multi-container correctness.

## Decision 3: Google sign-in flow

**Decision**: Implement Authorization Code flow with strict redirect allowlist. On completion, create the same cookie-based session state as email/password login.

**Rationale**:
- Aligns with constitution OAuth guidance.
- Keeps tokens server-side.

**Alternatives considered**:
- **Implicit flow**: rejected for security reasons and modern best-practice guidance.
- **Frontend-only OAuth tokens**: rejected due to cookie-first posture and secret-handling concerns.

## Decision 4: Celery ownership (tasks + worker image)

**Decision**: Keep Celery app ownership in `api/` for this feature (Celery app already exists in `api/tasks.py`, and `local.docker.yml` wires worker/beat from the `api` image).

**Rationale**:
- Minimizes churn while adding auth/security features.
- Preserves existing deploy verification expectations (Celery ping/result artifacts).

**Alternatives considered**:
- **Move Celery app to Django**: viable long-term (tasks near canonical models) but higher refactor cost now.

## Decision 5: Mirror contract enforcement between Django and FastAPI

**Decision**: Use two complementary gates:
- **DB schema compatibility**: continue using `django` management command `schema_compat_check` (already executed during deploy).
- **API contract compatibility**: maintain an explicit OpenAPI contract under `specs/001-django-fastapi-react/contracts/openapi.yaml` and add a normalized diff gate against FastAPI runtime OpenAPI.

**Rationale**:
- DB drift and API drift are different failure modes; both must be caught.
- Contract-as-artifact supports deploy-time capture and CI diffing.

**Alternatives considered**:
- **Generate OpenAPI directly from Django models**: attractive, but would require additional tooling and tight coupling.

## Decision 6: Staging TLS and security headers

**Decision**: Keep staging-only ACME issuance (`le-staging`) and ensure security headers are applied consistently, with the ability to disable HSTS for staging if needed.

**Rationale**:
- Constitution requires staging-only issuance.
- HSTS can be risky if applied incorrectly on a real domain during staging simulations.

**Alternatives considered**:
- **Always-on HSTS everywhere**: rejected as potentially hazardous in a staging-only cert environment.

## Tooling note: Spec directory prefix ambiguity

**Decision**: Proceed on the current branch spec directory (`specs/001-django-fastapi-react/`).

**Rationale**:
- Spec-Kit scripts warn about multiple `001-*` directories; this does not block plan generation but should be cleaned up to prevent future ambiguity.
