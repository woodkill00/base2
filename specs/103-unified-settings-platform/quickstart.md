# Validation Quickstart

Run from the native WSL checkout through repository entrypoints:

The supported workstation runtime is Node 24.20.0 LTS. On WSL, expose at least two processors; the complete gate fails early with an actionable `.wslconfig` remedy if the host is constrained below that safe boundary.

```bash
cd /home/woodkill/code/base2
scripts/bash/test.sh
scripts/bash/complete-gate.sh
```

Focused validation includes Django migration checks, API contract/security tests, profile generation, React unit/accessibility tests, settings Playwright tests, authenticated visual matrices, secret scans, and the complete gate.

Separately admitted live acceptance uses `digital_ocean/orchestrate_deploy.py`, staging certificates, an approved cost ceiling, exact-main source, signed lease evidence, exact teardown, and empty provider inventory.
