
# Base2 Constitution


## Core Principles

### I. Test-First Development
All code MUST be developed using test-driven development (TDD).  
Tests are written before implementation, must fail initially, and must pass after code is complete.  
No feature or fix is merged without passing tests and coverage review.

### II. Seamless Dockerization
All services MUST run together via Docker Compose.  
Containers are built to work together out-of-the-box, with health checks and clear interdependencies.  
No manual steps required beyond provided scripts.

### III. Documentation-Driven
Every feature, change, or fix MUST be accompanied by updated documentation.  
Docs cover setup, usage, environment variables, and scripts.  
No undocumented features or breaking changes.

### IV. User-Friendly Operations
All processes (build, start, stop, test, logs) MUST be runnable via scripts.  
No required manual commands outside documented scripts.  
All required configuration is stored in `.env`/`.env.example` only.

### V. Environment Variable Discipline
All required variables are defined in `.env.example` and loaded from `.env`.  
Scripts and code MUST pull variables from `.env` or replace them automatically.  
No hardcoded secrets or config outside `.env`.


## Additional Constraints

- All containers must pass health checks before considered "ready".
- No sensitive information is committed; only `.env.example` is tracked.
- All dependencies and versions are documented.
- All breaking changes require a migration guide in the documentation.


## Development Workflow

- All features/changes require updated tests and documentation before merge.
- Code reviews verify TDD, Docker integration, documentation, and env discipline.
- Any new or changed feature triggers a documentation update.
- Scripts are the only supported way to run, build, or test the project.


## Governance

- This constitution supersedes all other practices.
- Amendments require documentation, approval, and migration plan.
- All PRs/reviews must verify compliance with these principles.
- TODO(RATIFICATION_DATE): Set original ratification date.
- **Version**: 1.1.0 | **Ratified**: TODO(RATIFICATION_DATE) | **Last Amended**: 2025-11-21
