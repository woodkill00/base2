#!/usr/bin/env python3
"""Risk-based, compact Base2 assurance planning and execution."""

from __future__ import annotations

import argparse
import fcntl
import fnmatch
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager, suppress
from datetime import UTC, datetime
from dataclasses import asdict, dataclass
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any

try:
    from scripts.python.run_complete_gate import (
        open_private_directory,
        open_private_file,
        private_atomic_json,
        private_write,
        retryable_interpreter_corruption,
        retryable_native_crash,
    )
except ModuleNotFoundError:
    from run_complete_gate import (
        open_private_directory,
        open_private_file,
        private_atomic_json,
        private_write,
        retryable_interpreter_corruption,
        retryable_native_crash,
    )

ROOT = Path(__file__).resolve().parents[2]
GRAPH_PATH = Path("shared/config/assurance-orchestrator-v1.json")
TIERS = ("focused", "standard", "full", "release")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
SAFE_ID = re.compile(r"^[a-z][a-z0-9-]{1,63}$")


class AssuranceError(RuntimeError):
    """The assurance request cannot be admitted safely."""


@dataclass(frozen=True)
class Command:
    argv: tuple[str, ...]
    cwd: str = "."
    timeout: int = 300


COMMANDS: dict[str, Command] = {
    # Markdown formatters intentionally use two-space hard breaks. Retain Git's
    # conflict-marker and indentation checks without misclassifying those bytes.
    "diff-check": Command(("git", "-c", "core.whitespace=-blank-at-eol,-blank-at-eof,space-before-tab,tab-in-indent", "diff", "--check", "{base}"), timeout=30),
    "feature-plan": Command(("python3", "specs/107-efficient-assurance-orchestrator/validate_plan.py"), timeout=30),
    "contract-policy": Command(("python3", "-m", "unittest", "scripts.tests.test_production_readiness_contract"), timeout=45),
    "assurance-tests": Command((".venv/bin/python", "-m", "pytest", "-q", "-o", "addopts=", "scripts/tests/test_assurance_orchestrator.py", "scripts/tests/test_assurance_orchestrator_policy.py", "scripts/tests/test_assurance_benchmark.py"), timeout=60),
    "ci-policy": Command((".venv/bin/python", "-m", "pytest", "-q", "-o", "addopts=", "scripts/tests/test_ci_policy.py"), timeout=90),
    "api-unit": Command((".venv-api/bin/python", "-m", "pytest", "-q", "-o", "addopts=", "-m", "not integration and not perf", "api/tests"), timeout=240),
    "django-unit": Command((".venv-django/bin/python", "-m", "pytest", "-q", "-o", "addopts=", "-p", "no:cov", "django/tests"), timeout=180),
    "frontend-unit": Command(("node", "node_modules/vitest/vitest.mjs", "run", "--coverage=false", "--pool=threads", "--maxWorkers=1"), cwd="react-app", timeout=180),
    "visual-contract": Command(("node", "node_modules/playwright/cli.js", "test", "--config=playwright.operations-release.config.mjs"), cwd="react-app", timeout=300),
    "visual-full": Command(("node", "node_modules/playwright/cli.js", "test", "--config=playwright.visual-release.config.mjs"), cwd="react-app", timeout=600),
    "migration-contract": Command((".venv/bin/python", "-m", "pytest", "-q", "-o", "addopts=", "scripts/tests/test_migration_entrypoints.py", "scripts/tests/test_workspace_postgres_runner.py"), timeout=300),
    "deployment-contract": Command((".venv/bin/python", "-m", "pytest", "-q", "-o", "addopts=", "digital_ocean/tests/test_deployment_mode.py", "digital_ocean/tests/test_provider_ready.py", "digital_ocean/tests/test_deploy_config.py"), timeout=300),
    "security-policy": Command((".venv/bin/python", "-m", "pytest", "-q", "-o", "addopts=", "scripts/tests/test_security_action_contract.py", "scripts/tests/test_secure_file_lock.py"), timeout=120),
    "complete-gate": Command(("python3", "scripts/python/run_complete_gate.py"), timeout=1800),
}


@dataclass(frozen=True)
class Change:
    status: str
    path: str
    old_path: str | None
    content_digest: str


@dataclass(frozen=True)
class ChangeSet:
    base_commit: str
    head_commit: str
    diff_digest: str
    dirty: bool
    entries: tuple[Change, ...]


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _cycle(nodes: dict[str, dict[str, Any]], dependency_key: str) -> bool:
    visiting: set[str] = set()
    complete: set[str] = set()

    def visit(name: str) -> bool:
        if name in visiting:
            return True
        if name in complete:
            return False
        visiting.add(name)
        if any(visit(item) for item in nodes[name].get(dependency_key, [])):
            return True
        visiting.remove(name)
        complete.add(name)
        return False

    return any(visit(name) for name in nodes)


