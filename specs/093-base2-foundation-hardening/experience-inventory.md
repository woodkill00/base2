# Current Experience Inventory

This ledger records the T060-T062 reconciliation. T069 will perform the final cross-browser checkpoint and requires zero unexplained entries.

## Route inventory

| Route                                            | Current access/state                                                                             | Decision                                                                           |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------- |
| `/`                                              | Public, manifest-driven home with enabled/disabled capability states and real CTA destinations   | Implemented and tested                                                             |
| `/login`                                         | Public account login                                                                             | Keep; complete error/security/accessibility matrix                                 |
| `/signup`                                        | Public account registration                                                                      | Keep when enabled by site manifest                                                 |
| `/verify-email`                                  | Public token flow                                                                                | Keep; expired/replay/privacy states                                                |
| `/forgot-password`                               | Public reset request                                                                             | Keep; enumeration-safe and rate-limited                                            |
| `/reset-password`                                | Public reset completion                                                                          | Keep; expiry/replay/session revocation                                             |
| `/items`                                         | Legacy component remains available for future reviewed module extraction but has no public route | Removed from routing; never shows false success                                    |
| `/dashboard`                                     | Protected manifest-branded capability inventory with no sample metrics or dead actions           | Implemented and tested                                                             |
| `/settings`                                      | Protected user settings                                                                          | Keep; consolidate duplicate settings implementations and validate real persistence |
| unknown paths                                    | Manifest-branded catch-all with a working home link                                              | Implemented and tested                                                             |
| `/about`, `/privacy`, `/terms`, `/accessibility` | Published-only content API with loading, empty, offline, and error states                        | Implemented and tested                                                             |
| `/contact`                                       | Manifest-gated durable idempotent form submission                                                | Implemented and tested                                                             |
| `/search`                                        | Manifest-gated tenant search with explicit disabled/result/empty/error states                    | Implemented and tested                                                             |
| `/journal`                                       | Published content collection with loading/empty/offline/error states                             | Implemented and tested                                                             |

OAuth API start/callback routes return HTTP 501 while other Google OAuth behavior exists elsewhere. Feature 093 must choose one supported contract, remove dead routes, and make provider absence explicit. E2E support routes return email bodies and must be impossible to expose outside a verified test profile.

## Public home controls and data

| Surface                            | Current behavior                                                                  | Disposition                                                       |
| ---------------------------------- | --------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| Header/sidebar navigation          | Generated from enabled manifest navigation                                        | Implemented and tested                                            |
| Hero search                        | Navigates to tenant search when enabled; visibly disabled otherwise               | Implemented and tested                                            |
| Primary CTA                        | Contact or first enabled manifest navigation target                               | Implemented and tested                                            |
| Secondary CTA                      | Manifest accessibility route                                                      | Implemented and tested                                            |
| Features/trust/visual copy         | Derived from modules, locales, consent, analytics, search, and operations profile | Implemented and tested                                            |
| Project cards                      | Hardcoded `sample` array                                                          | Replace with portfolio/content pack query plus empty/error states |
| Contact send                       | Client validation followed by explicit no-op                                      | Replace with durable protected form/outbox or disable/omit        |
| Contact social orbs                | `href="#"`                                                                        | Manifest URLs or omit                                             |
| Footer product/company/legal links | Generated fragment links with no route guarantee                                  | Manifest navigation and real route/URL validation                 |
| Footer social links                | Fake fragments                                                                    | Manifest URLs or omit                                             |
| Brand/copyright                    | Manifest legal identity and current UTC year                                      | Implemented and tested                                            |

## Authenticated controls and data

| Surface                        | Current behavior                                        | Disposition                                               |
| ------------------------------ | ------------------------------------------------------- | --------------------------------------------------------- |
| App brand                      | Manifest logo and identity                              | Implemented                                               |
| Avatar fallback                | Local deterministic initial with no third-party request | Implemented                                               |
| Dashboard totals/growth/rating | Removed until backed by a real module source            | Removed                                                   |
| Recent activity                | Removed until backed by an audited tenant feed          | Removed                                                   |
| Create/upload/invite/reports   | Removed until independently enabled and implemented     | Removed                                                   |
| Settings/profile fields        | Multiple page implementations and mixed user shapes     | One account contract, explicit save/error/conflict states |
| Logout                         | Calls auth service then navigates home                  | Keep; verify server revocation/failure/offline behavior   |

## System and status states

- Suspense fallback remains a short accessible loading state; T069 will finalize its visual checkpoint.
- ErrorBoundary and route-level branded 404/500/offline states are implemented.
- Several tests self-identify as placeholders and therefore cannot count as final evidence.
- Loading, empty, error, permission, disabled, offline, conflict, rate-limit, maintenance, reduced-motion, locale, and narrow/wide states require explicit route/control coverage.

## Required reconciliation

T060 must derive an automated route/control inventory from the rendered application. T061-T068 implement the accepted behaviors. T069 compares that output with this ledger and fails if any visible interactive element has no tested action, disabled explanation, or removal record.
