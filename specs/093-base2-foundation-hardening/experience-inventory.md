# Current Experience Inventory

This is the pre-implementation ledger. T060 creates the automated crawler/control contract and T069 requires zero unexplained entries. “Keep” means preserve intent after manifest, state, security, and accessibility integration—not accept current implementation unchanged.

## Route inventory

| Route | Current access/state | Decision |
|---|---|---|
| `/` | Public home, hardcoded brand/content and mixed real/no-op controls | Keep and rebuild manifest/content driven |
| `/login` | Public account login | Keep; complete error/security/accessibility matrix |
| `/signup` | Public account registration | Keep when enabled by site manifest |
| `/verify-email` | Public token flow | Keep; expired/replay/privacy states |
| `/forgot-password` | Public reset request | Keep; enumeration-safe and rate-limited |
| `/reset-password` | Public reset completion | Keep; expiry/replay/session revocation |
| `/items` | Public route to API-backed UI whose service is an explicit placeholder/501 | Remove from core navigation/public routing until delivered as a reviewed module; never show false success |
| `/dashboard` | Protected but contains hardcoded metrics/activity and dead quick actions | Keep shell; replace each card/action with real enabled-module data or remove |
| `/settings` | Protected user settings | Keep; consolidate duplicate settings implementations and validate real persistence |
| unknown paths | No catch-all route | Add manifest-branded 404 and error recovery |
| `/about`, `/contact`, `/privacy`, `/terms`, `/accessibility`, `/search` | Sections/anchors, absent, or not real routes | Add as manifest/content-driven core routes |

OAuth API start/callback routes return HTTP 501 while other Google OAuth behavior exists elsewhere. Feature 093 must choose one supported contract, remove dead routes, and make provider absence explicit. E2E support routes return email bodies and must be impossible to expose outside a verified test profile.

## Public home controls and data

| Surface | Current behavior | Disposition |
|---|---|---|
| Header/sidebar navigation | Partially scrolls only `home` and `features` | Generate from manifest and validate every target |
| Hero search (“Ask anything”) | Stores local text; no submit/action | Connect to authorized site search or omit |
| “Get Started” | Navigates to signup | Keep only when registration enabled; otherwise manifest action |
| “View Documentation” | Empty callback | Connect to enabled docs module/URL or omit |
| Features/about/trust/visual copy | Hardcoded marketing copy | Move to content/profile records |
| Project cards | Hardcoded `sample` array | Replace with portfolio/content pack query plus empty/error states |
| Contact send | Client validation followed by explicit no-op | Replace with durable protected form/outbox or disable/omit |
| Contact social orbs | `href="#"` | Manifest URLs or omit |
| Footer product/company/legal links | Generated fragment links with no route guarantee | Manifest navigation and real route/URL validation |
| Footer social links | Fake fragments | Manifest URLs or omit |
| Brand/copyright | Hardcoded “SpecKit” and year | Manifest legal identity and current/configured year |

## Authenticated controls and data

| Surface | Current behavior | Disposition |
|---|---|---|
| App brand | Hardcoded rocket and “App” | Manifest identity |
| Avatar fallback | Third-party placeholder URL | Local deterministic privacy-safe fallback |
| Dashboard totals/growth/rating | Hardcoded values | Real module-scoped metrics or omit |
| Recent activity | Hardcoded events/times | Audited tenant activity feed or omit |
| Create New | No handler | Module-declared action or omit |
| Upload File | No handler | Media module action with policy or omit |
| Invite User | No handler | Organization invitation action when authorized or omit |
| View Reports | No handler | Enabled report module action or omit |
| Settings/profile fields | Multiple page implementations and mixed user shapes | One account contract, explicit save/error/conflict states |
| Logout | Calls auth service then navigates home | Keep; verify server revocation/failure/offline behavior |

## System and status states

- Suspense fallback is an inline generic “Loading...” rather than branded accessible skeleton/state.
- ErrorBoundary exists, but route-level branded 404/500/offline/retry contracts are incomplete.
- Several tests self-identify as placeholders and therefore cannot count as final evidence.
- Loading, empty, error, permission, disabled, offline, conflict, rate-limit, maintenance, reduced-motion, locale, and narrow/wide states require explicit route/control coverage.

## Required reconciliation

T060 must derive an automated route/control inventory from the rendered application. T061-T068 implement the accepted behaviors. T069 compares that output with this ledger and fails if any visible interactive element has no tested action, disabled explanation, or removal record.
