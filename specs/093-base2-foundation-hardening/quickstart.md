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

The required CI canary is providerless and safe to run without credentials:

```bash
.venv/bin/python digital_ocean/scripts/python/providerless_canary.py
```

It uses an in-memory provider and documentation-only addresses, then proves exact replay, update, rollback, DNS restoration, and zero residual resources. It performs zero network requests, credential reads, provider mutations, public DNS changes, or certificate requests.

Before requesting live authority, render a redacted exact plan from an ignored environment source:

```bash
.venv/bin/python digital_ocean/scripts/python/live_canary_preflight.py \
  --env-path /absolute/path/to/ignored/base2.env
```

This reads one local credential source but emits no secret value and performs no network request. Review its exact commit, plan digest, provider target, single temporary DNS record, staging-only certificate mode, lease, concurrency, trial count, and cost ceiling before granting provider-read or mutation authority.

The commands below are discovery only. Running a live canary requires a new approval bound to the exact commit, manifest digest, provider project, DNS mutation set, resource ceiling, cost ceiling, lease expiry, and number of trials. Approval for local/providerless work is not live authority.

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
