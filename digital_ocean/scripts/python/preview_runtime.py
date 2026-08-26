#!/usr/bin/env python3
"""Credential-free native WSL runtime admission for Base2 preview operations."""

from __future__ import annotations

import hashlib
import os
import platform
import re
import shutil
from collections.abc import Callable
from pathlib import Path

TOOLS = ("python3", "node", "npm", "git", "ssh", "docker")
WINDOWS_PATH = re.compile(r"(?:^[A-Za-z]:[\\/]|^\\\\|/mnt/[a-z]/|\.exe$)", re.IGNORECASE)


class RuntimeAdmissionError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _binary_class(path: Path) -> str:
    try:
        prefix = path.read_bytes()[:128]
    except OSError as exc:
        raise RuntimeAdmissionError(
            "RUNTIME_TOOL_UNREADABLE", f"tool is unreadable: {path.name}"
        ) from exc
    if prefix.startswith(b"\x7fELF"):
        return "linux-elf"
    if prefix.startswith(b"#!"):
        line = prefix.splitlines()[0].decode("utf-8", "replace")
        if "powershell" in line.casefold() or "cmd.exe" in line.casefold():
            raise RuntimeAdmissionError(
                "RUNTIME_WINDOWS_TOOL", f"Windows tool rejected: {path.name}"
            )
        return "linux-script"
    raise RuntimeAdmissionError(
        "RUNTIME_TOOL_INVALID", f"tool is not a Linux executable: {path.name}"
    )


def _tool_receipt(name: str, raw_path: str) -> dict:
    if WINDOWS_PATH.search(raw_path.replace("\\", "/")):
        raise RuntimeAdmissionError("RUNTIME_WINDOWS_TOOL", f"Windows tool rejected: {name}")
    path = Path(raw_path)
    if path.is_symlink():
        path = path.resolve(strict=True)
    elif not path.is_file():
        raise RuntimeAdmissionError("RUNTIME_TOOL_MISSING", f"tool is unavailable: {name}")
    resolved = str(path)
    if WINDOWS_PATH.search(resolved.replace("\\", "/")):
        raise RuntimeAdmissionError("RUNTIME_WINDOWS_TOOL", f"Windows tool rejected: {name}")
    return {
        "name": name,
        "path": resolved,
        "binaryClass": _binary_class(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def inspect_runtime(
    repo: str | os.PathLike[str],
    *,
    which: Callable[[str], str | None] = shutil.which,
    proc_version: str | None = None,
    machine: str | None = None,
    tool_paths: dict[str, str] | None = None,
) -> dict:
    raw_repo = str(repo)
    if WINDOWS_PATH.search(raw_repo.replace("\\", "/")):
        raise RuntimeAdmissionError(
            "RUNTIME_NON_WSL_REPOSITORY", "repository must be stored in WSL"
        )
    candidate = Path(raw_repo)
    if candidate.is_symlink() or not candidate.is_dir():
        raise RuntimeAdmissionError(
            "RUNTIME_NON_WSL_REPOSITORY", "repository must be a real directory"
        )
    resolved_repo = candidate.resolve(strict=True)
    if not str(resolved_repo).startswith("/home/"):
        raise RuntimeAdmissionError(
            "RUNTIME_NON_WSL_REPOSITORY", "repository must be stored under /home"
        )
    version = proc_version
    if version is None:
        try:
            version = Path("/proc/version").read_text(encoding="utf-8")
        except OSError:
            version = ""
    if "microsoft" not in version.casefold() and not os.environ.get("WSL_DISTRO_NAME"):
        raise RuntimeAdmissionError("RUNTIME_NOT_WSL", "preview operations require WSL")
    architecture = machine or platform.machine()
    if architecture not in {"x86_64", "aarch64"}:
        raise RuntimeAdmissionError("RUNTIME_ARCH_INVALID", "unsupported Linux architecture")
    receipts = []
    for name in TOOLS:
        raw = (tool_paths or {}).get(name) if tool_paths is not None else which(name)
        if not raw:
            raise RuntimeAdmissionError("RUNTIME_TOOL_MISSING", f"tool is unavailable: {name}")
        receipts.append(_tool_receipt(name, raw))
    return {
        "schemaVersion": 1,
        "ok": True,
        "code": "OK",
        "repository": str(resolved_repo),
        "runtime": "wsl-linux",
        "architecture": architecture,
        "tools": receipts,
        "credentialReads": 0,
        "secretValuesEmitted": 0,
    }
