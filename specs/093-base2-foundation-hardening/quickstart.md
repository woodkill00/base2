# Quickstart: Feature 093 Development

This feature does not authorize public production deployment. Local work uses Compose; live work uses a separately authorized leased DigitalOcean canary.

## Confirm source

```bash
git switch 093-base2-foundation-hardening
git merge-base --is-ancestor 5320d3fac8decfb77df75c10b4633821f91cea78 HEAD
git status --short --branch
```

## Planning integrity

```bash
python3 scripts/python/validate_feature_093.py
```

It must report zero unresolved findings, unmapped requirements, duplicate tasks, invalid dependencies, or placeholders.

## Local validation and stack

```bash
bash scripts/bash/test.sh
bash scripts/bash/first-start.sh
bash scripts/bash/start.sh --build
bash scripts/bash/health.sh
```

Missing/skipped/unavailable checks are not green.

Focused development commands:

```bash
cd react-app && npm run test:ci
cd ../api && python3 -m pytest
cd ../django && python3 -m pytest
cd .. && python3 -m pytest digital_ocean/tests
```

## Visual port boundary

```bash
git show --stat 0132131292d584172a9b2fa173e439b540abed99
git diff 0132131292d584172a9b2fa173e439b540abed99^ 0132131292d584172a9b2fa173e439b540abed99 -- react-app
```

Do not merge/rebase Feature 093 onto that stale branch.

## Live canary (separate approval required)

```bash
bash digital_ocean/scripts/bash/deploy.sh --help
bash digital_ocean/scripts/bash/teardown.sh --help
```

The canary must create a lease before mutation, publish DNS only after health, and finish with zero owned resources.

## Evidence

- Planning analysis/traceability
- Test, accessibility, visual, performance, and security results
- Redacted config/manifest digests, image identities, SBOM/provenance
- Lease, inventory, DNS, teardown, and cost receipts
- Residual-risk/manual-validation ledger
