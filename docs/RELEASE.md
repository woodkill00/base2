# Release Process

## Overview

This document describes the lightweight release process for Base2.

## Steps

1. Ensure `main` is green in CI (backend, frontend, security)
2. Bump versions if needed (app or docs)
3. Tag the release: `git tag -a vX.Y.Z -m "Release vX.Y.Z" && git push --tags`
4. Create GitHub Release with changelog highlights
5. Run deploy gate:
   - `powershell -File digital_ocean/scripts/powershell/deploy.ps1 -UpdateOnly -AllTests -Timestamped`
6. Verify post-deploy report success

## Rollback

- Use the rollback hook in deploy logs if enabled
- Alternatively, revert and re-run the deploy gate

## Notes

- SBOM and security scans run in CI
- Coverage thresholds enforced (backend, frontend)
