#!/usr/bin/env python3
"""Fail-closed planning validator for Feature 104.

This script is intentionally standard-library only and credential-free. It validates
the Spec-Kit planning contract; it does not claim that pending implementation works.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REQUIRED_FILES = (
    "spec.md",
    "plan.md",
    "research.md",
    "data-model.md",
    "contracts/content-api.md",
    "quickstart.md",
    "tasks.md",
    "traceability.md",
    "analysis.md",
)
EXPECTED_REQUIREMENTS = tuple(f"FR-{number:03d}" for number in range(1, 63))
BASE_TASKS = tuple(f"T{number:03d}" for number in range(1, 151))


def fail(message: str) -> None:
    raise AssertionError(message)


def read(relative: str) -> str:
    path = ROOT / relative
    if not path.is_file():
        fail(f"missing required planning file: {relative}")
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        fail(f"empty required planning file: {relative}")
    return text


def validate_spec(spec: str) -> None:
    found = tuple(re.findall(r"^- \*\*(FR-\d{3})\*\*:", spec, flags=re.MULTILINE))
    if found != EXPECTED_REQUIREMENTS:
        fail(
            "functional requirements must be exactly sequential FR-001..FR-062; "
            f"found {len(found)} entries"
        )
    stories = re.findall(
        r"^### User Story \d+ - .+ \(Priority: P[123]\)$", spec, flags=re.MULTILINE
    )
    if len(stories) != 7:
        fail(f"expected 7 prioritized user stories, found {len(stories)}")
    criteria = re.findall(r"^- \*\*SC-\d{3}\*\*:", spec, flags=re.MULTILINE)
    if len(criteria) != 11:
        fail(f"expected 11 success criteria, found {len(criteria)}")
    required_boundaries = (
        "does not implement a free-form page builder",
        "does not send email",
        "does not implement payments",
        "does not deploy a live site",
        "cannot guarantee that unknown future defects are impossible",
    )
    for boundary in required_boundaries:
        if boundary not in spec:
            fail(f"missing explicit boundary: {boundary}")


def validate_tasks(tasks: str, analysis: str) -> int:
    task_rows = re.findall(r"^- \[([ x])\] (T\d{3})\b", tasks, flags=re.MULTILINE)
    found = tuple(task_id for _, task_id in task_rows)
    expected = tuple(f"T{number:03d}" for number in range(1, len(found) + 1))
    if len(found) < len(BASE_TASKS) or found != expected:
        fail(
            "tasks must contain contiguous T001..T150 base tasks followed only by "
            f"contiguous corrective tasks; found {len(found)} entries"
        )
    completed = {task_id for mark, task_id in task_rows if mark == "x"}
    phase_numbers = tuple(
        int(number) for number in re.findall(r"^## Phase (\d+)\b", tasks, flags=re.MULTILINE)
    )
    if phase_numbers != tuple(range(1, 11)):
        fail(f"phases must be sequential 1..10; found {phase_numbers}")
    if "Tests precede implementation" not in tasks:
        fail("task graph must state test-first ordering")
    if "Django precedes FastAPI, which precedes React" not in tasks:
        fail("task graph must state constitutional build order")
    for task_id in BASE_TASKS[18:140]:
        if task_id not in tasks:
            fail(f"missing implementation/verification task {task_id}")
    for guarded in ("T144", "T145", "T148", "T149"):
        if guarded not in tasks:
            fail(f"missing separately governed lifecycle task {guarded}")
        if guarded in completed:
            fail(f"separately governed lifecycle task may not be pre-completed: {guarded}")
    published = bool(
        re.search(
            r"^\*\*Current implementation status\*\*: " r"`IMPLEMENTATION_PUBLISHED_NOT_MERGED`$",
            analysis,
            flags=re.MULTILINE,
        )
    )
    if ("T142" in completed) != published:
        fail("T142 completion must exactly match the published-not-merged lifecycle status")
    return len(found)


def validate_traceability(traceability: str) -> None:
    rows: dict[str, list[str]] = {}
    for line in traceability.splitlines():
        match = re.match(r"^\|\s*(FR-\d{3})\s*\|(.+)\|\s*$", line)
        if not match:
            continue
        columns = [column.strip() for column in match.group(2).split("|")]
        rows[match.group(1)] = columns
    if tuple(rows) != EXPECTED_REQUIREMENTS:
        fail(
            "traceability rows must be exactly sequential FR-001..FR-062; "
            f"found {len(rows)} rows"
        )
    valid_task_ids = set(BASE_TASKS)
    for requirement, columns in rows.items():
        if len(columns) != 3:
            fail(f"{requirement} must have implementation, automated test, and evidence columns")
        for label, column in zip(("implementation", "test", "evidence"), columns, strict=True):
            references = re.findall(r"T\d{3}", column)
            if not references:
                fail(f"{requirement} has no {label} task reference")
            unknown = sorted(set(references) - valid_task_ids)
            if unknown:
                fail(f"{requirement} references unknown {label} tasks: {unknown}")


def validate_cross_document_contract(documents: dict[str, str]) -> None:
    combined = "\n".join(documents.values())
    required_concepts = (
        "tenant",
        "site",
        "optimistic",
        "idempotency",
        "row-level security",
        "quarantine",
        "malware",
        "CSV formula",
        "structured rich text",
        "saved view",
        "isolated restore",
        "staging-only certificates",
        "exact teardown",
        "visual review sidecar",
        "/api/items",
        "existing `sitecontent.ContentRecord`",
        "does not introduce a second competing tenant/site identity",
        "/api/content/v1",
        "Django",
        "FastAPI",
        "React",
    )
    for concept in required_concepts:
        if concept.casefold() not in combined.casefold():
            fail(f"missing cross-document concept: {concept}")
    forbidden_markers = (
        "[TBD]",
        "TODO:",
        "FIXME:",
        "UNRESOLVED_FINDING",
        "NEEDS CLARIFICATION",
    )
    for marker in forbidden_markers:
        if marker.casefold() in combined.casefold():
            fail(f"unresolved planning marker present: {marker}")
    if "NO_UNRESOLVED_PLANNING_FINDINGS" not in documents["analysis.md"]:
        fail("analysis has no explicit planning closure result")
    present_states = re.findall(
        r"^\*\*Current implementation status\*\*: "
        r"`(IMPLEMENTATION_ACTIVE_NOT_PUBLISHED|IMPLEMENTATION_PUBLISHED_NOT_MERGED)`$",
        documents["analysis.md"],
        flags=re.MULTILINE,
    )
    if len(present_states) != 1:
        fail("analysis must state exactly one current implementation/publication status")
    if present_states[0] == "IMPLEMENTATION_PUBLISHED_NOT_MERGED" and (
        "NO_UNRESOLVED_IMPLEMENTATION_FINDINGS" not in documents["analysis.md"]
    ):
        fail("published lifecycle status requires evidence-backed implementation closure")


def main() -> int:
    documents = {relative: read(relative) for relative in REQUIRED_FILES}
    validate_spec(documents["spec.md"])
    task_count = validate_tasks(documents["tasks.md"], documents["analysis.md"])
    validate_traceability(documents["traceability.md"])
    validate_cross_document_contract(documents)
    print(
        "Feature 104 planning validation: PASS "
        f"(62 requirements, {task_count} ordered base/corrective tasks, complete "
        "task/test/evidence traceability, "
        "zero unresolved planning findings)"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"Feature 104 planning validation: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
