#!/usr/bin/env python3
"""Create or repair Traefik ACME storage without replacing certificate data."""

from __future__ import annotations

import argparse
import json
import os
import stat
from pathlib import Path
from typing import Any

FILES = ("acme.json", "acme-staging.json")


class AcmeBootstrapError(RuntimeError):
    """Raised when ACME storage cannot be made safe without ambiguity."""


def ownership_change_required(metadata: Any, *, uid: int, gid: int) -> bool:
    return metadata.st_uid != uid or metadata.st_gid != gid


def _entry_state(path: Path) -> tuple[int, int, int] | None:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return None
    return (stat.S_IMODE(metadata.st_mode), metadata.st_uid, metadata.st_gid)


def _set_contract(path: Path, *, mode: int, uid: int, gid: int) -> bool:
    before = _entry_state(path)
    os.chmod(path, mode, follow_symlinks=False)
    metadata = path.stat(follow_symlinks=False)
    if ownership_change_required(metadata, uid=uid, gid=gid):
        os.chown(path, uid, gid, follow_symlinks=False)
    after = _entry_state(path)
    return before != after


def bootstrap_acme(directory: str | Path, *, uid: int, gid: int) -> dict[str, Any]:
    if uid < 0 or gid < 0:
        raise AcmeBootstrapError("uid and gid must be non-negative")
    target = Path(directory).expanduser().absolute()
    if target.is_symlink():
        raise AcmeBootstrapError("ACME storage directory must not be a symlink")
    if target.exists() and not target.is_dir():
        raise AcmeBootstrapError("ACME storage path is not a directory")

    changed = not target.exists()
    target.mkdir(parents=True, mode=0o700, exist_ok=True)
    changed = _set_contract(target, mode=0o700, uid=uid, gid=gid) or changed

    file_states: list[dict[str, Any]] = []
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    for name in FILES:
        path = target / name
        if path.is_symlink():
            raise AcmeBootstrapError(f"{name} must not be a symlink")
        if path.exists() and not path.is_file():
            raise AcmeBootstrapError(f"{name} is not a regular file")
        existed = path.exists()
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | nofollow, 0o600)
        except OSError as exc:
            raise AcmeBootstrapError(f"cannot safely open {name}") from exc
        os.close(descriptor)
        changed = (not existed) or _set_contract(path, mode=0o600, uid=uid, gid=gid) or changed
        metadata = path.stat(follow_symlinks=False)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or ownership_change_required(metadata, uid=uid, gid=gid)
        ):
            raise AcmeBootstrapError(f"{name} contract verification failed")
        file_states.append({"name": name, "mode": "0600", "uid": uid, "gid": gid})

    directory_metadata = target.stat(follow_symlinks=False)
    if stat.S_IMODE(directory_metadata.st_mode) != 0o700 or ownership_change_required(
        directory_metadata, uid=uid, gid=gid
    ):
        raise AcmeBootstrapError("ACME storage directory contract verification failed")
    return {
        "schemaVersion": 1,
        "status": "ready",
        "directory": str(target),
        "directoryMode": "0700",
        "uid": uid,
        "gid": gid,
        "changed": changed,
        "files": file_states,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True)
    parser.add_argument("--uid", type=int, default=1000)
    parser.add_argument("--gid", type=int, default=1000)
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        result = bootstrap_acme(args.directory, uid=args.uid, gid=args.gid)
    except AcmeBootstrapError as exc:
        print(f"ACME bootstrap: FAILED ({exc})")
        return 1
    if args.output:
        Path(args.output).write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(f"ACME bootstrap: READY (changed={str(result['changed']).lower()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
