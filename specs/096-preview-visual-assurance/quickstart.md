# Quickstart

Run only from the native WSL checkout:

```bash
cd /home/woodkill/code/base2
./digital_ocean/scripts/bash/base2-preview.sh preflight --repo "$PWD"
./digital_ocean/scripts/bash/base2-preview.sh status \
  --state-root "$HOME/.local/state/base2-full-preview"
```

Build a visual evidence index without network or credentials:

```bash
./digital_ocean/scripts/bash/base2-preview.sh evidence \
  --evidence-root "$HOME/.local/state/base2-full-preview/RUN/browser-exact" \
  --commit "$(git rev-parse HEAD)" \
  --profile-digest "$(sha256sum site_profiles/base2-obsidian.json | cut -d' ' -f1)" \
  --run-id RUN
```

Mutation remains a separately authorized exact-lease operation. Never paste secrets into the command line.

Plan old visual-evidence retention without deleting anything:

```bash
./digital_ocean/scripts/bash/base2-preview.sh retention \
  --state-root "$HOME/.local/state/base2-full-preview"
```

`--apply` deletes only bounded, old, unapproved screenshot/index artifacts from
already-destroyed runs. It never deletes lease/provider state or approved visual evidence.
