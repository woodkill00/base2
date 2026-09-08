#!/usr/bin/env python3
"""Validate the Feature 106 planning and independent-review repair contract."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REQUIRED_FILES = {
    "README.md",
    "spec.md",
    "plan.md",
    "tasks.md",
    "analysis.md",
    "local-closeout-review.md",
    "traceability.md",
    "validate_plan.py",
}
REQUIRED_AUTHORITY_TERMS = (
    "publication",
    "merge",
    "deployment",
    "provider",
    "DNS",
    "production certificate",
    "destructive",
    "separately approved",
)


def ids(pattern: str, text: str) -> list[int]:
    return [int(value) for value in re.findall(pattern, text)]


def main() -> int:
    missing = sorted(name for name in REQUIRED_FILES if not (ROOT / name).is_file())
    if missing:
        raise SystemExit(f"production_readiness_plan_missing:{','.join(missing)}")

    spec = (ROOT / "spec.md").read_text(encoding="utf-8")
    plan = (ROOT / "plan.md").read_text(encoding="utf-8")
    tasks = (ROOT / "tasks.md").read_text(encoding="utf-8")
    analysis = (ROOT / "analysis.md").read_text(encoding="utf-8")
    traceability = (ROOT / "traceability.md").read_text(encoding="utf-8")
    local_review = (ROOT / "local-closeout-review.md").read_text(encoding="utf-8")
    activation_path = ROOT.parents[1] / "docs" / "PRODUCTION_ACTIVATION_RUNBOOK.md"
    if not activation_path.is_file():
        raise SystemExit("production_readiness_activation_runbook_missing")
    activation = activation_path.read_text(encoding="utf-8")

    requirement_ids = ids(r"\*\*FR-(\d{3})\*\*", spec)
    if requirement_ids != list(range(1, 79)):
        raise SystemExit(f"production_readiness_requirements_invalid:{requirement_ids}")

    task_ids = [
        int(value)
        for value in re.findall(r"^- \[[ x]\] B(\d{3})\b", tasks, re.MULTILINE)
    ]
    if task_ids != list(range(1, 219)):
        raise SystemExit(f"production_readiness_tasks_invalid:{task_ids}")

    checked = len(re.findall(r"^- \[x\] B\d{3}\b", tasks, re.MULTILINE))
    pending = len(re.findall(r"^- \[ \] B\d{3}\b", tasks, re.MULTILINE))
    if checked + pending != 218:
        raise SystemExit(
            f"production_readiness_status_invalid:checked={checked}:pending={pending}"
        )
    statuses = re.findall(r"^- \[([ x])\] B\d{3}\b", tasks, re.MULTILINE)
    if statuses != ["x"] * checked + [" "] * pending:
        raise SystemExit("production_readiness_status_not_contiguous")

    expected_requirements = set(range(1, 79))
    task_requirements = set(ids(r"FR-(\d{3})", tasks))
    trace_requirements = set(ids(r"FR-(\d{3})", traceability))
    missing_task_trace = sorted(expected_requirements - task_requirements)
    missing_table_trace = sorted(expected_requirements - trace_requirements)
    if missing_task_trace or missing_table_trace:
        raise SystemExit(
            "production_readiness_traceability_invalid:"
            f"tasks={missing_task_trace}:table={missing_table_trace}"
        )

    combined = "\n".join((spec, plan, tasks, analysis, traceability))
    absent_terms = [term for term in REQUIRED_AUTHORITY_TERMS if term not in combined]
    if absent_terms:
        raise SystemExit(
            f"production_readiness_authority_missing:{','.join(absent_terms)}"
        )

    required_analysis_markers = (
        "Cycle 1",
        "Cycle 2",
        "Cycle 3",
        "Cycle 4",
        "Cycle 5",
        "Cycle 6",
        "zero unresolved planning gaps",
        "unknown defects",
    )
    absent_markers = [marker for marker in required_analysis_markers if marker not in analysis]
    if absent_markers:
        raise SystemExit(
            f"production_readiness_analysis_missing:{','.join(absent_markers)}"
        )

    required_task_phrases = (
        "native operations",
        "forced-RLS",
        "staging certificates",
        "dead-letter",
        "object storage",
        "visual builder",
        "automatic ephemeral",
        "independent code, security, UX/accessibility, data, and operations reviews",
        "empty provider inventory",
    )
    tasks_lower = tasks.lower()
    absent_phrases = [
        phrase for phrase in required_task_phrases if phrase.lower() not in tasks_lower
    ]
    if absent_phrases:
        raise SystemExit(
            f"production_readiness_task_boundary_missing:{','.join(absent_phrases)}"
        )

    for label, text, markers in (
        (
            "local_review",
            local_review,
            (
                "## Candidate",
                "## Exact-source local evidence",
                "## Security and privacy review",
                "## UX and accessibility review",
                "## Data and operations review",
                "## Pending independent and external evidence",
            ),
        ),
        (
            "activation_runbook",
            activation,
            (
                "## Status and authority",
                "## Recovery roles",
                "## Required inputs",
                "## Preflight",
                "## Traffic sequence",
                "## Halt and rollback",
                "## Completion and teardown",
                "## Residual risk",
            ),
        ),
    ):
        missing_markers = [marker for marker in markers if marker not in text]
        if missing_markers:
            raise SystemExit(
                f"production_readiness_{label}_missing:{','.join(missing_markers)}"
            )

    print(
        "production_readiness_plan_valid "
        f"requirements={len(requirement_ids)} tasks={len(task_ids)} "
        f"complete={checked} pending={pending}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
