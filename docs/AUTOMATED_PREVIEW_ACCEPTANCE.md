# Automated preview acceptance

Routine unchanged-design review is automated. Human approval is for intentional
design/baseline changes, not a substitute for missing tests. No automatic baseline
updates are allowed by the live acceptance configuration.

## Coverage map

| Concern                                                      | Automated evidence                                                                                       | Honest limit                                                                                   |
| ------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Approved home, left/right menus, palette                     | 8 exact existing pixel references across mobile/desktop; same assertion helper locally and live          | API responses mocked only in these design cases                                                |
| Public and authenticated page layouts                        | 69 local Volcano cases; live public route and authenticated settings matrix                              | Other page captures are layout/interaction evidence, not individually approved pixel baselines |
| Responsive menus, scroll, footer, palette                    | Live desktop/tablet/mobile geometry, first/last content reachability, focus/escape and screenshots       | Subjective future redesign requires approval                                                   |
| Signup and persistent Woodkill login                         | Separate ephemeral signup/settings flow and reusable-owner login/logout                                  | Persistent owner credentials required; never reset password or edit owner preferences          |
| Admin, pgAdmin, Swagger, Traefik, Flower                     | Anonymous denial, owner-edge readiness, second-layer admin/pgAdmin login                                 | Requires approved isolated preview and private inputs                                          |
| Content/API, settings, media                                 | Real HTTP failure checks, settings mutations on synthetic account, media admission and worker completion | Full media acceptance cannot pass on a restricted preview                                      |
| Light preference, RTL, zoom, failure/loading/disabled states | Existing local layout/Volcano/experience/settings suites                                                 | Synthetic tests remain distinguished from live backend checks                                  |
| Cleanup, expiry, DNS identity, restart and rollback          | Feature 111 lease/journal/scheduler tests and explicit live lifecycle receipt                            | Browser success NEVER proves cleanup; offline WSL cannot act                                   |
| Gate completeness                                            | Fixed 11-case inventory, no skip/retry/duplicate/filtered passes, clean exact source, private output     | Not a cryptographic attestation against a malicious operator                                   |

## Supported execution

Use the existing approved preview launch path; never provision just to run the
provider-free checks. Local release entrypoint remains `scripts/bash/complete-gate.sh`
(PowerShell equivalent under `scripts/powershell`). CI runs the acceptance policy
tests and approved Volcano suite on PRs and main.

For an already authorized live preview, run the existing
`npm --prefix react-app run test:live-full-preview` entrypoint without reporter or
baseline overrides. Supply all existing private operator/application inputs plus:

- `BASE2_OWNER_EMAIL`, `BASE2_OWNER_PASSWORD`: reusable owner, sourced privately
  from the existing Vaultwarden item; never paste into commands or commit them.
- `BASE2_LIVE_SOURCE_COMMIT`: exact deployed 40-character Git revision, also HEAD
  of the clean local checkout. Obtain from the actual deployment receipt, not a guess.
- `BASE2_LIVE_RUN_ID`: exact existing lease ID (`base2-full-YYYYMMDD-HHMMSS`).
- `BASE2_LIVE_EVIDENCE_DIR`: a new empty absolute owner-only directory, no symlink
  parents. Existing evidence is never overwritten.
- Explicit `BASE2_LIVE_DOMAIN` and `BASE2_LIVE_ADDRESS` remain required; there is
  no automatic target selection.

The machine-local notebook wrapper predates these additional inputs. Export them
through its private credential integration before using it, or use the supported
repository npm entrypoint. Missing inputs fail BEFORE browser launch. No notebook
sync or machine-local helper modification is part of this feature.

`acceptance.json` is a sanitized private browser acceptance summary. Missing,
skipped, failed, retried or filtered required cases cannot pass. `--list` intentionally
does not grant acceptance. Preserve `playwright-result.json` privately for diagnosis.
Never publish live screenshots/logs containing account information.

## Lifecycle acceptance is separate

Before testing, verify the supported launch admitted its persistent expiry timer
and exact lease; after the approved teardown, verify the existing integrity-bound
destroyed receipt and bounded inventory. Do not manually manufacture these records.
If the provider result is ambiguous, stop for reconciliation. This implementation
does not grant cloud credentials, spending, destruction or lease-extension authority.

Local acceptance can pass while live acceptance is blocked awaiting an approved
preview. A human walkthrough is optional for unchanged visuals; it cannot override
failed automated acceptance. No suite proves absence of unknown defects.
