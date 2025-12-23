#!/usr/bin/env python3
"""Legacy entrypoint (thin trampoline).

Canonical implementation lives in:
  digital_ocean/scripts/python/orchestrate_deploy.py

This remains to preserve historical docs and commands like:
  python digital_ocean/orchestrate_deploy.py
"""

from __future__ import annotations

import runpy
from pathlib import Path


def main() -> None:
    target = Path(__file__).resolve().parent / "scripts" / "python" / "orchestrate_deploy.py"
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    main()

