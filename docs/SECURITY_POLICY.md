# Dependency Security Policy

Base2 treats dependency results as release controls, not informational dashboards. The machine authority is `scripts/config/dependency-policy.json`; this document explains the same rules for maintainers.

## Severity and remediation

| Severity | Gate behavior       | Remediation deadline    | Exception                               |
| -------- | ------------------- | ----------------------- | --------------------------------------- |
| Critical | Block immediately   | Before merge or release | Never                                   |
| High     | Block               | 72 hours                | Never                                   |
| Moderate | Track and remediate | 30 days                 | Owner-approved, expiring exception only |
| Low      | Track and remediate | 90 days                 | Owner-approved, expiring exception only |

Scanner absence, malformed output, stale evidence, or an interrupted scan is not a pass. Required scanners must report `passed`, `failed`, or `unavailable`; unavailable required evidence leaves the gate incomplete.

## Exception contract

An exception must identify the ecosystem, exact package and advisory, severity, accountable owner, concrete rationale, compensating mitigation, approving owner, next review date, and expiry date. Exceptions last no more than 30 days, cannot cover high or critical findings, and cannot be renewed silently. Expired, overdue, duplicated, ownerless, or malformed entries fail the policy gate.

There are currently no dependency exceptions. Disabling a feature is only a mitigation when tests prove the vulnerable path is unreachable and the exception still satisfies every field above.

## Update and evidence flow

Dependabot opens grouped monthly updates for each npm/Python surface and GitHub Actions. Security advisories bypass the normal cadence. Every update must pass the complete gate, machine-readable audits, license checks, secret/SAST checks, build tests, and relevant runtime tests. Action references and CI service images remain digest-pinned; version comments and update automation may propose reviewed digest changes.

Audit outputs are private CI artifacts. They must not contain credentials, personal environment files, access tokens, or production configuration. Security remediation never grants deployment, publication, credential, payment, or destructive authority.
