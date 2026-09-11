#!/usr/bin/env python3
"""Validate planning structure; does not certify implementation correctness."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def validate():
    names = ("spec.md", "plan.md", "tasks.md", "analysis.md", "research.md",
             "data-model.md", "quickstart.md", "traceability.md", "contracts/acceptance.md")
    docs = {name: (ROOT / name).read_text(encoding="utf-8") for name in names}
    requirements = re.findall(r"\*\*(FR-\d{3})\*\*", docs["spec.md"])
    assert requirements == [f"FR-{i:03}" for i in range(1, 17)], "requirement sequence"
    tasks = re.findall(r"^- \[([ x])\] (T\d{3}) \[([^\]]+)\] \(depends: ([^)]+)\) (.+)$",
                       docs["tasks.md"], re.M)
    assert [t[1] for t in tasks] == [f"T{i:03}" for i in range(1, 29)], "task sequence"
    seen = set()
    coverage = {r: set() for r in requirements}
    for status, tid, refs, deps, text in tasks:
        assert status == " ", "planning cannot certify implementation"
        for dep in deps.split():
            assert dep == "none" or dep in seen, f"{tid}: invalid predecessor {dep}"
        for ref in refs.split():
            assert ref in coverage, f"{tid}: unknown requirement {ref}"
            coverage[ref].add(tid)
        assert len(text) > 60, f"{tid}: missing actionable detail"
        seen.add(tid)
    for ref, tids in coverage.items():
        assert tids, f"{ref}: uncovered"
        row = re.search(r"^\| " + ref + r" \| (.+) \|$", docs["traceability.md"], re.M)
        assert row and set(row[1].split(", ")) == tids, f"{ref}: traceability mismatch"
    assert "run_complete_gate.py" in docs["plan.md"], "release authority missing"
    assert "Cycle 1" in docs["analysis.md"] and "Cycle 2" in docs["analysis.md"]
    assert all("NEEDS CLARIFICATION" not in d and "$ARGUMENTS" not in d for d in docs.values())
    print("plan_valid requirements=16 tasks=28 cycles=2 implementation=pending")

if __name__ == "__main__":
    validate()
