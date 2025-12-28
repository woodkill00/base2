# Feature Specification: Full-stack Baseline

**Feature Branch**: `001-django-fastapi-react`  
**Created**: 2025-12-24  
**Status**: Draft  
**Input**: User description: "django-fastapi-react, using this file as a base"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Production-like deploy verification (Priority: P1)

As a maintainer, I can deploy/update the full stack to a staging-like environment and receive a clear verification report so I can trust the environment and diagnose failures.

**Why this priority**: Without a repeatable deploy + verification loop, it’s hard to validate any other user-facing functionality.

**Independent Test**: Can be tested by running the standard deployment workflow end-to-end and confirming a successful verification report plus a complete artifact bundle.

**Acceptance Scenarios**:

1. **Given** no existing environment, **When** a full deploy is executed, **Then** all services become healthy and a verification report is produced.
2. **Given** an existing environment, **When** an update deploy is executed, **Then** the environment remains healthy and a new verification report is produced.
3. **Given** a failed deployment, **When** verification runs, **Then** artifacts (logs, status, and probe outputs) are still captured for diagnosis.
4. **Given** verification probes protected operational/admin endpoints without credentials, **When** requests are made, **Then** access is denied.
5. **Given** the environment is configured for staging-like TLS, **When** certificates are issued/renewed, **Then** production certificate issuance is not attempted.
6. **Given** the environment is running, **When** health endpoints are probed, **Then** they report healthy status for the edge proxy, web client, API, and core dependencies.

---

### User Story 2 - Signup and login/logout (Priority: P2)

As a visitor, I can create an account and sign in/out securely so I can access protected parts of the product.

**Why this priority**: This is the core user capability the rest of the UX depends on.

**Independent Test**: Can be tested by completing signup, seeing an authenticated session, logging out, and confirming protected pages require re-auth.

**Acceptance Scenarios**:

1. **Given** I have no account, **When** I sign up with a valid email and password, **Then** my account is created and I am signed in.
2. **Given** my credentials are invalid, **When** I attempt to sign in repeatedly, **Then** I receive a generic error and further attempts are rate limited.
3. **Given** I am signed in, **When** I sign out, **Then** my session is invalidated and protected routes require sign-in again.
4. **Given** I am signed in and perform a state-changing action, **When** I do not present anti-forgery protections (CSRF protection), **Then** the request is rejected.

---

### User Story 3 - Dashboard and settings (Priority: P3)

As a signed-in user, I can view a dashboard and update my profile settings so I can confirm identity and manage my account.

**Why this priority**: This validates authenticated navigation and basic profile persistence.

**Independent Test**: Can be tested by loading the dashboard, changing a profile field, and seeing it reflected in a subsequent “current user” view.

**Acceptance Scenarios**:

1. **Given** I am signed in, **When** I open the dashboard, **Then** I see my identity (e.g., email) and basic account metadata.
2. **Given** I am signed in, **When** the client loads my session state, **Then** it can retrieve a “current user” view and render an authenticated state.
3. **Given** I am signed in, **When** I update an allowed profile field, **Then** the change persists and is visible on refresh.
4. **Given** my session expires, **When** I open a protected page, **Then** I’m redirected to sign in with a user-friendly message.

---

### User Story 4 - Sign in with Google (Priority: P4)

As a user, I can sign in with Google so I can access the product without creating a separate password.

**Why this priority**: Provides a common alternative login method and validates a secure third-party sign-in flow.

**Independent Test**: Can be tested by completing a third-party sign-in flow and ending in an authenticated session.

**Acceptance Scenarios**:

1. **Given** I choose “Sign in with Google”, **When** I complete the provider flow successfully, **Then** I am signed in and returned to the dashboard.
2. **Given** I cancel or the provider rejects access, **When** I return to the app, **Then** I see a non-sensitive error and remain signed out.

### Edge Cases

- Stale or split-horizon DNS causes some subdomains to resolve to an old environment.
- TLS certificate issuance fails or uses an unintended certificate authority.
- A protected internal tool endpoint is accidentally exposed without authentication.
- User attempts to reuse an email address that already exists.
- Brute-force login attempts trigger rate limiting without revealing account existence.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a production-like environment composed of an edge proxy, web client, API service, domain/persistence service, and database.
- **FR-002**: System MUST route web client traffic and API traffic through the edge proxy using consistent host/path rules across local and staging-like environments.
- **FR-003**: System MUST restrict operational/admin tools to authenticated and/or allowlisted access.
- **FR-004**: System MUST support a staging-like TLS configuration that does not attempt production certificate issuance.

- **FR-010**: System MUST allow a visitor to create an account with email and password.
- **FR-011**: System MUST allow a user to sign in and sign out.
- **FR-012**: System MUST prevent account enumeration via error messages for signup and login.
- **FR-013**: System MUST apply rate limiting to authentication endpoints.
- **FR-014**: System MUST protect state-changing requests against cross-site request forgery (CSRF) when using cookie-based authentication.

- **FR-020**: System MUST provide an authenticated “current user” endpoint/view used by the client to render identity state.
- **FR-021**: System MUST provide a dashboard view that is accessible only to authenticated users.
- **FR-022**: System MUST allow authenticated users to update allowed profile fields.

- **FR-030**: System MUST support Google sign-in.
- **FR-031**: OAuth sign-in MUST fail securely (no session created) when the flow is canceled, invalid, or tampered with.

- **FR-040**: System MUST provide health endpoints sufficient to validate basic liveness and core dependencies.
- **FR-041**: System MUST produce a structured verification report for each deploy/update run.
- **FR-042**: System MUST capture deploy/verification artifacts for each run, including enough information to diagnose failures.

### Assumptions

- The product initially supports a single user role (end user) plus an administrator role for internal management.
- Cookie-based sessions are the default authentication mechanism.
- Staging-like environments prioritize safe defaults over production issuance of certificates.

### Key Entities *(include if feature involves data)*

- **User**: Account identity; includes email, status (active/disabled), and timestamps.
- **Session**: Represents an authenticated login state with an expiration policy.
- **OAuth Identity**: Link between a User and an external provider identity (Google) used for third-party sign-in.
- **Audit Event**: Security-relevant event record (e.g., login failures, account changes) with timestamps and a request correlation identifier.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A full deploy produces a successful verification report with zero missing required artifacts.
- **SC-002**: 95% of health checks complete in under 5 seconds in a staging-like environment.
- **SC-003**: A new user can complete signup and reach the dashboard in under 2 minutes.
- **SC-004**: 99% of login attempts under normal conditions complete in under 2 seconds.
- **SC-005**: 0 successful unauthenticated accesses to protected operational/admin endpoints during verification.
