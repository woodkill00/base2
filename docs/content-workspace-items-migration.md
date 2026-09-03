# Items placeholder migration

The historical `/api/items` routes and `/items` screen were demonstration placeholders. The API routes never provided a successful production contract: they returned HTTP 501 for list, detail, and create requests.

Feature 104 keeps those routes non-mutating and adds standard deprecation metadata. Clients receive `Deprecation: true`, a `Link` to `/workspace` with `rel="successor-version"`, and a stable `items_compatibility_read_only` error code. This avoids silently turning a public placeholder into a tenant-writing API.

Generated sites should migrate explicitly:

1. Enable the `content-workspace` module.
2. Create or select a tenant-scoped content definition, normally the `catalog` or `listing` preset.
3. Import any real legacy records through a dry-run and review the exact duplicate outcomes.
4. Update authenticated clients to `/api/content/v1/types/{type_key}/records` and require the established tenant context.
5. Replace links to `/items` with `/workspace` only after role, record-count, and rollback evidence passes.

Removal of the placeholder routes or navigation remains a separately reviewed breaking change. The adapter does not read the legacy global Django `catalog.Item` table, create workspace records, infer a tenant, or broaden caller permissions.
