#!/usr/bin/env python3
"""Evaluate machine-readable coverage reports against the fixed Base2 policy."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys

from coverage_policy import summarize_python_coverage, validate_policy


def ratio(covered: int, total: int) -> float:
    return round(100.0 * covered / total, 2) if total else 100.0


def summarize_lcov(text: str) -> dict[str, float]:
    totals = {"lines": [0, 0], "branches": [0, 0], "functions": [0, 0]}
    keys = {"LF": ("lines", 1), "LH": ("lines", 0), "BRF": ("branches", 1), "BRH": ("branches", 0), "FNF": ("functions", 1), "FNH": ("functions", 0)}
    for line in text.splitlines():
        key, separator, value = line.partition(":")
        if separator and key in keys:
            metric, index = keys[key]
            totals[metric][index] += int(value)
    return {metric: ratio(values[0], values[1]) for metric, values in totals.items()}


def summarize_istanbul(entries: dict) -> dict[str, float]:
    statements = functions = branches = 0
    hit_statements = hit_functions = hit_branches = 0
    line_hits: dict[tuple[str, int], int] = {}
    for filename, item in entries.items():
        for statement_id, count in item.get("s", {}).items():
            statements += 1
            hit_statements += count > 0
            line = item["statementMap"][statement_id]["start"]["line"]
            line_hits[(filename, line)] = line_hits.get((filename, line), 0) + count
        for count in item.get("f", {}).values():
            functions += 1
            hit_functions += count > 0
        for counts in item.get("b", {}).values():
            branches += len(counts)
            hit_branches += sum(count > 0 for count in counts)
    return {
        "lines": ratio(sum(value > 0 for value in line_hits.values()), len(line_hits)),
        "statements": ratio(hit_statements, statements),
        "functions": ratio(hit_functions, functions),
        "branches": ratio(hit_branches, branches),
    }


def normalized_path(filename: str, repo_root: Path) -> str:
    path = Path(filename)
    if path.is_absolute():
        try:
            path = path.relative_to(repo_root)
        except ValueError:
            return ""
    return path.as_posix()


def lcov_line_map(text: str, repo_root: Path) -> dict[str, dict[int, bool]]:
    result: dict[str, dict[int, bool]] = {}
    current = ""
    for line in text.splitlines():
        if line.startswith("SF:"):
            current = normalized_path(line[3:], repo_root)
            result.setdefault(current, {})
        elif current and line.startswith("DA:"):
            number, hits, *_ = line[3:].split(",")
            result[current][int(number)] = int(hits) > 0
    return result


def istanbul_line_map(entries: dict, repo_root: Path) -> dict[str, dict[int, bool]]:
    result: dict[str, dict[int, bool]] = {}
    for filename, item in entries.items():
        name = normalized_path(filename, repo_root)
        lines = result.setdefault(name, {})
        for statement_id, count in item.get("s", {}).items():
            line = item["statementMap"][statement_id]["start"]["line"]
            lines[line] = lines.get(line, False) or count > 0
    return result


def python_line_map(report: dict, repo_root: Path) -> dict[str, dict[int, bool]]:
    result = {}
    for filename, item in report.get("files", {}).items():
        name = normalized_path(filename, repo_root)
        executed = set(item.get("executed_lines", []))
        missing = set(item.get("missing_lines", []))
        result[name] = {line: line in executed for line in executed | missing}
    return result


def parse_changed_lines(diff: str) -> dict[str, set[int]]:
    changed: dict[str, set[int]] = {}
    current = ""
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
            changed.setdefault(current, set())
        elif current and line.startswith("@@"):
            match = re.search(r"\+(\d+)(?:,(\d+))?", line)
            if match:
                start = int(match.group(1))
                count = int(match.group(2) or "1")
                changed[current].update(range(start, start + count))
    return changed


def changed_line_result(changed: dict[str, set[int]], maps: list[dict[str, dict[int, bool]]], floor: float) -> dict:
    combined: dict[str, dict[int, bool]] = {}
    for coverage_map in maps:
        for filename, lines in coverage_map.items():
            combined.setdefault(filename, {}).update(lines)
    measured = []
    for filename, lines in changed.items():
        instrumented = combined.get(filename, {})
        measured.extend(instrumented[line] for line in lines if line in instrumented)
    actual = ratio(sum(measured), len(measured)) if measured else None
    status = "not_applicable" if not measured else ("passed" if actual >= floor else "failed")
    return {"status": status, "covered": sum(measured), "executable": len(measured), "percent": actual, "floor": floor}


def evaluate(policy: dict, reports: dict[str, dict[str, float]], changed_lines: dict | None = None) -> dict:
    findings = validate_policy(policy)
    results = []
    for surface in policy["surfaces"]:
        actual = reports.get(surface["id"])
        failures = []
        if actual is None:
            failures.append("report missing")
            actual = {}
        for metric, floor in surface["floors"].items():
            if metric not in actual:
                failures.append(f"{metric} unavailable")
            elif actual[metric] < floor:
                failures.append(f"{metric} {actual[metric]} < {floor}")
        results.append({"id": surface["id"], "status": "passed" if not failures else "failed", "actual": actual, "floors": surface["floors"], "findings": failures})
        findings.extend(f"{surface['id']}: {failure}" for failure in failures)
    if changed_lines and changed_lines["status"] == "failed":
        findings.append(f"changed lines {changed_lines['percent']} < {changed_lines['floor']}")
    return {"schemaVersion": 1, "status": "passed" if not findings else "failed", "changedLines": changed_lines, "surfaces": results, "findings": sorted(set(findings))}


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    artifact_root = repo_root / ".artifacts" / "coverage"
    policy = json.loads((repo_root / "scripts/config/coverage-policy.json").read_text(encoding="utf-8"))
    frontend_summary = json.loads((repo_root / "react-app/coverage/coverage-summary.json").read_text(encoding="utf-8"))["total"]
    frontend = {metric: float(frontend_summary[metric]["pct"]) for metric in ("lines", "branches", "functions", "statements")}
    istanbul = json.loads((repo_root / "react-app/coverage/coverage-final.json").read_text(encoding="utf-8"))
    api_report = json.loads((artifact_root / "api.json").read_text(encoding="utf-8"))
    django_report = json.loads((artifact_root / "django.json").read_text(encoding="utf-8"))
    digitalocean_report = json.loads((artifact_root / "digitalocean.json").read_text(encoding="utf-8"))
    root_lcov = (artifact_root / "root.lcov").read_text(encoding="utf-8")
    critical = {name: item for name, item in istanbul.items() if any(scope in name.replace("\\", "/") for scope in ("/components/glass/", "/services/glass/", "/services/theme/"))}
    reports = {
        "root-env-runtime": summarize_lcov(root_lcov),
        "frontend-runtime": frontend,
        "frontend-critical-glass": summarize_istanbul(critical),
        "api-runtime": summarize_python_coverage(api_report, ["/tests/"]),
        "django-runtime": summarize_python_coverage(django_report, ["/tests/"]),
        "digitalocean-supported-runtime": summarize_python_coverage(digitalocean_report, ["/tests/"]),
    }
    target = "main"
    merge_base = subprocess.run(["git", "merge-base", target, "HEAD"], cwd=repo_root, text=True, capture_output=True, check=True).stdout.strip()
    diff = subprocess.run(["git", "diff", "--unified=0", f"{merge_base}...HEAD", "--", "scripts", "react-app/src", "api", "django", "digital_ocean/scripts/python"], cwd=repo_root, text=True, capture_output=True, check=True).stdout
    changed = changed_line_result(
        parse_changed_lines(diff),
        [lcov_line_map(root_lcov, repo_root), istanbul_line_map(istanbul, repo_root), python_line_map(api_report, repo_root), python_line_map(django_report, repo_root), python_line_map(digitalocean_report, repo_root)],
        policy["changedLines"]["minimumPercent"],
    )
    result = evaluate(policy, reports, changed)
    artifact_root.mkdir(parents=True, exist_ok=True)
    (artifact_root / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Coverage gate: {result['status'].upper()}")
    for item in result["surfaces"]:
        print(f"- {item['id']}: {item['status']} {item['actual']}")
    print(f"- changed-lines: {result['changedLines']}")
    for finding in result["findings"]:
        print(f"  {finding}")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
