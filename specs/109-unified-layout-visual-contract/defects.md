# Initial defect ledger

| ID      | Evidence / cause                                                            | Repair and regression                                                 |
| ------- | --------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| L109-01 | AppShell lacks right slot; left rail initially hidden                       | shared structure, rail-presence assertions                            |
| L109-02 | PublicShell omits both rails; Home owns unrelated navigation                | route policy and staged consolidation                                 |
| L109-03 | Dashboard/Settings nest Navigation below GlassHeader                        | single global header assertion and screenshot review                  |
| L109-04 | Settings uses viewport-based two-column grid inside shrinking main track    | container-based reflow; geometry and narrow checks                    |
| L109-05 | GlassSidebar closes on every selection and unmounts mobile panels           | persistent desktop rails; explicit drawer lifecycle/scroll tests      |
| L109-06 | Home actions are section-bound and several shortcuts explicitly unavailable | retain useful Home actions, do not invent working permissions or data |

Before evidence: `.artifacts/layout-109/before-109/` with synthetic local identities.
New attempts use distinct paths. These are findings, not claims that repairs are done.
