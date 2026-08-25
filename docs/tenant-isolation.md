# Tenant isolation and PostgreSQL defense decision

Base2 treats a canonical `site_id`/organization slug as the tenant key. It is
required at the HTTP boundary, carried in tenant-owned job envelopes, included
in every cache namespace, bound transaction-locally on database checkout, and
re-applied as an explicit predicate in repository queries. Pooled connections
are rolled back and reset before reuse, including exception paths.

The canonical Django models retain database uniqueness and relationship
constraints. Non-superuser Django admin queries and object permissions are
limited to active organization memberships. Superuser access is an explicit
operator boundary and remains audited operational access, not tenant access.

## PostgreSQL row-level security decision

RLS is not presented as active defense while Django migrations, admin, and the
FastAPI runtime share the table-owning database role. PostgreSQL table owners
bypass ordinary RLS; forcing RLS on that shared role would either break
migrations/admin or require a user-settable bypass flag and provide misleading
protection.

Before production activation, provisioning must create a non-owner runtime role
with no `BYPASSRLS`, grant only required DML, install `site_id =
current_setting('app.tenant_id', true)` policies on every tenant-owned table,
and use a distinct migration role. The direct-query/pool-reuse acceptance test
must then run against PostgreSQL and prove missing, wrong, reset, rollback, and
migration-role behavior. Until that role split is supplied, explicit query
scoping plus transaction-local binding is required and the production RLS
control is reported as `deferred`, never `passed`.
