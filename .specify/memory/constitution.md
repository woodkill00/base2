# Base2 Constitution

This document defines the **governing principles and development guidelines** for Base2.  
All contributions (human or AI) MUST comply.

---

## 0) How we build here (Spec-Driven Development)

1. **Constitution → Spec → Plan → Tasks → Code**  
   - *Constitution*: immutable principles (this file).  
   - *Spec*: user-facing outcomes, scenarios, acceptance, constraints (no implementation detail).  
   - *Plan*: technical approach, architecture, tradeoffs, interfaces.  
   - *Tasks*: small, verifiable steps mapping to tests and deliverables.  
2. **Separation of concerns across docs is mandatory**: keep the spec high-level and user-oriented; keep implementation details in the plan; keep step-by-step execution in tasks.

---

## 1) Non‑negotiable engineering standards

### I. Test-First Development (TDD by default)
- All changes MUST be developed with tests written first (or alongside, when refactoring).  
- Nothing merges without passing tests and an explicit review of coverage impact.  

### II. Environment Parity (Dev mimics Production)
- Development MUST run the same topology as production: same services, networking, and trust boundaries.
- Differences are permitted **only** when explicitly scoped (e.g., staging certificates, debug tooling), and must be documented.

### III. Container-first, Compose-first
- All services MUST run together via Docker Compose with health checks and clear dependencies.
- Local setup MUST be “clone → configure `.env` → run script” with no hidden manual steps.

### IV. Single-entrypoint operations
- The *only supported* way to deploy/update/test the production-like environment is via:
  - `digital_ocean/scripts/powershell/deploy.ps1`
- If you need a new operational capability, add it to the script and document it (don’t invent ad-hoc commands).

### V. Observability is a feature
- Every deploy/update run MUST generate an artifact set (logs, configs, health responses, non-sensitive env snapshots).
- Failures MUST be diagnosable from captured artifacts—prefer “fail fast with clear error” over silent partial success.

---

## 2) Architecture governance

### I. Source of truth for domain models (Django)
- **Django is the canonical source of truth for domain models.**
- New domain concepts MUST begin in `common/models.py`.
- Additional Django apps MAY define *wrappers/adapters* around `common/models.py` to add app-specific behavior, but MUST NOT fork the “primordial” model design.

### II. API mirror contract (FastAPI)
- FastAPI is the external/internal API surface for the project.
- FastAPI schemas MUST **faithfully mirror** Django model semantics (fields, validation, constraints, relationships) and expose them via a stable, versioned API contract.
- Any change to a Django model that impacts the API MUST:
  1) update the API schema/contract  
  2) include backward-compat strategy (versioning or migration)  
  3) update tests and documentation

### III. Frontend contract (React)
- React is the user-facing client.
- All calls MUST be internal API calls and follow best-practice security defaults:
  - No sensitive tokens in `localStorage` / `sessionStorage`
  - Prefer **HttpOnly, Secure, SameSite cookies** for session/refresh credentials
  - Enforce CSRF protection for cookie-based auth
- Frontend MUST be treated as untrusted input at all times.

### IV. Networking and trust boundaries
- Public edge entrypoint: Traefik.
- Databases, queues, and admin surfaces are **internal-only by default**.
- Any non-production public exposure (e.g., admin in dev) MUST be explicitly gated by:
  - allowlists and/or strong auth
  - explicit documentation
  - automated verification

### V. TLS and certificates policy
- Traefik MUST issue/serve certificates **only in staging** for this production-like simulation.
- Production certificates MUST NOT be issued from this environment (to avoid rate-limit and trust mistakes).

---

## 3) Security governance (baseline)

- Enforce HTTPS everywhere in staging/prod-like environments.
- Use defense-in-depth headers on public routes (HSTS, X-Content-Type-Options, X-Frame-Options, conservative Referrer-Policy).
- Passwords:
  - hashed using modern, slow hashing (argon2/bcrypt) and never logged
  - rate-limited login attempts
- OAuth:
  - Authorization Code + PKCE where applicable
  - strict redirect URI allowlists
- Secrets:
  - never committed
  - redacted in logs/artifacts by default

---

## 4) Documentation governance

- Every user-facing behavior MUST be documented (setup, env vars, scripts, endpoints, UI flows).
- Every breaking change MUST include a migration guide.
- “Docs are part of the product”: docs changes are reviewed like code.

---

## 5) Change management

- This constitution supersedes all other practices.
- Amendments require:
  1) rationale  
  2) scope/impact  
  3) migration plan (if behavior changes)  
  4) version bump + date

---

**Version**: 2.0.0  
**Ratified**: 2025-12-24  
**Last Amended**: 2025-12-24
