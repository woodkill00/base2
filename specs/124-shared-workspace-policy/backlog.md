# Ordered capability queue after Feature 124

Status: planning only. User approved pursuing the roadmap on 2026-10-31; this queue
is not implementation evidence, a live-provider authorization or permission to merge/
deploy/spend. Each slice requires its own constitution -> spec -> plan -> tasks ->
analysis -> tests -> canonical Django -> FastAPI -> React sequence and independent
acceptance. Keep one bounded functional slice active before expanding families.

| Order | Capability slice                                                                 | Family coverage contributed, not completed                                                  | Exit evidence before advancing                                                                                                                            |
| ----- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0     | Finish current baseline release evidence without bypassing blocked security work | Shared foundation                                                                           | Exact-source gate; known blockers explicit; Feature 122 stopped restriction honored                                                                       |
| 1     | Feature 124 shared workspace policy + real local review notifications            | Business/service, portfolio/creative, publication/blog/newsletter, documentation/knowledge  | Four feature outcomes, multi-user privacy/concurrency and preserved design                                                                                |
| 2     | Consent-aware form -> contact/lead -> bounded sales pipeline                     | Business/service, CRM/sales                                                                 | Canonical people/company relations, own/team visibility, deduplication with audit/rollback, constrained stages; no arbitrary scripts                      |
| 3     | Requester -> ticket -> queue/assignment -> permitted reply                       | Help desk/support                                                                           | Private notes never leak, assignment races, requester scope, controlled adapter failures; SLA expansion separate                                          |
| 4     | Audience-scoped posts + block/report + moderation decision                       | Community/social, nonprofit community use                                                   | Direct/search/notification privacy propagation, moderator scope, appeal history; messaging/social graph separate                                          |
| 5     | Catalog -> stock hold -> order -> cancellation/return                            | Storefront/B2B commerce                                                                     | Money/currency precision, concurrency, replay-safe fake-provider transactions, permission-separated refunds; no live payments                             |
| 6     | Membership/seat -> entitlement -> gated content                                  | SaaS/customer portal, membership/association/paid community                                 | Seat races, role vs billing privilege, current-session/worker/cache revocation, cancellation/grace states                                                 |
| 7     | Seller listing -> moderation -> order ownership                                  | Multi-vendor marketplace, directory/classifieds/job listings                                | Seller/buyer/moderator boundaries, listing expiry, dispute lifecycle; live settlement deferred                                                            |
| 8     | Availability/resource -> reservation -> cancellation/reminder                    | Appointments/resource booking, events/conferences/ticketing, rental/property/local services | Last-slot races, DST/buffers, capacity reduction, reminder rescheduling; deposits/leases separate                                                         |
| 9     | Volunteer/campaign composition                                                   | Nonprofit/volunteer/community organization                                                  | Consent, coordinator roles, private directories, event integration; donations reuse separately accepted commerce                                          |
| 10    | Scoped connectors and bounded automation                                         | Cross-family integration                                                                    | Revocable grants, signed/replay-safe events, dry-run, idempotency, bounded recursion, health/reconciliation; each external provider separately authorized |
| 11    | Project/task/client sharing                                                      | Project/client/team workspace                                                               | Project-scoped guests, task workflow, reminders, audit and client isolation                                                                               |
| 12    | Course/cohort/enrollment/progress                                                | Learning/course portal                                                                      | Learner privacy, instructor cohort scope, release rules, entitlement integration; credentials separately scoped                                           |
| 13    | Application -> review -> interview                                               | Hiring/applicant portal                                                                     | Candidate consent/retention, assigned hiring-team access, interview privacy and scheduling; no broad exports by default                                   |

All 19 families in Feature 121's matrix are represented above; none gains a support
claim merely by appearing in this queue. Follow-up acceptance may reorder dependent
slices based on concrete need, but must not combine all engines into one giant PR.
Specialized regulated/high-risk domains remain separately scoped, not implicitly
promised. Do not turn stored-only controls into active promises without consumers.

## Security-specific interrupted-flow follow-up

The Feature 124 shared dirty-draft guard covers ordinary profile, appearance/language,
notification, privacy-input and (when integrated) workspace-policy drafts. Embedded
AccountCenter MFA enrollment and one-time recovery-code workflows retain their existing
credential lifecycle; they are not a generic persisted settings draft. Separately design
and test interrupted enrollment/recovery warnings, dismissal and authentication recovery
without retaining one-time secrets across category/account changes or weakening cleanup.
This follow-up is planned, not implemented or accepted by the ordinary-draft guard tests.
