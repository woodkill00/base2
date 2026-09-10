# Production governance inventory

This inventory documents implemented boundaries; it is not a claim of legal,
privacy, security, or accessibility certification. Site owners remain
responsible for reviewing the generated site's actual jurisdiction, content,
vendors, and operating choices before activation.

| Area          | Base2 contract                                                                                                                                               | Owner evidence                                  |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------- |
| Data classes  | Account, tenant content, media, operational metadata, audit, and delivery records are classified in the generated manifest. Payment-card data is prohibited. | Exact manifest and schema inventory             |
| Purposes      | Authentication, requested service delivery, tenant administration, reliability, security, and owner-enabled optional features only.                          | Enabled-module and consent inventory            |
| Consent       | Necessary processing is separate from optional analytics and marketing; denial does not block required service use.                                          | Consent receipt and policy version              |
| Retention     | Each data family has a bounded policy; legal hold and deletion exceptions must be explicit.                                                                  | Retention run receipt and unresolved exceptions |
| Vendors       | No provider is implied. Each activated provider requires an inventory entry, scoped reference, region, purpose, and separate approval.                       | Provider activation receipt                     |
| Regions       | Region is an explicit release-plan field and cannot be inferred from developer state.                                                                        | Immutable release manifest                      |
| Accessibility | Keyboard, screen reader, zoom, contrast, motion, RTL, locale, responsive, browser, and visual evidence are required; passing tests are not certification.    | Exact-source accessibility matrix               |
| Incidents     | Health failures create durable tenant-safe incidents and bounded alerts; provider loss cannot fabricate success.                                             | Incident timeline and delivery receipt          |
| User rights   | Access, export, correction, and deletion workflows are tenant scoped, authenticated, auditable, and recovery aware.                                          | Data-rights receipt and isolated restore proof  |

Production activation must replace synthetic evidence with exact-environment
evidence, confirm the real vendor and regional inventory, and obtain all
separately required owner/provider approvals.
