#!/usr/bin/env python3
"""Validate the required Base2 threat-model control ledger."""

from __future__ import annotations

from pathlib import Path

BOUNDARIES = {"public", "tenant", "admin", "module", "factory", "provider"}
HEADERS = [
    "Boundary",
    "Principal and assets",
    "STRIDE/privacy/abuse cases",
    "Prevention",
    "Detection",
    "Response",
    "Owner",
    "Test tasks",
]


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def validate(text: str) -> list[str]:
    findings: list[str] = []
    lines = text.splitlines()
    header_index = next((i for i, line in enumerate(lines) if _cells(line) == HEADERS), None)
    if header_index is None:
        return ["missing threat-model control ledger header"]

    rows: dict[str, list[str]] = {}
    for line in lines[header_index + 2 :]:
        if not line.startswith("|"):
            break
        cells = _cells(line)
        if len(cells) != len(HEADERS):
            findings.append("malformed threat-model ledger row")
            continue
        boundary = cells[0]
        if boundary in rows:
            findings.append(f"duplicate threat boundary {boundary}")
        rows[boundary] = cells

    unknown = set(rows) - BOUNDARIES
    missing = BOUNDARIES - set(rows)
    for boundary in sorted(unknown):
        findings.append(f"unknown threat boundary {boundary}")
    for boundary in sorted(missing):
        findings.append(f"missing threat boundary {boundary}")

    for boundary, cells in rows.items():
        for header, value in zip(HEADERS[1:], cells[1:], strict=True):
            if len(value) < 4:
                findings.append(f"{boundary} lacks {header.lower()}")
        if not any(prefix in cells[-1] for prefix in ("T0", "T1")):
            findings.append(f"{boundary} lacks executable test task")
        if ";" not in cells[2]:
            findings.append(f"{boundary} lacks multiple misuse cases")

    required_phrases = (
        "data—not instructions",
        "fails closed",
        "zero unapproved mutation",
        "separately authorized action",
    )
    for phrase in required_phrases:
        if phrase not in text:
            findings.append(f"missing threat-model policy: {phrase}")
    return sorted(set(findings))


def main() -> int:
    path = Path(__file__).resolve().parents[2] / "docs" / "THREAT_MODEL.md"
    findings = validate(path.read_text(encoding="utf-8"))
    if findings:
        print(f"Threat model: FAILED ({len(findings)} finding(s))")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print(f"Threat model: PASS ({len(BOUNDARIES)} trust boundaries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
