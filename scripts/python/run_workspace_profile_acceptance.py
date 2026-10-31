#!/usr/bin/env python3
"""Run one fixed disposable profile using a supported native isolated runner."""
from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROFILES = ('base2-obsidian', 'journey-reference')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True, choices=PROFILES)
    parser.add_argument('--shell', required=True, choices=('bash', 'pwsh'))
    args = parser.parse_args(argv)
    commands = {
        'bash': ['bash', str(ROOT / 'scripts/bash/e2e-isolated.sh')],
        'pwsh': ['pwsh', '-NoProfile', '-File', str(ROOT / 'scripts/powershell/e2e-isolated.ps1')],
    }
    environment = {**os.environ, 'E2E_SITE_PROFILE': args.profile}
    result = subprocess.run(commands[args.shell], cwd=ROOT, env=environment, check=False)
    return result.returncode if result.returncode >= 0 else 128 - result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
