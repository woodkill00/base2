#!/usr/bin/env python3
"""Validate the integrity of the Feature 093 Spec-Kit package."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys


TASK_LINE = re.compile(r"^- \[(?P<done>[ x])\] (?P<id>T\d{3})\b(?P<body>.*)$", re.MULTILINE)
TASK_REF = re.compile(r"T\d{3}")
REQUIREMENT = re.compile(r"FR-\d{3}")
PLACEHOLDERS = ("NEEDS CLARIFICATION", "ACTION REQUIRED", "TXXX", "[FEATURE", "[###")


def _dependencies(body: str) -> list[str]:
    match = re.search(r"\| Depends: (?P<deps>.*?) \| Validate:", body)
    if not match or match.group("deps").strip().lower() == "none":
        return []
    return TASK_REF.findall(match.group("deps"))


def validate_task_graph(text: str) -> list[str]:
    findings: list[str] = []
    matches = list(TASK_LINE.finditer(text))
    ids = [match.group("id") for match in matches]
    defined = set(ids)

    for task_id in sorted(defined):
        if ids.count(task_id) > 1:
            findings.append(f"duplicate task ID {task_id}")

    graph: dict[str, list[str]] = {}
    for match in matches:
        task_id = match.group("id")
        body = match.group("body")
        dependencies = _dependencies(body)
        graph[task_id] = dependencies
        for dependency in dependencies:
            if dependency not in defined:
                findings.append(f"{task_id} has unknown dependency {dependency}")
        validation = body.split("| Validate:", 1)[1].strip() if "| Validate:" in body else ""
        if not validation:
            findings.append(f"{task_id} has no validation")
        if match.group("done") == "x" and validation.lower() in {"", "none", "n/a"}:
            findings.append(f"checked task {task_id} has no evidence-producing validation")
        lower = body.lower()
        live_provider_action = "digitalocean" in lower or "digital ocean" in lower
        if live_provider_action and "deploy" in lower and "providerless" not in lower and "separate" not in lower:
            findings.append(f"{task_id} has a live provider action without a separate approval boundary")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str, path: list[str]) -> None:
        if task_id in visited or task_id not in graph:
            return
        if task_id in visiting:
            start = path.index(task_id) if task_id in path else 0
            findings.append("dependency cycle: " + " -> ".join(path[start:] + [task_id]))
            return
        visiting.add(task_id)
        for dependency in graph[task_id]:
            visit(dependency, path + [task_id])
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in sorted(graph):
        visit(task_id, [])

    return sorted(set(findings))


def validate_traceability(spec_text: str, trace_text: str) -> list[str]:
    required = set(REQUIREMENT.findall(spec_text))
    traced = set(re.findall(r"^\| (FR-\d{3}) \|", trace_text, re.MULTILINE))
    findings = [f"requirement {item} is not traced" for item in sorted(required - traced)]
    findings.extend(f"traceability references unknown {item}" for item in sorted(traced - required))
    return findings


def validate_placeholders(docs: dict[str, str]) -> list[str]:
    findings: list[str] = []
    for name, text in docs.items():
        for placeholder in PLACEHOLDERS:
            if placeholder in text:
                findings.append(f"{name} contains unresolved placeholder: {placeholder}")
        if "Pending." in text and "Result: Resolved" not in text:
            findings.append(f"{name} contains unresolved placeholder: Pending.")
    return findings


def validate_feature(feature_dir: Path) -> list[str]:
    findings: list[str] = []
    required_docs = ("spec.md", "plan.md", "research.md", "data-model.md", "quickstart.md", "tasks.md", "traceability.md", "analysis.md")
    docs: dict[str, str] = {}
    for name in required_docs:
        path = feature_dir / name
        if not path.is_file():
            findings.append(f"missing required document {name}")
        else:
            docs[name] = path.read_text(encoding="utf-8")

    if "tasks.md" in docs:
        findings.extend(validate_task_graph(docs["tasks.md"]))
    if "spec.md" in docs and "traceability.md" in docs:
        findings.extend(validate_traceability(docs["spec.md"], docs["traceability.md"]))
    findings.extend(validate_placeholders(docs))

    contracts = feature_dir / "contracts"
    for name in ("site-manifest.schema.json", "module-manifest.schema.json", "preview-lease.schema.json", "gate-result.schema.json"):
        path = contracts / name
        if not path.is_file():
            findings.append(f"missing contract {name}")
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            findings.append(f"invalid contract {name}: {exc}")
            continue
        if payload.get("additionalProperties") is not False:
            findings.append(f"contract {name} is not strict at its root")

    return sorted(set(findings))


def main(argv: list[str]) -> int:
    repo_root = Path(__file__).resolve().parents[2]
    feature_dir = Path(argv[1]).resolve() if len(argv) > 1 else repo_root / "specs" / "093-base2-foundation-hardening"
    findings = validate_feature(feature_dir)
    if findings:
        print(f"Feature 093 analysis: FAILED ({len(findings)} finding(s))")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print("Feature 093 analysis: PASS (0 findings)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
