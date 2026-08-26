# Research: Base2 Full-Stack Obsidian Preview

## Live findings that define the feature

- The 2026-08-26 preview deployed exact `main` commit `7e06964b3fea93a951f59a87eccb50a18d1881dc`; all 12 containers were healthy.
- Root DNS pointed to `104.131.184.135`, while admin, Traefik, Swagger, and pgAdmin still pointed to legacy `138.197.38.153`.
- `dynamic-canary.yml` intentionally routed only the root host frontend and `/api/*`; `live-canary-remote.sh` explicitly rejected full-preview hostnames.
- The live renderer selected `ember-studio`, forced production docs off, supplied loopback owner admission, and disabled operator credentials.
- `/api/health` was green but `/api` had no route and returned 404.
- Obsidian composition classes existed, but the selected manifest identified Ember Studio and the `volcanic` theme. The visual gate was local/hermetic and did not bind a live screenshot to the approved reference.
- Manual pre-expiry service start returned `ok: true, status: not_expired` for compute, which allowed an unconditional DNS post-step to delete root DNS while the Droplet remained. Exact forced teardown subsequently removed the Droplet; final matching provider inventory was zero.

## Decisions

1. Preserve minimal canary rather than weakening it.
2. Add a canonical `base2-obsidian` profile instead of treating a fixture tenant as Base2.
3. Generate the frontend profile registry to eliminate manual-import drift.
4. Treat brand theme and user light/dark preference as separate attributes and apply both before first paint.
5. Use exact public host CIDRs only. A DigitalOcean edge cannot use a router's RFC1918 address to identify the owner.
6. Require both edge auth and allowlist for every operator surface; retain application auth where supported.
7. Represent DNS records inside the lease rather than as an unrelated cleanup post-step.
8. Make an unexpired teardown refusal non-zero/non-success for mutation workflows.
9. Keep all certificates staging-only.
10. Require a live visual and interaction probe before reporting `live_verified`.

## Rejected alternatives

- Point all subdomains to the Droplet and use the existing full config unchanged: rejected because current allowlist and credential values are unsafe/invalid for live use.
- Use wildcard DNS: rejected because it broadens ownership and cleanup scope.
- Expose dashboards without allowlists to simplify testing: rejected because basic authentication alone is insufficient for these operator surfaces.
- Merge the stale Obsidian branch: rejected because it diverges heavily from current architecture; it is a visual reference only.
- Issue production certificates: outside this feature and constitutionally forbidden.
- Call container health sufficient: rejected because the observed failure was entirely outside the containers.
