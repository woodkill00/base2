# Quickstart

```bash
# Explain the minimum safe plan for current changes.
scripts/bash/assure.sh plan --tier auto

# Execute it with compact output.
scripts/bash/assure.sh run --tier auto

# Force the existing complete release authority.
scripts/bash/assure.sh run --tier release
```

Use `auto` during ordinary iteration, `standard` before publishing a draft PR, and `release` only at the final merge/release boundary. A policy, auth, tenancy, migration, dependency, workflow, deployment, backup, restore, test-infrastructure, or unknown change escalates automatically. Full logs remain under the private ignored evidence directory and are never streamed by default.
