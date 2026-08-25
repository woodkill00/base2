# Current Experience Inventory

This ledger records the completed T060-T069 public-experience reconciliation. Every public control is implemented, explicitly disabled with an explanation, or removed.

## Route inventory

| Route                                            | Current access/state                                                                             | Decision                                                                           |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------- |
| `/`                                              | Public, manifest-driven home with enabled/disabled capability states and real CTA destinations   | Implemented and tested                                                             |
| `/login`                                         | Public account login, exposed only when the accounts module is enabled                           | Implemented; deeper identity acceptance remains T080                               |
| `/signup`                                        | Public account registration, exposed only when enabled                                           | Implemented; deeper identity acceptance remains T080                               |
| `/verify-email`                                  | Public token flow                                                                                | Implemented; transactional delivery is disabled by default                         |
| `/forgot-password`                               | Enumeration-safe reset request                                                                   | Implemented; transactional delivery is disabled by default                         |
| `/reset-password`                                | Reset completion                                                                                 | Implemented; deeper session-revocation acceptance remains T080                     |
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

| Surface                            | Current behavior                                                                  | Disposition            |
| ---------------------------------- | --------------------------------------------------------------------------------- | ---------------------- |
| Header/sidebar navigation          | Generated from enabled manifest navigation                                        | Implemented and tested |
| Hero search                        | Navigates to tenant search when enabled; visibly disabled otherwise               | Implemented and tested |
| Primary CTA                        | Contact or first enabled manifest navigation target                               | Implemented and tested |
| Secondary CTA                      | Manifest accessibility route                                                      | Implemented and tested |
| Features/trust/visual copy         | Derived from modules, locales, consent, analytics, search, and operations profile | Implemented and tested |
| Project cards                      | Removed; enabled module inventory is generated from the manifest                  | Removed                |
| Contact send                       | Durable idempotent form/outbox with explicit receipts and errors                  | Implemented and tested |
| Contact social orbs                | Removed because the manifest has no reviewed social URL contract                  | Removed                |
| Footer product/company/legal links | Manifest navigation and validated legal routes                                    | Implemented and tested |
| Footer social links                | Removed because the manifest has no reviewed social URL contract                  | Removed                |
| Brand/copyright                    | Manifest legal identity and current UTC year                                      | Implemented and tested |

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

- Suspense fallback is a short accessible loading state.
- ErrorBoundary and route-level branded 404/500/offline states are implemented.
- Placeholder tests are excluded from this checkpoint's evidence.
- Loading, empty, error, permission, disabled, offline, conflict, rate-limit, reduced-motion, locale, and narrow/wide states have explicit automated coverage; identity and module-only states remain bound to their later checkpoints.

## Required reconciliation

T069 reconciliation completed with zero unexplained public controls. Chromium, Firefox, and WebKit desktop/mobile projects pass without retries; the accessibility/visual matrices remain deterministic; both fixture brands build under enforced JavaScript, CSS, and total-output budgets. Live provider, production certificate, identity-admin, and optional-module activation remain outside this checkpoint.
