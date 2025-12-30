# Multi-Tenant Context & Isolation

This document outlines the tenant context propagation and isolation patterns adopted for the Base2 stack.

- Context carrier: header `X-Tenant-Id`. Traefik forwards headers unchanged; FastAPI attaches tenant id to `request.state.tenant_id` via middleware.
- Enforcement: routes requiring tenant semantics call `require_tenant(request)`; routes with path tenants call `ensure_path_tenant_matches(request, path_tenant)` to block cross-tenant access.
- Rate limits: per-tenant counters maintained in Redis using keys prefixed with `tenant_rl`. Env overrides allow tuning per scope: `TENANT_RATE_LIMIT_<SCOPE>_WINDOW_MS`, `TENANT_RATE_LIMIT_<SCOPE>_MAX_REQUESTS`.
- Quotas: per-tenant quotas stored in Redis with expiry windows; use `check_quota_and_incr(tenant_id, quota, limit, window_seconds)`.
- Logging: the access log includes `request_id` and standard fields. Tenant-aware routes should include `tenant_id` in structured logs where appropriate (never log sensitive data).

These patterns are intentionally minimal and can evolve into subdomain- or path-based tenancy. For database-level isolation, prefer schema-per-tenant or row-level filters enforced in the ORM layer.
