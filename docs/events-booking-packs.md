# Events and booking packs

Events store UTC instants plus a validated IANA timezone for presentation. Booking depends on events and requires an authenticated public-account principal. Tenant identity is bound at the request, repository, and model layers.

Capacity admission locks the exact tenant-owned event row in one database transaction, checks confirmed seats, and inserts at most one booking per event/attendee. Exact replay returns the existing confirmation; changed replay, closed events, cross-tenant IDs, and oversubscription fail closed. A real PostgreSQL two-thread race proves a capacity-one event produces exactly one confirmation and one rejection.

Email is declared only by booking and remains disabled until a separately configured adapter is activated. Disabling either pack stops its scheduled jobs and preserves data under the module lifecycle policy.
