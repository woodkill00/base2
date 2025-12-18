# Feature Specification: FastAPI + Django Automated Deployment

**Feature Branch**: `001-fastapi-django-deploy`  
**Created**: 2025-12-18  
**Status**: Draft  
**Input**: User description: "fastapi-django-autmoated, we will be working on a new feature to extend our development, using the deploy.ps1 script to automate the full deployment / upgrade of a digital ocean droplet, it will load all the info an log information into a timestamped folder under loac_run_logs, the goal will be to integrate from fastapi-django-extension.md the build with out own current build"

## User Scenarios & Testing (mandatory)

### User Story 1 - One-command cloud deploy (Priority: P1)

A maintainer triggers a single deployment command that provisions/updates the cloud environment and brings up the full stack with the FastAPI API and Django service integrated behind the existing edge proxy. The process finishes with a concise verification report and a timestamped artifact folder saved locally.

**Why this priority**: It enables consistent, low-friction releases and upgrades with reliable post-deploy diagnostics—critical to delivery cadence and reliability.

**Independent Test**: Run the deployment command once on a prepared environment; confirm the front-end loads on the configured domain, the API health endpoint responds, and the local artifacts folder contains the expected files for the run.

**Acceptance Scenarios**:

1. Given a configured environment and valid cloud credentials, When the deployment command runs to completion, Then the web app home page loads over HTTPS at the configured domain and the API responds with an OK health signal.
2. Given timestamped logging is enabled, When the deployment finishes, Then a new subfolder is created under the local logs directory containing verification artifacts (proxy configs, container state, health checks).

---

### User Story 2 - Update-only redeploy (Priority: P2)

An operator performs an update-only redeploy to roll forward changes without a full rebuild. The command completes faster, preserves data, and still produces the verification artifact set.

**Why this priority**: Most routine changes are incremental; faster redeploys reduce downtime and cost.

**Independent Test**: Run the update-only mode; verify reduced execution time compared to full rebuild, unchanged persisted data, and presence of a complete artifact set for that run.

**Acceptance Scenarios**:

1. Given a running environment, When update-only mode is executed, Then services are updated in-place and remain reachable via the configured domain.
2. Given verification reporting is required, When update-only finishes, Then the artifact set is captured in a timestamped folder with the same structure as full deploy.

---

### User Story 3 - Safe fallback when remote verify unavailable (Priority: P3)

When remote verification cannot run (e.g., IP not discoverable or SSH access blocked), the command finishes local tasks and clearly reports that remote checks were skipped while still saving available local logs.

**Why this priority**: Prevents false failures and supports environments where remote inspection is temporarily unavailable.

**Independent Test**: Run with missing/invalid cloud access; confirm local steps complete, a warning is issued, and a partial artifact folder is produced.

**Acceptance Scenarios**:

1. Given cloud IP discovery fails, When the deployment command completes local tasks, Then the output warns that remote verification was skipped and local logs are still saved.
2. Given logging is mandatory, When remote verification is unavailable, Then a partial but well-formed artifact set exists for troubleshooting.

### Edge Cases

- Cloud access token missing or invalid; deployment should fail fast with a clear error or proceed in a limited mode per policy. [NEEDS CLARIFICATION: fail-fast vs proceed with best-effort local steps]
 - Cloud access token missing or invalid; deployment MUST fail fast with a clear error and MUST NOT proceed in a limited/local-only mode.
- Configuration domain missing or pointing to unmanaged DNS; verification should still capture results and highlight misconfiguration.
- SSH key not present or permission denied; remote verification is skipped with actionable guidance.
- Proxy container not running or misconfigured; artifacts must still capture the attempted state for diagnosis.

## Requirements (mandatory)

### Functional Requirements

- **FR-001**: Provide a single operator command to perform full environment deployment or incremental update, including integration of the FastAPI API and the Django service behind the existing edge proxy.
- **FR-002**: Automatically prepare the runtime environment (isolated environment, dependencies, configuration) prior to deploying services.
- **FR-003**: Load environment configuration from a file into the process environment, ignoring commented or blank lines and supporting quoted values.
- **FR-004**: Optionally refresh allowlists or equivalent access controls based on the operator’s current network unless explicitly skipped.
- **FR-005**: Perform the cloud deploy/upgrade and ensure services for front-end, API, and supporting components start and are routable at the configured domain.
- **FR-006**: Attempt to discover the cloud instance address automatically; if available, run remote verification checks and capture service state and health.
- **FR-007**: Save a verification artifact set locally; when timestamping is enabled, write into a new subfolder named with the execution timestamp.
- **FR-008**: The artifact set MUST include at minimum: container/process state, edge proxy static and dynamic configuration snapshots, environment snapshots (non-sensitive), recent proxy logs, and basic HTTP response headers for the root and API paths.
- **FR-009**: The API MUST expose a health endpoint addressable through the edge proxy path used by the web application.
- **FR-010**: The deployment MUST integrate the FastAPI + Django extension so that API requests route to FastAPI and FastAPI can reach Django on the internal network; the Django admin interface remains non-public by default. In non-production environments only, the admin MAY be publicly routable under additional protections per policy.
- **FR-011**: For this development-production simulation, the deployment MUST use staging certificates only and MUST NOT issue production certificates.
- **FR-012**: On failure, the command MUST emit clear, actionable messages and still persist any available logs/artifacts for diagnosis.

### Key Entities (data involved)

- **Deployment Run**: A single execution of the deployment command; attributes include date/time, mode (full vs update-only), outcome, and artifact path.
- **Log Artifact**: A captured file representing observed system state (e.g., proxy config snapshot, container list, health responses).
- **Cloud Instance**: The managed compute environment; attributes include name, region, IP address, and service inventory.
- **Service Health**: Outcome of health checks for the edge proxy, API, and application routes as observed externally.

### Assumptions & Dependencies

- The operator has a configured cloud account and access credentials.
- The application domain is registered and can be pointed to the environment.
- A single deployment entrypoint is available to the operator (e.g., a CLI command) and can load environment configuration.
- The API exposes a health endpoint reachable through the edge entrypoint.
- Network egress from the deployment host is available during the deploy.

## Success Criteria (mandatory)

### Measurable Outcomes

- **SC-001**: A single deployment command completes with a clear success/fail result and produces a local artifact folder for 100% of runs.
- **SC-002**: With timestamping enabled, 100% of runs create a new subfolder named with the run timestamp under the local logs directory.
- **SC-003**: Post-deploy, the home page loads over HTTPS at the configured domain and the API health route responds OK in under 5 seconds for 95% of runs.
- **SC-004**: Update-only mode reduces total execution time by at least 30% compared to full deploy for the same environment.
- **SC-005**: When remote verification is unavailable, the command still completes local steps and writes a partial artifact set, with an explicit warning, in 100% of such cases.
