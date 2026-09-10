#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    required = {
        "spec.md", "plan.md", "research.md", "data-model.md", "quickstart.md",
        "tasks.md", "analysis.md", "traceability.md", "contracts/cli.md",
    }
    missing = sorted(name for name in required if not (ROOT / name).is_file())
    if missing:
        raise SystemExit(f"missing={','.join(missing)}")
    spec = (ROOT / "spec.md").read_text(encoding="utf-8")
    tasks = (ROOT / "tasks.md").read_text(encoding="utf-8")
    requirement_ids = [int(value) for value in re.findall(r"\*\*FR-(\d{3})\*\*", spec)]
    task_ids = [int(value) for value in re.findall(r"^- \[[ x]\] T(\d{3})", tasks, re.M)]
    if requirement_ids != list(range(1, 36)):
        raise SystemExit("requirements_not_contiguous")
    if task_ids != list(range(1, 123)):
        raise SystemExit("tasks_not_contiguous")
    if "NEEDS CLARIFICATION" in spec:
        raise SystemExit("unresolved_clarification")
    if "run_complete_gate.py" not in (ROOT / "plan.md").read_text(encoding="utf-8"):
        raise SystemExit("release_authority_missing")
    print("efficient_assurance_plan_valid requirements=35 tasks=122")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