def validate_graph(graph: dict[str, Any]) -> dict[str, Any]:
    expected = {
        "schemaVersion", "graphVersion", "tierOrder", "mandatoryChecks", "outputPolicy",
        "evidencePolicy", "resourcePolicy", "pathRules", "surfaces", "checks",
    }
    if not isinstance(graph, dict) or set(graph) != expected or graph.get("schemaVersion") != 1:
        raise AssuranceError("graph_shape_invalid")
    if graph.get("tierOrder") != list(TIERS):
        raise AssuranceError("graph_tiers_invalid")
    surfaces = graph.get("surfaces")
    checks = graph.get("checks")
    if not isinstance(surfaces, dict) or not surfaces or not isinstance(checks, dict) or not checks:
        raise AssuranceError("graph_nodes_invalid")
    if any(not SAFE_ID.fullmatch(name) for name in [*surfaces, *checks]):
        raise AssuranceError("graph_id_invalid")
    for name, check in checks.items():
        if not isinstance(check, dict) or check.get("commandId") not in COMMANDS:
            raise AssuranceError(f"graph_command_unknown:{name}")
        if check.get("commandId") != name:
            raise AssuranceError(f"graph_command_binding_invalid:{name}")
        if set(check) != {"commandId", "dependsOn", "resource", "cache", "tiers"}:
            raise AssuranceError(f"graph_check_shape_invalid:{name}")
        if any(item not in checks for item in check["dependsOn"]):
            raise AssuranceError(f"graph_check_dependency_unknown:{name}")
        if not isinstance(check["cache"], bool) or not set(check["tiers"]) <= set(TIERS):
            raise AssuranceError(f"graph_check_policy_invalid:{name}")
        if check["resource"] not in {"light", "cpu", "docker", "browser", "exclusive"}:
            raise AssuranceError(f"graph_resource_invalid:{name}")
    for name, surface in surfaces.items():
        if set(surface) != {"checks", "dependsOn"}:
            raise AssuranceError(f"graph_surface_shape_invalid:{name}")
        if any(item not in checks for item in surface["checks"]):
            raise AssuranceError(f"graph_surface_check_unknown:{name}")
        if any(item not in surfaces for item in surface["dependsOn"]):
            raise AssuranceError(f"graph_surface_dependency_unknown:{name}")
    if _cycle(checks, "dependsOn") or _cycle(surfaces, "dependsOn"):
        raise AssuranceError("graph_dependency_cycle")
    mandatory = graph.get("mandatoryChecks")
    if not isinstance(mandatory, dict) or set(mandatory) != set(TIERS):
        raise AssuranceError("graph_mandatory_invalid")
    if any(item not in checks for values in mandatory.values() for item in values):
        raise AssuranceError("graph_mandatory_unknown")
    rules = graph.get("pathRules")
    if not isinstance(rules, list) or not rules:
        raise AssuranceError("graph_rules_invalid")
    for rule in rules:
        if (
            not isinstance(rule, dict)
            or set(rule) != {"glob", "surface", "minimumTier"}
            or not isinstance(rule["glob"], str)
            or ".." in Path(rule["glob"]).parts
            or rule["surface"] not in surfaces
            or rule["minimumTier"] not in TIERS
        ):
            raise AssuranceError("graph_rule_invalid")
    output = graph.get("outputPolicy", {})
    if output.get("successMaxBytes") != 4096 or output.get("successMaxLines") != 40:
        raise AssuranceError("graph_output_budget_invalid")
    resources = graph.get("resourcePolicy", {})
    if any(resources.get(name) != 1 for name in ("maxProcesses", "maxDocker", "maxBrowsers")):
        raise AssuranceError("graph_resource_budget_invalid")
    return graph


def load_graph(root: Path = ROOT) -> dict[str, Any]:
    path = root / GRAPH_PATH
    if path.is_symlink() or not path.is_file():
        raise AssuranceError("graph_missing")
    try:
        graph = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AssuranceError("graph_invalid") from exc
    return validate_graph(graph)


def _git(root: Path, arguments: list[str], *, accepted: set[int] = {0}) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            ["git", *arguments], cwd=root, capture_output=True, text=True, check=False,
            timeout=30, encoding="utf-8", errors="strict",
        )
    except UnicodeError as exc:
        raise AssuranceError("git_output_encoding_invalid") from exc
    if result.returncode not in accepted:
        raise AssuranceError("git_state_invalid")
    return result


def _file_digest(root: Path, relative: str) -> str:
    path = root / relative
    if not path.exists():
        return hashlib.sha256(b"deleted\0" + relative.encode()).hexdigest()
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
        details = path.lstat()
    except (OSError, ValueError) as exc:
        raise AssuranceError("change_path_invalid") from exc
    if stat.S_ISLNK(details.st_mode) or not stat.S_ISREG(details.st_mode):
        raise AssuranceError("change_member_unsafe")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _normalize_repo_path(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise AssuranceError("change_path_invalid")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value or any(part in {"", ".", ".."} for part in path.parts)
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
        or "\\" in value
    ):
        raise AssuranceError("change_path_invalid")
    return value


def _resolve_base(root: Path, head: str, supplied: str | None) -> str:
    if supplied is not None and not HEX40.fullmatch(supplied):
        raise AssuranceError("base_invalid")
    if supplied is None:
        reference = _git(root, ["rev-parse", "--verify", "origin/main^{commit}"], accepted={0, 128})
        target = reference.stdout.strip() if reference.returncode == 0 else head
        result = _git(root, ["merge-base", head, target])
        base = result.stdout.strip()
    else:
        base = supplied
        verified = _git(root, ["cat-file", "-e", f"{base}^{{commit}}"], accepted={0, 128})
        if verified.returncode:
            raise AssuranceError("base_invalid")
    ancestor = _git(root, ["merge-base", "--is-ancestor", base, head], accepted={0, 1})
    if ancestor.returncode or not HEX40.fullmatch(base):
        raise AssuranceError("base_not_ancestor")
    return base


def _parse_name_status(raw: str) -> list[tuple[str, str | None, str]]:
    fields = raw.split("\0")
    if fields and fields[-1] == "":
        fields.pop()
    parsed = []
    index = 0
    while index < len(fields):
        status = fields[index]
        index += 1
        if status.startswith(("R", "C")):
            if index + 1 >= len(fields):
                raise AssuranceError("diff_invalid")
            old_path, path = _normalize_repo_path(fields[index]), _normalize_repo_path(fields[index + 1])
            index += 2
        else:
            if index >= len(fields):
                raise AssuranceError("diff_invalid")
            old_path, path = None, _normalize_repo_path(fields[index])
            index += 1
        parsed.append((status, old_path, path))
    return parsed


def collect_changes(root: Path = ROOT, base: str | None = None) -> ChangeSet:
    project_root = root.resolve(strict=True)
    head = _git(project_root, ["rev-parse", "HEAD"]).stdout.strip()
    if not HEX40.fullmatch(head):
        raise AssuranceError("source_invalid")
    base_commit = _resolve_base(project_root, head, base)
    diff = _git(project_root, ["diff", "--name-status", "-z", "-M", base_commit, "--"])
    parsed = _parse_name_status(diff.stdout)
    untracked = _git(project_root, ["ls-files", "--others", "--exclude-standard", "-z"])
    seen = {(old, path) for _, old, path in parsed}
    for path in filter(None, untracked.stdout.split("\0")):
        if (None, path) not in seen:
            parsed.append(("?", None, _normalize_repo_path(path)))
    entries = tuple(
        sorted(
            (
                Change(status=status, old_path=old, path=path, content_digest=_file_digest(project_root, path))
                for status, old, path in parsed
            ),
            key=lambda item: (item.path, item.old_path or "", item.status),
        )
    )
    status = _git(project_root, ["status", "--porcelain=v1", "--untracked-files=all"])
    payload = [asdict(item) for item in entries]
    return ChangeSet(
        base_commit=base_commit,
        head_commit=head,
        diff_digest=_sha(payload),
        dirty=bool(status.stdout),
        entries=entries,
    )


