# Handoff

```bash
cd /home/woodkill/code/base2
git switch 108-obsidian-owner-experience
python3 specs/108-obsidian-owner-experience/validate_plan.py
scripts/bash/assure.sh plan --tier auto
```

Follow task dependencies; record failing regression first. Run affected suites
through existing assurance. Final release: scripts/bash/assure.sh run --tier release.
Auth/RLS/deployment must not be downgraded to docs-only validation.

Before live owner activation configure the approved private credential reference.
Present screenshots for human review, keep staging certificates and lease expiry.
Explicitly distinguish recreated login from retained/restored user data.
