#!/usr/bin/env python3
"""Run the fixed Base2 complete gate and emit integrity-bound evidence."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid


SECRET_KEY = re.compile(r"(?:TOKEN|PASSWORD|SECRET|PRIVATE|CREDENTIAL|API_KEY)", re.I)
INLINE_SECRET = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+")
TOOL_TOKENS = {
    "{python-api}": (".venv-api/bin/python", ".venv-api/Scripts/python.exe"),
    "{python-django}": (".venv-django/bin/python", ".venv-django/Scripts/python.exe"),
    "{python-orchestrator}": (".venv/bin/python", ".venv/Scripts/python.exe"),
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def validate_manifest(manifest: dict) -> None:
    if manifest.get("schemaVersion") != 1 or not isinstance(manifest.get("checks"), list):
        raise ValueError("unsupported complete-gate manifest")
    checks = manifest["checks"]
    ids = [item.get("id") for item in checks]
    if any(not isinstance(item, str) or not re.fullmatch(r"[a-z][a-z0-9-]+", item) for item in ids):
        raise ValueError("invalid check ID")
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate check ID")
    known = set(ids)
    graph = {}
    for item in checks:
        allowed = {"id", "command", "required", "timeoutSeconds", "dependsOn", "requiredTools"}
        if set(item) != allowed:
            raise ValueError(f"invalid fields for {item.get('id')}")
        if not isinstance(item["command"], list) or not item["command"] or not all(isinstance(value, str) and value for value in item["command"]):
            raise ValueError(f"invalid command for {item['id']}")
        for dependency in item["dependsOn"]:
            if dependency not in known:
                raise ValueError(f"unknown dependency {dependency}")
        graph[item["id"]] = item["dependsOn"]

    visiting = set()
    visited = set()

    def visit(check_id: str) -> None:
        if check_id in visited:
            return
        if check_id in visiting:
            raise ValueError("dependency cycle")
        visiting.add(check_id)
        for dependency in graph[check_id]:
            visit(dependency)
        visiting.remove(check_id)
        visited.add(check_id)

    for check_id in ids:
        visit(check_id)


def resolve_tool(tool: str, repo_root: Path) -> str:
    if tool in TOOL_TOKENS:
        candidates = TOOL_TOKENS[tool]
        selected = candidates[1] if os.name == "nt" else candidates[0]
        return str(repo_root / selected)
    return tool


def tool_available(tool: str, repo_root: Path) -> bool:
    tool = resolve_tool(tool, repo_root)
    if "/" in tool or "\\" in tool:
        candidate = Path(tool)
        if not candidate.is_absolute():
            candidate = repo_root / candidate
        return candidate.is_file() and os.access(candidate, os.X_OK)
    return shutil.which(tool) is not None


def redact(text: str, environment: dict[str, str]) -> str:
    output = INLINE_SECRET.sub(r"\1[REDACTED]", text)
    values = {
        str(value)
        for key, value in environment.items()
        if SECRET_KEY.search(key) and value is not None and len(str(value)) >= 4
    }
    for value in sorted(values, key=len, reverse=True):
        output = output.replace(value, "[REDACTED]")
    return output


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def run_gate(
    manifest: dict,
    repo_root: Path,
    evidence_dir: Path,
    *,
    source_commit: str,
    environment: dict[str, str] | None = None,
) -> dict:
    validate_manifest(manifest)
    repo_root = repo_root.resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    environment = dict(environment or os.environ)
    started = now()
    results = []
    states = {}

    for item in manifest["checks"]:
        check_id = item["id"]
        base = {
            "id": check_id,
            "required": item["required"],
            "exitCode": None,
            "artifact": None,
            "diagnostic": None,
        }
        blocked = [dependency for dependency in item["dependsOn"] if states.get(dependency) != "passed"]
        if blocked:
            result = {**base, "status": "not_run", "diagnostic": "blocked by: " + ", ".join(blocked)}
        else:
            missing = [tool for tool in item["requiredTools"] if not tool_available(tool, repo_root)]
            if missing:
                result = {**base, "status": "unavailable", "diagnostic": "missing tools: " + ", ".join(missing)}
            else:
                artifact = evidence_dir / f"{check_id}.log"
                try:
                    command = [resolve_tool(value, repo_root) for value in item["command"]]
                    completed = subprocess.run(
                        command,
                        cwd=repo_root,
                        env=environment,
                        text=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        timeout=item["timeoutSeconds"],
                        check=False,
                    )
                    artifact.write_text(redact(completed.stdout or "", environment), encoding="utf-8")
                    status = "passed" if completed.returncode == 0 else "failed"
                    result = {**base, "status": status, "exitCode": completed.returncode, "artifact": artifact.name}
                    if status == "failed":
                        result["diagnostic"] = f"command exited {completed.returncode}"
                except subprocess.TimeoutExpired as exc:
                    captured = exc.stdout or ""
                    if isinstance(captured, bytes):
                        captured = captured.decode(errors="replace")
                    artifact.write_text(redact(captured, environment), encoding="utf-8")
                    result = {**base, "status": "failed", "artifact": artifact.name, "diagnostic": f"timed out after {item['timeoutSeconds']} seconds"}
        states[check_id] = result["status"]
        results.append(result)

    required_states = [item["status"] for item in results if item["required"]]
    if "failed" in required_states:
        overall = "failed"
    elif any(status != "passed" for status in required_states):
        overall = "incomplete"
    else:
        overall = "passed"

    payload = {
        "schemaVersion": 1,
        "runId": f"complete-gate-{uuid.uuid4().hex}",
        "sourceCommit": source_commit,
        "startedAt": started,
        "finishedAt": now(),
        "overallStatus": overall,
        "checks": results,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["evidenceDigest"] = hashlib.sha256(canonical).hexdigest()
    atomic_json(evidence_dir / "result.json", payload)
    return payload


def git_commit(repo_root: Path) -> str:
    completed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True, capture_output=True, check=True)
    return completed.stdout.strip()


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    manifest_path = repo_root / "scripts" / "config" / "complete-gate-v1.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    evidence_dir = repo_root / ".artifacts" / "complete-gate" / run_id
    result = run_gate(manifest, repo_root, evidence_dir, source_commit=git_commit(repo_root))
    print(f"Complete gate: {result['overallStatus'].upper()}")
    print(f"Evidence: {evidence_dir / 'result.json'}")
    return {"passed": 0, "failed": 1, "incomplete": 2}[result["overallStatus"]]


if __name__ == "__main__":
    raise SystemExit(main())
