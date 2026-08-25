#!/usr/bin/env python3
"""Fail closed when declared docs/config/API/client/module/route surfaces drift."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


GROUPS = {
    "docs": (
        "docs/ARCHITECTURE.md",
        "docs/CONFIG.md",
        "docs/DEPLOY.md",
        "docs/SECURITY.md",
        "docs/TESTING.md",
        "docs/module-sdk.md",
        "docs/website-factory.md",
        "docs/feature-093-production-readiness.md",
    ),
    "config": (
        ".env.example",
        "scripts/config/complete-gate-v1.json",
        "shared/config/*.json",
        "api/site_profiles/*.json",
        "django/site_profiles/*.json",
    ),
    "openapi": (
        "specs/001-django-fastapi-react/contracts/openapi.yaml",
        "digital_ocean/contracts/openapi.yaml",
    ),
    "generatedClient": (
        "react-app/src/lib/apiClient.js",
        "react-app/src/lib/apiErrors.js",
        "react-app/src/config/generated/*.json",
    ),
    "moduleInventory": (
        "modules/*/module.json",
        "modules/*/settings.schema.json",
        "shared/config/module-catalog.json",
    ),
    "routeInventory": (
        "api/main.py",
        "api/routes/*.py",
        "django/project/urls.py",
        "django/users/urls.py",
        "django/catalog/urls.py",
        "react-app/src/App.js",
        "react-app/src/routes/*.jsx",
    ),
}


class DriftError(ValueError):
    pass


def _files(root: Path, patterns: tuple[str, ...]) -> list[Path]:
    found: set[Path] = set()
    for pattern in patterns:
        found.update(path for path in root.glob(pattern) if path.is_file() and not path.is_symlink())
    return sorted(found)


def inventory(root: Path) -> dict:
    groups: dict[str, dict[str, str]] = {}
    for name, patterns in GROUPS.items():
        files = _files(root, patterns)
        if not files:
            raise DriftError(f"{name}:empty_inventory")
        groups[name] = {
            path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in files
        }
    return {"schemaVersion": 1, "algorithm": "sha256", "groups": groups}


def validate(root: Path, lock_path: Path) -> dict:
    try:
        expected = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DriftError("lock:invalid") from exc
    actual = inventory(root)
    if expected != actual:
        findings: list[str] = []
        expected_groups = expected.get("groups", {}) if isinstance(expected, dict) else {}
        for group, actual_files in actual["groups"].items():
            expected_files = expected_groups.get(group, {})
            for path in sorted(set(actual_files) | set(expected_files)):
                if path not in expected_files:
                    findings.append(f"{group}:unlocked:{path}")
                elif path not in actual_files:
                    findings.append(f"{group}:missing:{path}")
                elif actual_files[path] != expected_files[path]:
                    findings.append(f"{group}:stale:{path}")
        raise DriftError(";".join(findings or ["lock:shape_mismatch"]))
    return {
        "status": "passed",
        "groupCount": len(actual["groups"]),
        "fileCount": sum(len(value) for value in actual["groups"].values()),
        "findings": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--lock", type=Path)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    lock = (args.lock or root / "scripts/config/surface-drift-v1.json").resolve()
    if args.write:
        if lock.is_symlink():
            raise DriftError("lock:symlink_forbidden")
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text(json.dumps(inventory(root), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"status": "written", "path": str(lock)}))
        return 0
    try:
        result = validate(root, lock)
    except DriftError as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