def _closure(nodes: dict[str, dict[str, Any]], seeds: set[str]) -> set[str]:
    result = set(seeds)
    pending = list(seeds)
    while pending:
        for dependency in nodes[pending.pop()]["dependsOn"]:
            if dependency not in result:
                result.add(dependency)
                pending.append(dependency)
    return result


def _ordered_checks(
    checks: dict[str, dict[str, Any]], selected: set[str], history: dict[str, int] | None = None
) -> list[str]:
    result: list[str] = []
    remaining = set(selected)
    while remaining:
        ready = sorted(
            (name for name in remaining if set(checks[name]["dependsOn"]) <= set(result)),
            key=lambda name: ((history or {}).get(name, COMMANDS[name].timeout * 1000), name),
        )
        if not ready:
            raise AssuranceError("selected_check_cycle")
        result.extend(ready)
        remaining.difference_update(ready)
    return result


def build_plan(
    graph: dict[str, Any], changes: list[Change] | tuple[Change, ...], requested_tier: str,
    base_commit: str, head_commit: str, dirty: bool, history: dict[str, int] | None = None,
) -> dict[str, Any]:
    validate_graph(graph)
    if requested_tier not in {*TIERS, "auto"} or not HEX40.fullmatch(base_commit) or not HEX40.fullmatch(head_commit):
        raise AssuranceError("plan_request_invalid")
    surfaces: set[str] = set()
    minimum = "focused"
    reasons: list[str] = []
    ranks = {name: index for index, name in enumerate(TIERS)}
    for item in changes:
        paths = [item.path, *([item.old_path] if item.old_path else [])]
        for path in paths:
            matches = [rule for rule in graph["pathRules"] if fnmatch.fnmatchcase(path, rule["glob"])]
            if not matches:
                minimum = "full"
                reasons.append(f"unmapped_path:{path}")
            for rule in matches:
                surfaces.add(rule["surface"])
                if ranks[rule["minimumTier"]] > ranks[minimum]:
                    minimum = rule["minimumTier"]
                reasons.append(f"{path}->{rule['surface']}:{rule['minimumTier']}")
    if not changes:
        surfaces.add("docs")
        reasons.append("no_changes:focused_health")
    surfaces = _closure(graph["surfaces"], surfaces)
    requested = "focused" if requested_tier == "auto" else requested_tier
    resolved = TIERS[max(ranks[requested], ranks[minimum])]
    if resolved == "release":
        selected = set(graph["mandatoryChecks"]["release"])
    else:
        selected = set(graph["mandatoryChecks"][resolved])
        for surface in surfaces:
            selected.update(graph["surfaces"][surface]["checks"])
        selected = _closure(graph["checks"], selected)
    ordered = _ordered_checks(graph["checks"], selected, history)
    all_checks = sorted(graph["checks"])
    complete_reasons = sorted(set(reasons))
    payload = {
        "schemaVersion": 1,
        "sourceCommit": head_commit,
        "baseCommit": base_commit,
        "diffDigest": _sha([asdict(item) for item in changes]),
        "graphVersion": graph["graphVersion"],
        "graphDigest": _sha(graph),
        "requestedTier": requested_tier,
        "resolvedTier": resolved,
        "dirty": dirty,
        "surfaces": sorted(surfaces),
        "selected": ordered,
        "avoided": [name for name in all_checks if name not in selected],
        "reasonCount": len(complete_reasons),
        "reasonsDigest": _sha(complete_reasons),
        "reasons": complete_reasons[:12],
        "residualScope": "release gate not run" if resolved != "release" else "none within configured release gate",
    }
    payload["planDigest"] = _sha(payload)
    return payload


def require_executable_plan(plan: dict[str, Any]) -> None:
    if plan.get("dirty") and plan.get("resolvedTier") in {"full", "release"}:
        raise AssuranceError("dirty_strong_tier_forbidden")


def _resolved_command(check_id: str, plan: dict[str, Any], root: Path) -> tuple[list[str], Path, int]:
    command_id = check_id
    if command_id not in COMMANDS:
        raise AssuranceError("command_unknown")
    command = COMMANDS[command_id]
    argv = [plan["baseCommit"] if item == "{base}" else item for item in command.argv]
    argv[0] = str(_resolve_executable(command, root))
    if any("\x00" in item or "\n" in item for item in argv):
        raise AssuranceError("command_argument_invalid")
    cwd = (root / command.cwd).resolve(strict=True)
    try:
        cwd.relative_to(root.resolve(strict=True))
    except ValueError as exc:
        raise AssuranceError("command_cwd_invalid") from exc
    return argv, cwd, command.timeout


def _approved_tool_directories() -> list[Path]:
    directories = [Path(item) for item in (
        "/usr/local/sbin", "/usr/local/bin", "/usr/sbin", "/usr/bin", "/sbin", "/bin"
    ) if Path(item).is_dir()]
    node_root = Path.home() / ".local" / "lib" / "nodejs"
    if node_root.is_dir():
        directories.extend(path for path in sorted(node_root.glob("node-*/bin")) if path.is_dir())
    return directories


def _resolve_named_executable(name: str) -> Path:
    for directory in _approved_tool_directories():
        candidate = directory / name
        if candidate.exists() and os.access(candidate, os.X_OK):
            resolved = candidate.resolve(strict=True)
            if resolved.is_file():
                return resolved
    raise AssuranceError(f"tool_unavailable:{name}")


def _safe_playwright_path() -> Path | None:
    cache_root = Path.home() / ".cache"
    candidate = cache_root / "ms-playwright"
    try:
        cache_details = cache_root.lstat()
        details = candidate.lstat()
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(cache_root.resolve(strict=True))
    except (OSError, ValueError):
        return None
    if (
        stat.S_ISLNK(cache_details.st_mode) or not stat.S_ISDIR(cache_details.st_mode)
        or cache_details.st_uid != os.geteuid() or stat.S_IMODE(cache_details.st_mode) & 0o077
        or stat.S_ISLNK(details.st_mode) or not stat.S_ISDIR(details.st_mode)
        or details.st_uid != os.geteuid() or stat.S_IMODE(details.st_mode) & 0o022
    ):
        return None
    return resolved


