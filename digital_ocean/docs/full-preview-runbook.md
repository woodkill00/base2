# Base2 full-preview runbook

This runbook creates one short-lived 2 GB DigitalOcean preview from an exact merged commit. It exposes only Traefik on ports 80/443, uses Let's Encrypt staging, and protects every operator surface with an exact public-host allowlist plus independent edge authentication.

## Vaultwarden records

Keep these owner-only records; never put their values in Git, command history, reports, or Discord:

- `base2/digitalocean.api-token`: login item, token in **Password**; read/write Droplet, Domain, and SSH-key scope only.
- `base2/full-preview.operator`: login item, username and generated password. The private resolver derives an htpasswd line; the raw password is used only by the outside-in/browser gate.
- `base2/full-preview.flower`: a different login item and password; the hash must differ from the operator hash.
- `base2/pgadmin`: pgAdmin application login; it remains behind edge auth.
- `base2/django-admin`: Django application login; it remains behind edge auth.

Resolved JSON, raw username/password files, SSH keys, generated htpasswd files, state, and evidence directories must be owner-only (`0600` files, `0700` directories). The resolver must write them outside the repository.

## Preflight and archive

From the native WSL checkout on merged `main`:

```bash
test -z "$(git status --porcelain)"
commit="$(git rev-parse HEAD)"
profile_digest="$(sha256sum site_profiles/base2-obsidian.json | cut -d" " -f1)"
install -d -m 0700 "$HOME/.local/state/base2-full-preview/input"
archive="$HOME/.local/state/base2-full-preview/input/base2-${commit}.tar"
git archive --format=tar --output="$archive" "$commit"
chmod 0600 "$archive"
./digital_ocean/scripts/bash/full-preview.sh policy --domain woodkilldev.com --owner-cidr "PUBLIC_IP/32" --ttl-minutes 60
```

Use the exact current public IPv4 as `/32` (or public IPv6 as `/128`). Private router addresses and broad networks fail closed. Confirm the readiness receipt says `letsencrypt-staging-only` and `ready_for_live_approval` before live mutation.

## Separately approved launch

After resolving the private inputs, invoke the portable module. Paths below are examples and must point to owner-only files:

```bash
run_id="base2-full-$(date -u +%Y%m%d-%H%M%S)"
.venv/bin/python -m digital_ocean.scripts.python.full_preview_live \
  --credential-file "$PRIVATE/do.json" --source-archive "$archive" \
  --ssh-private-key "$PRIVATE/id_ed25519" --ssh-key-id "$DO_SSH_KEY_ID" \
  --operator-auth-file "$PRIVATE/operator.htpasswd" --flower-auth-file "$PRIVATE/flower.htpasswd" \
  --probe-username-file "$PRIVATE/operator.username" --probe-password-file "$PRIVATE/operator.password" \
  --source-commit "$commit" --profile-digest "$profile_digest" \
  --domain woodkilldev.com --owner-cidr "PUBLIC_IP/32" --run-id "$run_id" \
  --state-root "$HOME/.local/state/base2-full-preview/$run_id" --ttl-minutes 60
```

The launch order is compute, fixed bootstrap, direct-address health, transactional creation of `@`, `admin`, `swagger`, `traefik`, `pgadmin`, and `flower`, outside-in checks, then an integrity-bound lease. A failure restores the prior exact DNS set and deletes the Droplet; incomplete cleanup reports reconciliation instead of success.

## Live browser gate

Load credentials through private environment injection, never as CLI arguments:

```bash
cd react-app
BASE2_LIVE_DOMAIN=woodkilldev.com \
BASE2_LIVE_USERNAME="$(<"$PRIVATE/operator.username")" \
BASE2_LIVE_PASSWORD="$(<"$PRIVATE/operator.password")" \
BASE2_LIVE_EVIDENCE_DIR="$HOME/.local/state/base2-full-preview/$run_id/browser" \
npm run test:live-full-preview
```

Review the full-page Obsidian screenshot plus the five operator screenshots. The gate also verifies the keyboard command palette, browser console, failed requests, anonymous denial, and authorized access.

## Expiry, teardown, and owner-IP refresh

The versioned service/timer templates in `digital_ocean/systemd/` call the same integrity-bound teardown operation every minute. Before expiry, it performs zero provider actions. At expiry it deletes compute first and then only the six exact DNS record IDs. An earlier teardown requires `--early-approved` on the same command.

An owner IP change uses `refresh_full_preview_allowlist.py`. Its approval digest binds the run ID and exact `/32` or `/128` list; the update is atomic, preserves unrelated private values, emits no secrets, and must be followed by an exact Traefik recreate and the outside-in/browser gates. Broad or unapproved CIDRs perform zero writes.

Completion requires `destroyed`, the exact ownership tag returning zero Droplets, every bound DNS ID absent, no failed browser check, and redacted evidence with `secretValuesEmitted: 0`.
