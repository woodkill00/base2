# Content workspace operations

## Measured bounds

The workspace rejects work beyond these server-owned ceilings. Tests use deterministic boundary fixtures at the exact limit and one unit beyond it.

| Surface                                 |        Default |               Maximum |
| --------------------------------------- | -------------: | --------------------: |
| Fields per schema                       | preset-defined |                    64 |
| Filters per query                       |              0 |                    16 |
| Sort fields                             |         `slug` |                     3 |
| Page size                               |             25 |                   100 |
| Relationship expansions                 |              0 |                     4 |
| Relationship traversal depth            |              1 |                     2 |
| Relationships per field                 | schema-defined |                    50 |
| Upload                                  |           none |                10 MiB |
| Image edge / decoded pixels             |           none |   12,000 / 40,000,000 |
| Import/export source                    |           none |       5,000,000 bytes |
| Import rows / columns / cell characters |           none | 10,000 / 128 / 20,000 |
| Structured nesting / collection members |           none |               8 / 256 |
| Asset/import upload grant               |           none |           300 seconds |
| Asset/export download grant             |           none |            60 seconds |
| Export artifact availability            |           none |                1 hour |
| Recovery members / plaintext            |           none |     100,000 / 100 MiB |

Queries bind tenant, type, schema, permission projection, filters, ordering, and page limit into opaque cursors. Relationship reads are capped and never accept arbitrary recursive expansion. Import/export workers rediscover durable work in bounded batches and terminal failures retain closed error codes.

## Backup and isolated restore

Workspace recovery includes definitions, fields, workflows, records, versions, relationships, views, import/export jobs, audit references, asset metadata, asset bindings, and per-collection hashes. The bundle payload is encrypted; output contains no raw key and has owner-only permissions.

Set `CONTENT_WORKSPACE_RECOVERY_KEY` from an approved runtime secret reference. Do not place it in an argument, repository file, shell history, report, or Discord message. Inputs and outputs are confined beneath `.artifacts/workspace-recovery/`.

```bash
scripts/bash/content-workspace-recovery.sh backup \
  .artifacts/workspace-recovery/synthetic-snapshot.json \
  .artifacts/workspace-recovery/synthetic-backup.json

scripts/bash/content-workspace-recovery.sh restore \
  .artifacts/workspace-recovery/synthetic-backup.json \
  .artifacts/workspace-recovery/isolated/restored.json
```

Restore refuses existing targets, configured live data roots, out-of-root paths, wrong keys, modified manifests, changed ciphertext, mismatched counts/hashes, and broken references. It never restores directly into a database. Importing a verified snapshot into any database is a separate reviewed operation.

## Failure response

Do not reinterpret a failed, cancelled, expired, quarantined, or dependency-unavailable state as success. Preserve the closed error code and integrity digest, correct the underlying cause, and replay only through the same idempotent job identifier. Never bypass schema-version, tenant, permission, hash, scan, or approval checks. If evidence is malformed or stale, generate new evidence rather than editing the receipt.
