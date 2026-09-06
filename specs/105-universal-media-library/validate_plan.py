#!/usr/bin/env python3
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    required = {"README.md", "spec.md", "plan.md", "tasks.md", "analysis.md", "traceability.md"}
    missing = sorted(name for name in required if not (ROOT / name).is_file())
    tasks = (ROOT / "tasks.md").read_text(encoding="utf-8")
    identifiers = [int(value) for value in re.findall(r"B(\d{3})", tasks)]
    if missing or identifiers != list(range(1, 25)):
        raise SystemExit(f"media_plan_invalid missing={missing} tasks={identifiers}")
    if tasks.count("- [ ]") != 10 or tasks.count("- [x]") != 14:
        raise SystemExit("media_plan_status_invalid")
    for marker in ("PostgreSQL", "browser matrix", "draft PR", "staging canary", "destroy"):
        if marker not in tasks:
            raise SystemExit(f"media_plan_boundary_missing:{marker}")
    print("media_plan_valid tasks=24 complete=14 pending=10")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
