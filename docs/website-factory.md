# Base2 website factory

The factory accepts a strict, bounded JSON profile and exports source with `git archive` from one exact commit. It never copies the working tree, untracked files, `.git`, virtual environments, caches, logs, test artifacts, receipts, or dependency directories. Archive paths and types are checked before extraction, and interrupted generation removes its temporary output.

Each child receives a distinct ID, selected module inventory, exact base commit/tree and profile provenance, README, license, notice, vulnerability policy, CODEOWNERS, branch-protection guidance, dependency updates, CI inherited from the exact source, and Vaultwarden references only. The applicable child gate validates those controls without executing any profile-supplied command.

The upgrade advisor emits review-only compatibility evidence and never applies, pushes, merges, or deploys a change. Bash and PowerShell wrappers pass the same arguments to the Python generator. Generated preview deployment remains a separate provider-approved action.
