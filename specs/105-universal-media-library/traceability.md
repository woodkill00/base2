# Traceability

| Concern | Implementation | Verification |
|---|---|---|
| Closed capability | `modules/media`, module catalog, generated profiles | manifest tests |
| Tenant isolation | forced RLS, scoped repository, permission route | migration/repository/route tests |
| Hostile ingest | media policy and byte admission | policy/format negative tests |
| Lifecycle/replay | lifecycle service, optimistic versions | lifecycle/model/repository tests |
| Safe processing | scanner plus deterministic derivative processor | scanner/processor/worker tests |
| Safe delivery | encrypted private store and restrictive headers | storage/route tests |
| Accessibility | semantic React page and non-drag upload path | component axe and browser matrix |
| Disabled residue | conditional router/navigation generation | profile and registration tests |
| Publication/provider safety | explicit staged tasks B019-B023 | owner approvals and live receipts |
| Private visibility and tenant writes | repository visibility predicates, composite tenant references, scoped worker mutations | route/repository negative tests and disposable PostgreSQL acceptance |
| Recent authentication | sensitive-action claim-age guard | missing, malformed, expired, and current claim tests |
| Bounded replay-safe ingest | streaming admission, idempotency, quota, and backpressure | route integration and hostile upload tests |
| Governed runtime processing | scanner freshness, bounded parser subprocess, persistent jobs/inspection/audit | worker/runtime tests and type/static checks |
| Exact export semantics | selected IDs plus fields and filters in the package consumed by the worker | route/repository/worker contract tests |
| Cursor context integrity | tenant and normalized-filter signature binding | cross-tenant and cross-query replay rejection tests |
| Governance enforcement | retention/hold expiry, reviewed abuse outcomes, grant revocation, chained redacted audit | runtime governance regressions |
| Dialog and picker accessibility | focus traps, return focus, consequence copy, real picker integration | React accessibility tests and Playwright interaction proof |
| Reviewed visual integrity | contrast correction and exact-source visual sidecar | responsive/theme/zoom/detail/picker matrix plus drift rejection |
| Dependency integrity | patched React Router and transitive override | production build, frontend suite, and zero-finding npm audit |
| Corrective closeout | tasks B039-B040 | exact-head complete gate, repeated critical suites, hosted checks, fresh independent review |
