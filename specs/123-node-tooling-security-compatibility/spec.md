# 123 — Node tooling security compatibility

## Outcome and scope

The frontend development toolchain installs genuinely fixed dependencies and passes
the existing moderate-severity dependency gate without weakening useful tooling.
The owner authorized this separate compatibility migration on 2026-10-31 after
ordinary compatible updates proved insufficient. Site design, production settings,
media runtime work, deployment and merge are outside this change.

## Acceptance

- A clean supported frontend installation and the unchanged all-dependency
  `npm audit --audit-level=moderate` pass; production-only audit passes too.
- Lint rules, file selection, lint caching, OpenAPI type generation, TypeScript,
  production build and Storybook retain their intended behavior.
- Fixed packages keep their real upstream names, versions, registry origins and
  integrity records. No advisory suppression, scanner omission, fake versions,
  external fork publication or blanket incompatible override is permitted.
- Existing pngjs/comparator and redirect-security repairs are preserved. No UI
  source, screenshot baseline or application behavior changes are required.
- Compatibility adaptations receive real-consumer positive/negative tests and
  independent review. Install-time drift fails rather than silently skipping work.
- Local evidence is not a substitute for exact-source PR CI or the full release gate.
