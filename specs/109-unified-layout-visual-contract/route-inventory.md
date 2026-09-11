# Initial route inventory (T001)

Source: PublicRoutes.jsx, LocalizedExperience.jsx and SettingsCenter.jsx at d29e801.

| Family    | Patterns                                                                                                                 | Existing shell                               | Policy                        |
| --------- | ------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------- | ----------------------------- |
| Home      | `/`                                                                                                                      | Home-specific                                | both rails                    |
| Public    | `/about`, `/privacy`, `/terms`, `/accessibility`, `/contact`, `/search`, `/journal`                                      | PublicShell                                  | both, public safe             |
| Packs     | `/events`, `/portfolio`, `/portfolio/:slug`, `/blog`, `/blog/:slug`, `/docs`, `/docs/:slug`                              | PublicShell; module guarded                  | both, preserve availability   |
| Auth      | `/login`, `/signup`, `/verify-email`, `/forgot-password`, `/reset-password`                                              | public AppShell                              | both, public safe             |
| Account   | `/dashboard`, `/account`, `/accept-invitation`                                                                           | AppShell/account redirect                    | both, preserve auth guards    |
| Tools     | `/workspace`, `/media`, `/operations`, `/admin`                                                                          | AppShell plus local navigation               | both, preserve permissions    |
| Settings  | `/settings/*`: overview, profile, security, privacy, notifications, appearance, language-region, organization, developer | AppShell plus global and category navigation | both; categories remain local |
| Localized | `/:locale/*`: home, about, privacy, terms, accessibility, contact, search, journal                                       | corresponding public shell                   | both; supported locales only  |
| Fallback  | `*`; unsupported locales and disabled modules                                                                            | NotFound/PublicShell                         | both, no protected data       |

All 30 top-level route patterns enumerated. Guest/authenticated/denied, module-on/off,
deep-link/refresh/back and loading/error/empty/long/disabled variants form the planned
state inventory; representative implementation does not certify those all complete.