def _environment(home: Path, check_id: str | None = None) -> dict[str, str]:
    environment = {
        "CI": "1",
        "HOME": str(home),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "NO_PROXY": "*",
        "PATH": os.pathsep.join(str(path) for path in _approved_tool_directories()),
        "PYTHONHASHSEED": "0",
        "PYTHONMALLOC": "malloc",
        "XDG_CACHE_HOME": str(home / ".cache"),
        "XDG_CONFIG_HOME": str(home / ".config"),
    }
    if check_id in {"visual-contract", "visual-full"}:
        browser_path = _safe_playwright_path()
        if browser_path is None:
            raise AssuranceError("playwright_browser_path_unsafe")
        environment["PLAYWRIGHT_BROWSERS_PATH"] = str(browser_path)
    return environment


@contextmanager
def _run_lease(root: Path):
    try:
        directory_fd = open_private_directory(root / ".artifacts" / "assurance-orchestrator", root)
    except (OSError, ValueError) as exc:
        raise AssuranceError("evidence_root_unsafe") from exc
    descriptor: int | None = None
    try:
        try:
            descriptor = os.open(
                "run.lock", os.O_CREAT | os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW,
                0o600, dir_fd=directory_fd,
            )
        except OSError as exc:
            raise AssuranceError("run_lock_unsafe") from exc
        details = os.fstat(descriptor)
        if (
            not stat.S_ISREG(details.st_mode) or details.st_uid != os.geteuid()
            or details.st_nlink != 1
        ):
            raise AssuranceError("run_lock_unsafe")
        os.fchmod(descriptor, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise AssuranceError("run_busy") from exc
        yield directory_fd
    finally:
        if descriptor is not None:
            with suppress(OSError):
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)
        os.close(directory_fd)


def _open_child(directory_fd: int, name: str, *, create: bool) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    if create:
        with suppress(FileExistsError):
            os.mkdir(name, 0o700, dir_fd=directory_fd)
    child = os.open(name, flags, dir_fd=directory_fd)
    details = os.fstat(child)
    if details.st_uid != os.geteuid() or stat.S_IMODE(details.st_mode) != 0o700:
        os.close(child)
        raise AssuranceError("evidence_directory_unsafe")
    return child


def _read_private(directory_fd: int, name: str, maximum: int) -> bytes:
    descriptor = os.open(name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=directory_fd)
    try:
        details = os.fstat(descriptor)
        if (
            not stat.S_ISREG(details.st_mode) or details.st_uid != os.geteuid()
            or details.st_nlink != 1 or stat.S_IMODE(details.st_mode) != 0o600
            or details.st_size > maximum
        ):
            raise AssuranceError("evidence_member_unsafe")
        with os.fdopen(os.dup(descriptor), "rb") as stream:
            return stream.read(maximum + 1)
    finally:
        os.close(descriptor)


def _resolve_executable(command: Command, root: Path) -> Path:
    executable = command.argv[0]
    if "/" in executable:
        path = (root / executable).absolute()
        try:
            path.relative_to(root.resolve(strict=True))
            details = path.lstat()
            target = path.resolve(strict=True)
        except (OSError, ValueError) as exc:
            raise AssuranceError(f"tool_unavailable:{executable}") from exc
        managed_python = (
            executable in {
                ".venv/bin/python", ".venv-api/bin/python", ".venv-django/bin/python",
            }
            and (stat.S_ISREG(details.st_mode) or stat.S_ISLNK(details.st_mode))
            and target.is_file() and os.access(path, os.X_OK)
        )
        if not managed_python:
            raise AssuranceError("tool_unsafe")
    else:
        path = _resolve_named_executable(executable)
    try:
        path.relative_to(root.resolve(strict=True))
    except ValueError:
        pass
    else:
        if ".artifacts" in path.parts:
            raise AssuranceError("tool_unsafe")
    return path


def _executable_identity(command: Command, root: Path) -> dict[str, Any]:
    path = _resolve_executable(command, root)
    link_details = path.lstat()
    details = path.stat()
    if not stat.S_ISREG(details.st_mode):
        raise AssuranceError("tool_unsafe")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {
        "path": str(path), "target": str(path.resolve(strict=True)),
        "linked": stat.S_ISLNK(link_details.st_mode),
        "bytes": details.st_size, "sha256": digest.hexdigest(),
    }


