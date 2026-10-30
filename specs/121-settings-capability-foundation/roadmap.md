# Site-family settings roadmap

This is an inventory, not an activation promise. **Existing** means source-backed
foundations already exist; it does not assert this candidate passed live acceptance.
**Limited** means the named boundary must remain visible. **Planned** means no working
control is offered. All future mutations require typed canonical Django semantics,
API authorization/tenant checks, audit/recovery design and user-facing acceptance.

| Site family                                         | Existing foundation                                                  | Limited / deployment-managed                                           | Planned settings and engines                                               |
| --------------------------------------------------- | -------------------------------------------------------------------- | ---------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Any account site                                    | Profile, security, privacy, personal preferences, organization roles | No inheritance; notification choices stored, delivery engine not wired | Scoped policy inheritance; notification digest execution and concurrency   |
| Publishing, blog, portfolio, gallery, documentation | Content records, workspace, media, public content routes             | Module/profile enablement requires generated deployment                | Editorial approval, revision policy, audience/scheduling policy UI         |
| Catalog / storefront                                | Catalog content and module contracts                                 | Commerce provider is none/local_fake; not live billing                 | Taxes, shipping, returns, real provider lifecycle, budgets/approvals       |
| Marketplace / listings                              | Listing/content foundations                                          | No complete seller, fulfillment or payout engine                       | Seller onboarding, commissions, disputes, policy scopes                    |
| Community / social                                  | Pre-moderated submission foundation                                  | Not a complete social graph/feed or configurable moderation engine     | Audience defaults, block/mute/report, moderation queues, reputation        |
| Events / booking                                    | Event inventory and transactional reservations                       | Adapter and module configuration deployment-managed                    | Availability, buffers, cancellations, reminders, calendar integrations     |
| CRM / service / support                             | Organization permissions, universal workspace and content presets    | Not a complete CRM automation/support engine                           | Objects, pipelines, ownership, record visibility, deduplication, SLA rules |
| Membership / subscription / SaaS                    | Accounts, organizations, module contracts                            | No real entitlement/billing provider by flag alone                     | Plans, seats, lifecycle policies, entitlements, trials, usage              |
| Forms / lead capture                                | Existing forms/contact foundation                                    | Delivery/retention configured by generated profile                     | Form builder, consent-version policy, routing, anti-abuse controls         |

## Delivery order

1. Feature 121: role-aware discovery, personal save integrity, searchable deep links,
   applied appearance, truthful module availability and audit isolation.
2. Delivery preferences: versioned notification set plus actual delivery consumers,
   unsubscribe/mandatory policy, digest jobs and failure observability.
3. Workspace policy: schema-backed publishing/approval/record visibility and preview
   of effective permissions. Do not equate a product seat with data access.
4. Commerce, social and CRM engines separately, each behind explicit capability and
   provider readiness contracts with end-to-end tests before controls become active.

## Research principles and official sources

Borrow patterns, not branding or unimplemented promises: group organization and
purchasing policies ([Amazon groups](https://business.amazon.com/en/learn/groups),
[guided buying](https://business.amazon.com/en/solutions/compliance-management/guided-buying));
separate own/team/all record access from feature seats
([HubSpot permissions](https://knowledge.hubspot.com/user-management/hubspot-user-permissions-guide));
make permission dependencies explicit
([Salesforce dependencies](https://help.salesforce.com/s/articleView?id=platform.users_perm_dependencies.htm&language=en_US&type=5));
separate common identity from app-specific controls
([Meta account](https://about.fb.com/news/2026/04/meta-account/)).

The full reusable capability-group inventory and staged family acceptance matrix is
in [site-family-matrix.md](site-family-matrix.md). Its broader P2–P5 controls remain
planned; Feature 121 delivers only this bounded foundation.
