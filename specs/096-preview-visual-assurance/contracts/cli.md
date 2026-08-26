# Preview Control CLI Contract

## Commands

```text
base2-preview preflight --repo PATH
base2-preview status --state-root PATH
base2-preview provider-status --state-root PATH --credential-file PATH
base2-preview dns --observation OWNER_ONLY_JSON
base2-preview evidence --evidence-root PATH --commit SHA --profile-digest SHA256 --run-id ID
base2-preview launch --config OWNER_ONLY_JSON
base2-preview arm-expiry --lease-root PATH --run-id ID --credential-file PATH [--install]
base2-preview extend --lease-root PATH --run-id ID --minutes N --credential-file PATH --python-executable PATH --repo-root PATH
base2-preview verify --state-root PATH --run-id ID
base2-preview destroy --state-root PATH --run-id ID --credential-file PATH [--early-approved]
base2-preview retention --state-root PATH [--apply]
```

## Output

- stdout contains exactly one JSON object.
- Successful commands return exit code `0` and `ok: true`.
- Validation or admission failure returns exit code `2`.
- State integrity failure returns exit code `3`.
- External verification failure returns exit code `4`.
- Authorized lifecycle failure returns exit code `5`.
- Output always contains `secretValuesEmitted: 0`.

## Fixed failure codes

- `OK`
- `RUNTIME_WINDOWS_TOOL`
- `RUNTIME_NON_WSL_REPOSITORY`
- `STATE_PERMISSION_INVALID`
- `LEASE_INTEGRITY_INVALID`
- `LEASE_CONFLICT`
- `DNS_STALE_RECURSIVE`
- `DNS_SPLIT_VIEW`
- `DNS_UNEXPECTED_IPV6`
- `EXPIRY_NOT_ARMED`
- `EXPIRY_PLAN_DRIFT`
- `EVIDENCE_INVALID`
- `EVIDENCE_INCOMPLETE`
- `LIFECYCLE_EXTERNAL_FAILURE`
- `LAUNCH_CONFIG_INVALID`
- `SOURCE_NOT_EXACT_MAIN`
- `PROVIDER_RATE_LIMITED`
- `CLEANUP_RECONCILIATION_REQUIRED`