def _regular_file_identity(path: Path, boundary: Path) -> dict[str, Any]:
    try:
        details = path.lstat()
        resolved = path.resolve(strict=True)
        resolved.relative_to(boundary.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise AssuranceError("dependency_manifest_missing") from exc
    if stat.S_ISLNK(details.st_mode) or not stat.S_ISREG(details.st_mode):
        raise AssuranceError("dependency_manifest_unsafe")
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise AssuranceError("dependency_manifest_unreadable") from exc
    return {"path": str(resolved), "bytes": details.st_size, "sha256": digest.hexdigest()}


def _python_distribution_identity(command: Command, root: Path) -> dict[str, Any]:
    executable = _resolve_executable(command, root)
    probe = (
        "import importlib.metadata as m,json;"
        "print(json.dumps(sorted((d.metadata.get('Name','').lower(),d.version) "
        "for d in m.distributions()),separators=(',',':')))"
    )
    try:
        result = subprocess.run(
            [str(executable), "-I", "-c", probe], cwd=root,
            env={
                "HOME": "/nonexistent", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
                "NO_PROXY": "*", "PATH": str(executable.parent), "PYTHONHASHSEED": "0",
            },
            capture_output=True, check=False, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AssuranceError("python_distribution_probe_failed") from exc
    if result.returncode != 0 or len(result.stdout) > 1024 * 1024:
        raise AssuranceError("python_distribution_probe_failed")
    try:
        distributions = json.loads(result.stdout.decode("utf-8", errors="strict"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AssuranceError("python_distribution_probe_invalid") from exc
    if not isinstance(distributions, list) or any(
        not isinstance(item, list) or len(item) != 2
        or not all(isinstance(value, str) for value in item)
        for item in distributions
    ):
        raise AssuranceError("python_distribution_probe_invalid")
    return {"count": len(distributions), "sha256": _sha(distributions)}


def _browser_installation_identity() -> dict[str, Any]:
    path = _safe_playwright_path()
    if path is None:
        raise AssuranceError("playwright_browser_path_unsafe")
    try:
        entries = sorted(item.name for item in path.iterdir())
        details = path.stat()
    except OSError as exc:
        raise AssuranceError("playwright_browser_path_unsafe") from exc
    return {
        "path": str(path), "device": details.st_dev, "inode": details.st_ino,
        "entries": entries, "entriesDigest": _sha(entries),
    }


def _runtime_dependency_identity(check_id: str, command: Command, root: Path) -> dict[str, Any]:
    identity: dict[str, Any] = {}
    if command.argv[0].startswith((".venv/", ".venv-api/", ".venv-django/")):
        identity["pythonDistributions"] = _python_distribution_identity(command, root)
    if command.argv[0] == "node":
        identity["nodeInstalledLock"] = _regular_file_identity(
            root / "react-app" / "node_modules" / ".package-lock.json", root,
        )
    if check_id in {"visual-contract", "visual-full"}:
        identity["playwrightBrowsers"] = _browser_installation_identity()
    return identity


def _toolchain_identity(check_id: str, command: Command, root: Path) -> str:
    return _sha({
        "executable": _executable_identity(command, root),
        "runtimeDependencies": _runtime_dependency_identity(check_id, command, root),
        "orchestratorPython": sys.version,
    })


def _input_binding(check_id: str, plan: dict[str, Any], graph: dict[str, Any], root: Path) -> dict[str, str]:
    command = COMMANDS[check_id]
    binding = {
        "checkId": check_id,
        "sourceCommit": plan["sourceCommit"],
        "diffDigest": plan["diffDigest"],
        "graphDigest": plan["graphDigest"],
        "commandDigest": _sha(asdict(command)),
        "toolchainDigest": _toolchain_identity(check_id, command, root),
        "environmentClass": "local-wsl-v1",
        "cachePolicyDigest": _sha(graph["checks"][check_id]["cache"]),
    }
    return binding


def _input_digest(check_id: str, plan: dict[str, Any], graph: dict[str, Any], root: Path) -> str:
    return _sha(_input_binding(check_id, plan, graph, root))


def exact_complete_gate_evidence(root: Path, source_commit: str) -> str | None:
    if not HEX40.fullmatch(source_commit):
        raise AssuranceError("release_evidence_source_invalid")
    try:
        parent_fd = open_private_directory(
            root / ".artifacts" / "complete-gate", root, create=False,
        )
    except (OSError, ValueError):
        return None
    try:
        names = sorted(
            name for name in os.listdir(parent_fd)
            if re.fullmatch(r"[0-9]{8}T[0-9]{6}Z-[0-9]+", name)
        )
        for name in reversed(names):
            try:
                run_fd = _open_child(parent_fd, name, create=False)
                try:
                    payload = json.loads(_read_private(run_fd, "result.json", 2 * 1024 * 1024))
                finally:
                    os.close(run_fd)
            except (OSError, UnicodeError, json.JSONDecodeError, AssuranceError):
                continue
            supplied = payload.get("evidenceDigest")
            unsigned = {key: value for key, value in payload.items() if key != "evidenceDigest"}
            checks = payload.get("checks")
            if (
                payload.get("schemaVersion") == 1
                and payload.get("sourceCommit") == source_commit
                and payload.get("overallStatus") == "passed"
                and supplied == _sha(unsigned)
                and isinstance(checks, list) and checks
                and all(item.get("status") == "passed" for item in checks if item.get("required"))
            ):
                return f".artifacts/complete-gate/{name}/result.json"
        return None
    finally:
        os.close(parent_fd)


def _cached_receipt(cache_fd: int, input_digest: str, now: int) -> dict[str, Any] | None:
    try:
        entry_fd = _open_child(cache_fd, input_digest, create=False)
    except FileNotFoundError:
        return None
    try:
        if set(os.listdir(entry_fd)) != {"result.json", "output.log"}:
            raise AssuranceError("cache_invalid")
        raw = _read_private(entry_fd, "result.json", 65536)
        receipt = json.loads(raw.decode("utf-8"))
        supplied = receipt.get("integrity")
        unsigned = {key: value for key, value in receipt.items() if key != "integrity"}
        if (
            receipt.get("schemaVersion") != 1 or receipt.get("status") != "passed"
            or receipt.get("inputDigest") != input_digest or supplied != _sha(unsigned)
        ):
            raise AssuranceError("cache_invalid")
        log = _read_private(entry_fd, "output.log", 4 * 1024 * 1024)
        if len(log) != receipt.get("logBytes") or hashlib.sha256(log).hexdigest() != receipt.get("logSha256"):
            raise AssuranceError("cache_log_changed")
        if receipt.get("expiresAtEpoch", 0) < now:
            for name in ("result.json", "output.log"):
                os.unlink(name, dir_fd=entry_fd)
            os.close(entry_fd)
            entry_fd = -1
            os.rmdir(input_digest, dir_fd=cache_fd)
            return None
        return receipt
    except (OSError, json.JSONDecodeError, UnicodeError) as exc:
        raise AssuranceError("cache_invalid") from exc
    finally:
        if entry_fd >= 0:
            os.close(entry_fd)


def _write_cache(cache_fd: int, receipt: dict[str, Any], log: bytes) -> None:
    input_digest = receipt["inputDigest"]
    stage = f".{input_digest}.{uuid.uuid4().hex}"
    stage_fd: int | None = None
    try:
        os.mkdir(stage, 0o700, dir_fd=cache_fd)
        stage_fd = _open_child(cache_fd, stage, create=False)
        private_write(stage_fd, "output.log", log)
        private_atomic_json(stage_fd, "result.json", receipt)
        os.close(stage_fd)
        stage_fd = None
        os.rename(stage, input_digest, src_dir_fd=cache_fd, dst_dir_fd=cache_fd)
        os.fsync(cache_fd)
    finally:
        if stage_fd is not None:
            os.close(stage_fd)
        with suppress(OSError):
            cleanup_fd = _open_child(cache_fd, stage, create=False)
            try:
                for name in os.listdir(cleanup_fd):
                    details = os.stat(name, dir_fd=cleanup_fd, follow_symlinks=False)
                    if not stat.S_ISREG(details.st_mode) or details.st_uid != os.geteuid() or details.st_nlink != 1:
                        raise AssuranceError("cache_stage_unsafe")
                    os.unlink(name, dir_fd=cleanup_fd)
            finally:
                os.close(cleanup_fd)
            os.rmdir(stage, dir_fd=cache_fd)


def _cleanup_cache_stages(cache_fd: int) -> None:
    pattern = re.compile(r"^\.[0-9a-f]{64}\.[0-9a-f]{32}$")
    for name in os.listdir(cache_fd):
        if not pattern.fullmatch(name):
            continue
        stage_fd = _open_child(cache_fd, name, create=False)
        try:
            for member in os.listdir(stage_fd):
                if member not in {"result.json", "output.log"}:
                    raise AssuranceError("cache_stage_unsafe")
                details = os.stat(member, dir_fd=stage_fd, follow_symlinks=False)
                if (
                    not stat.S_ISREG(details.st_mode) or details.st_uid != os.geteuid()
                    or details.st_nlink != 1 or stat.S_IMODE(details.st_mode) != 0o600
                ):
                    raise AssuranceError("cache_stage_unsafe")
                os.unlink(member, dir_fd=stage_fd)
        finally:
            os.close(stage_fd)
        os.rmdir(name, dir_fd=cache_fd)


def _history_from_fd(root_fd: int) -> dict[str, list[int]]:
    try:
        payload = json.loads(_read_private(root_fd, "history.json", 65536).decode("utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AssuranceError("history_invalid") from exc
    supplied = payload.get("integrity")
    unsigned = {key: value for key, value in payload.items() if key != "integrity"}
    samples = payload.get("samples")
    if payload.get("schemaVersion") != 1 or supplied != _sha(unsigned) or not isinstance(samples, dict):
        raise AssuranceError("history_invalid")
    for name, values in samples.items():
        if name not in COMMANDS or not isinstance(values, list) or len(values) > 20 or any(
            not isinstance(value, int) or value < 0 for value in values
        ):
            raise AssuranceError("history_invalid")
    return samples


def _next_run_sequence(root_fd: int) -> int:
    try:
        payload = json.loads(_read_private(root_fd, "sequence.json", 4096).decode("utf-8"))
    except FileNotFoundError:
        current = 0
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AssuranceError("sequence_invalid") from exc
    else:
        supplied = payload.get("integrity")
        unsigned = {key: value for key, value in payload.items() if key != "integrity"}
        if (
            payload.get("schemaVersion") != 1 or supplied != _sha(unsigned)
            or not isinstance(payload.get("value"), int) or not 0 <= payload["value"] < 10**20 - 1
        ):
            raise AssuranceError("sequence_invalid")
        current = payload["value"]
    result = {"schemaVersion": 1, "value": current + 1}
    result["integrity"] = _sha(result)
    private_atomic_json(root_fd, "sequence.json", result)
    return current + 1


def load_history(root: Path = ROOT) -> dict[str, int]:
    try:
        root_fd = open_private_directory(root / ".artifacts" / "assurance-orchestrator", root, create=False)
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        raise AssuranceError("history_invalid") from exc
    try:
        samples = _history_from_fd(root_fd)
    finally:
        os.close(root_fd)
    return {name: sum(values) // len(values) for name, values in samples.items() if values}


def _update_history(root_fd: int, receipts: list[dict[str, Any]], executed: set[str]) -> None:
    samples = _history_from_fd(root_fd)
    for receipt in receipts:
        name = receipt.get("checkId")
        duration = receipt.get("durationMilliseconds")
        if name in executed and isinstance(duration, int) and duration >= 0:
            samples[name] = [*samples.get(name, []), duration][-20:]
    payload = {"schemaVersion": 1, "samples": dict(sorted(samples.items()))}
    payload["integrity"] = _sha(payload)
    private_atomic_json(root_fd, "history.json", payload)


def _redact_output(output: bytes) -> bytes:
    text = output.decode("utf-8", errors="replace")
    text = re.sub(r"(?i)(token|secret|password|authorization)(\s*[:=]\s*)\S+", r"\1\2[REDACTED]", text)
    return text.encode("utf-8")


def _sanitized_tail(output: bytes) -> str:
    text = output.decode("utf-8", errors="replace")
    return "\n".join(text.splitlines()[-12:])[-2048:]


def execute_plan(root: Path, graph: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    require_executable_plan(plan)
    project_root = root.resolve(strict=True)
    release_evidence = None if plan["dirty"] else exact_complete_gate_evidence(
        project_root, plan["sourceCommit"],
    )
    if release_evidence is not None:
        return {
            "schemaVersion": 1, "status": "passed", "sourceCommit": plan["sourceCommit"],
            "requestedTier": plan["requestedTier"], "resolvedTier": "release",
            "planDigest": plan["planDigest"], "selected": plan["selected"],
            "reused": ["complete-gate"], "executed": [], "failed": [], "blocked": [],
            "avoided": plan["avoided"], "wallMilliseconds": 0, "outputBytes": 0,
            "estimatedTokens": 0, "evidencePath": release_evidence,
            "residualScope": "none within exact complete gate",
        }
    started = time.monotonic_ns()
    now = int(time.time())
    executed: list[str] = []
    reused: list[str] = []
    failed: list[str] = []
    blocked: list[str] = []
    receipts: list[dict[str, Any]] = []
    with _run_lease(project_root) as root_fd:
        runs_fd = _open_child(root_fd, "runs", create=True)
        cache_fd = _open_child(root_fd, "cache", create=True)
        _cleanup_cache_stages(cache_fd)
        run_id = f"{_next_run_sequence(root_fd):020d}-{uuid.uuid4().hex}"
        os.mkdir(run_id, 0o700, dir_fd=runs_fd)
        run_fd = _open_child(runs_fd, run_id, create=False)
        try:
            started_receipt = {
                "schemaVersion": 1,
                "status": "started",
                "sourceCommit": plan["sourceCommit"],
                "baseCommit": plan["baseCommit"],
                "diffDigest": plan["diffDigest"],
                "planDigest": plan["planDigest"],
                "startedAt": datetime.now(UTC).isoformat(),
            }
            started_receipt["integrity"] = _sha(started_receipt)
            private_atomic_json(run_fd, "started.json", started_receipt)
            dependency_status: dict[str, str] = {}
            with tempfile.TemporaryDirectory(prefix="base2-assurance-home.") as raw_home:
                home = Path(raw_home)
                home.chmod(0o700)
                for position, check_id in enumerate(plan["selected"]):
                    dependencies = graph["checks"][check_id]["dependsOn"]
                    if any(dependency_status.get(item) != "passed" for item in dependencies):
                        dependency_status[check_id] = "blocked"
                        blocked.append(check_id)
                        continue
                    binding = _input_binding(check_id, plan, graph, project_root)
                    input_digest = _sha(binding)
                    cached = None
                    if graph["checks"][check_id]["cache"] and not plan["dirty"] and plan["resolvedTier"] != "release":
                        cached = _cached_receipt(cache_fd, input_digest, now)
                    if cached is not None:
                        reused.append(check_id)
                        dependency_status[check_id] = "passed"
                        receipts.append(cached)
                        continue
                    argv, cwd, timeout = _resolved_command(check_id, plan, project_root)
                    environment = _environment(home, check_id)
                    attempt_started = time.monotonic_ns()
                    attempts = 0
                    attempt_outputs: list[bytes] = []
                    while attempts < 2:
                        attempts += 1
                        try:
                            result = subprocess.run(
                                argv, cwd=cwd, env=environment, capture_output=True, check=False,
                                timeout=timeout,
                            )
                            output = (result.stdout or b"") + (result.stderr or b"")
                            return_code = result.returncode
                            status_value = "passed" if return_code == 0 else "failed"
                        except subprocess.TimeoutExpired as exc:
                            output = (exc.stdout or b"") + (exc.stderr or b"")
                            return_code = 124
                            status_value = "failed"
                        except OSError as exc:
                            output = f"assurance: check launch failed: {type(exc).__name__}\n".encode()
                            return_code = 126
                            status_value = "failed"
                        if isinstance(output, str):
                            output = output.encode("utf-8", errors="replace")
                        current_toolchain = _toolchain_identity(check_id, COMMANDS[check_id], project_root)
                        if current_toolchain != binding["toolchainDigest"]:
                            output += b"\nassurance: executable identity changed during check\n"
                            return_code = 125
                            status_value = "failed"
                        attempt_outputs.append(
                            f"=== attempt {attempts} exit {return_code} ===\n".encode() + output
                        )
                        decoded = output.decode("utf-8", errors="replace")
                        retryable = (
                            attempts == 1 and status_value == "failed" and return_code != 124
                            and (
                                retryable_native_crash(return_code, decoded)
                                or retryable_interpreter_corruption(decoded)
                            )
                        )
                        if not retryable:
                            break
                    output = b"\n".join(attempt_outputs)
                    maximum = graph["outputPolicy"]["logMaxBytes"]
                    redacted = _redact_output(output)
                    bounded = redacted[:maximum]
                    log_name = f"{len(receipts):03d}-{check_id}.log"
                    log_sha, log_bytes = private_write(run_fd, log_name, bounded)
                    duration = (time.monotonic_ns() - attempt_started) // 1_000_000
                    receipt = {
                        "schemaVersion": 1,
                        "checkId": check_id,
                        "inputDigest": input_digest,
                        **binding,
                        "status": status_value,
                        "exitCode": return_code,
                        "durationMilliseconds": duration,
                        "attempts": attempts,
                        "logSha256": log_sha,
                        "logBytes": log_bytes,
                        "logTruncated": len(redacted) > len(bounded),
                        "summary": "passed" if status_value == "passed" else _sanitized_tail(bounded),
                        "expiresAtEpoch": now + graph["evidencePolicy"]["passedTtlSeconds"],
                    }
                    receipt["integrity"] = _sha(receipt)
                    receipts.append(receipt)
                    executed.append(check_id)
                    dependency_status[check_id] = status_value
                    if status_value == "passed" and graph["checks"][check_id]["cache"] and not plan["dirty"]:
                        _write_cache(cache_fd, receipt, bounded)
                    if status_value != "passed":
                        failed.append(check_id)
                        blocked.extend(plan["selected"][position + 1 :])
                        break
            wall = (time.monotonic_ns() - started) // 1_000_000
            aggregate = {
                "schemaVersion": 1,
                "status": "passed" if not failed and not blocked else "failed",
                "sourceCommit": plan["sourceCommit"],
                "baseCommit": plan["baseCommit"],
                "diffDigest": plan["diffDigest"],
                "dirty": plan["dirty"],
                "requestedTier": plan["requestedTier"],
                "resolvedTier": plan["resolvedTier"],
                "planDigest": plan["planDigest"],
                "selected": plan["selected"],
                "reused": reused,
                "executed": executed,
                "failed": failed,
                "blocked": blocked,
                "avoided": plan["avoided"],
                "wallMilliseconds": wall,
                "processMilliseconds": sum(item["durationMilliseconds"] for item in receipts if "durationMilliseconds" in item),
                "outputBytes": 0,
                "estimatedTokens": 0,
                "evidencePath": f".artifacts/assurance-orchestrator/runs/{run_id}/result.json",
                "receipts": receipts,
                "residualScope": plan["residualScope"],
            }
            summary = {key: aggregate[key] for key in (
                "schemaVersion", "status", "sourceCommit", "requestedTier", "resolvedTier",
                "planDigest", "selected", "reused", "executed", "failed", "blocked", "avoided",
                "wallMilliseconds", "outputBytes", "estimatedTokens", "evidencePath", "residualScope",
            )}
            provisional = compact_json(summary)
            summary["outputBytes"] = len(provisional.encode())
            summary["estimatedTokens"] = estimate_tokens(summary["outputBytes"])
            for _ in range(3):
                rendered = compact_json(summary)
                summary["outputBytes"] = len(rendered.encode())
                summary["estimatedTokens"] = estimate_tokens(summary["outputBytes"])
            aggregate["outputBytes"] = summary["outputBytes"]
            aggregate["estimatedTokens"] = summary["estimatedTokens"]
            aggregate["integrity"] = _sha(aggregate)
            private_atomic_json(run_fd, "result.json", aggregate)
            _update_history(root_fd, receipts, set(executed))
            return summary
        finally:
            os.close(run_fd)
            os.close(cache_fd)
            os.close(runs_fd)


def estimate_tokens(output_bytes: int) -> int:
    if not isinstance(output_bytes, int) or output_bytes < 0:
        raise AssuranceError("output_bytes_invalid")
    return (output_bytes + 3) // 4


def compact_json(payload: dict[str, Any], *, max_bytes: int = 4096, max_lines: int = 40) -> str:
    rendered = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    if len(rendered.encode()) > max_bytes or len(rendered.splitlines()) > max_lines:
        raise AssuranceError("compact_output_budget_exceeded")
    return rendered


def benchmark_report(
    *, legacy_measured_ms: int, optimized_measured_ms: int, legacy_output_bytes: int,
    optimized_output_bytes: int, estimated_avoided_ms: int, mutations_detected: int,
    mutations_total: int,
) -> dict[str, Any]:
    measured = (legacy_measured_ms, optimized_measured_ms, legacy_output_bytes, optimized_output_bytes)
    if any(not isinstance(value, int) or value <= 0 for value in measured):
        raise AssuranceError("benchmark_measurement_invalid")
    if not 0 <= mutations_detected <= mutations_total or mutations_total <= 0 or estimated_avoided_ms < 0:
        raise AssuranceError("benchmark_measurement_invalid")
    time_reduction = round((legacy_measured_ms - optimized_measured_ms) * 100 / legacy_measured_ms)
    output_reduction = round((legacy_output_bytes - optimized_output_bytes) * 100 / legacy_output_bytes)
    return {
        "schemaVersion": 1,
        "status": "passed" if time_reduction >= 50 and output_reduction >= 90 and mutations_detected == mutations_total else "failed",
        "timeReductionPercent": time_reduction,
        "outputReductionPercent": output_reduction,
        "legacyMeasuredMilliseconds": legacy_measured_ms,
        "optimizedMeasuredMilliseconds": optimized_measured_ms,
        "estimatedAvoidedMilliseconds": estimated_avoided_ms,
        "mutationsDetected": mutations_detected,
        "mutationsTotal": mutations_total,
    }


def validate_hosted_export(payload: dict[str, Any], source_commit: str, required_jobs: set[str]) -> dict[str, Any]:
    """Validate an offline sanitized export without granting hosted authority."""
    if not HEX40.fullmatch(source_commit) or not isinstance(payload, dict) or set(payload) != {
        "schemaVersion", "sourceCommit", "workflowPath", "workflowCommit", "jobs",
    }:
        raise AssuranceError("hosted_export_invalid")
    if (
        payload["schemaVersion"] != 1
        or payload["sourceCommit"] != source_commit
        or payload["workflowPath"] not in {
            ".github/workflows/ci-backend.yml", ".github/workflows/ci-contract.yml",
            ".github/workflows/ci-e2e.yml", ".github/workflows/ci-frontend.yml",
            ".github/workflows/ci-perf-smoke.yml", ".github/workflows/ci-repo-guards.yml",
            ".github/workflows/ci-smoke.yml", ".github/workflows/security.yml",
        }
        or payload["workflowCommit"] != source_commit
        or not isinstance(payload["jobs"], list)
    ):
        raise AssuranceError("hosted_export_invalid")
    jobs = payload["jobs"]
    if any(
        not isinstance(item, dict) or set(item) != {"name", "conclusion"}
        or not SAFE_ID.fullmatch(str(item["name"])) or item["conclusion"] != "success"
        for item in jobs
    ):
        raise AssuranceError("hosted_export_invalid")
    names = {item["name"] for item in jobs}
    if not required_jobs <= names:
        raise AssuranceError("hosted_export_incomplete")
    return {
        "status": "validated-informational",
        "sourceCommit": source_commit,
        "jobs": sorted(names),
        "reusable": False,
        "authority": "none",
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(prog="assurance-orchestrator")
    value.add_argument("action", nargs="?", choices=("plan", "run", "status", "explain"), default="run")
    value.add_argument("--tier", choices=("auto", *TIERS), default="auto")
    value.add_argument("--base")
    value.add_argument("--json", action="store_true")
    return value


def latest_status(root: Path = ROOT) -> dict[str, Any]:
    try:
        runs_fd = open_private_directory(
            root / ".artifacts" / "assurance-orchestrator" / "runs", root,
            create=False,
        )
    except (OSError, ValueError) as exc:
        raise AssuranceError("status_unavailable") from exc
    try:
        names = sorted(name for name in os.listdir(runs_fd) if re.fullmatch(r"[0-9]{20}-[0-9a-f]{32}", name))
        if not names:
            raise AssuranceError("status_unavailable")
        run_fd = _open_child(runs_fd, names[-1], create=False)
        try:
            try:
                payload = json.loads(_read_private(run_fd, "result.json", 1024 * 1024).decode("utf-8"))
            except FileNotFoundError:
                started = json.loads(_read_private(run_fd, "started.json", 65536).decode("utf-8"))
                supplied = started.get("integrity")
                unsigned = {key: value for key, value in started.items() if key != "integrity"}
                if supplied != _sha(unsigned) or started.get("status") != "started":
                    raise AssuranceError("status_integrity_invalid")
                return {
                    "schemaVersion": 1,
                    "status": "interrupted",
                    "sourceCommit": started["sourceCommit"],
                    "planDigest": started["planDigest"],
                    "evidencePath": f".artifacts/assurance-orchestrator/runs/{names[-1]}/started.json",
                    "current": False,
                }
        finally:
            os.close(run_fd)
    finally:
        os.close(runs_fd)
    supplied = payload.get("integrity")
    unsigned = {key: value for key, value in payload.items() if key != "integrity"}
    if supplied != _sha(unsigned):
        raise AssuranceError("status_integrity_invalid")
    summary = {key: payload[key] for key in (
        "schemaVersion", "status", "sourceCommit", "requestedTier", "resolvedTier",
        "planDigest", "selected", "reused", "executed", "failed", "blocked", "avoided",
        "wallMilliseconds", "outputBytes", "estimatedTokens", "evidencePath", "residualScope",
    )}
    try:
        current = collect_changes(root, payload["baseCommit"])
        summary["current"] = (
            current.head_commit == payload["sourceCommit"]
            and current.diff_digest == payload["diffDigest"]
            and current.dirty == payload["dirty"]
        )
    except AssuranceError:
        summary["current"] = False
    return summary


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        if arguments.action == "status":
            payload = latest_status(ROOT)
        else:
            graph = load_graph(ROOT)
            change_set = collect_changes(ROOT, arguments.base)
            plan = build_plan(
                graph, change_set.entries, arguments.tier, change_set.base_commit,
                change_set.head_commit, change_set.dirty, load_history(ROOT),
            )
            if arguments.action == "run":
                payload = execute_plan(ROOT, graph, plan)
            else:
                payload = {**plan, "status": "planned", "evidencePath": None}
        print(compact_json(payload), end="")
        return 0 if payload.get("status") in {"planned", "passed"} else 1
    except AssuranceError as exc:
        print(compact_json({"schemaVersion": 1, "status": "error", "error": str(exc)}), end="")
        return 3 if str(exc) == "run_busy" else 2
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError):
        print(compact_json({"schemaVersion": 1, "status": "error", "error": "assurance_storage_invalid"}), end="")
        return 2
    except KeyboardInterrupt:
        print(compact_json({"schemaVersion": 1, "status": "interrupted"}), end="")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
