#!/usr/bin/env python3
"""Run one fixed command while holding a no-follow private file lock."""

from __future__ import annotations

import argparse
import fcntl
import os
import stat
import subprocess
import sys
from contextlib import suppress
from pathlib import Path


def private_parent(path: Path, trusted_root: Path) -> tuple[int, str]:
    root = Path(os.path.abspath(trusted_root))
    candidate = Path(os.path.abspath(path))
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("lock_outside_trusted_root") from exc
    if len(relative.parts) < 2 or any(part in {"", ".", ".."} for part in relative.parts):
        raise ValueError("invalid_lock_path")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    descriptor = os.open(root, flags)
    try:
        for part in relative.parts[:-1]:
            with suppress(FileExistsError):
                os.mkdir(part, 0o700, dir_fd=descriptor)
            child = os.open(part, flags, dir_fd=descriptor)
            details = os.fstat(child)
            if not stat.S_ISDIR(details.st_mode) or details.st_uid != os.geteuid():
                os.close(child)
                raise ValueError("unsafe_lock_parent")
            os.fchmod(child, 0o700)
            os.close(descriptor)
            descriptor = child
        return descriptor, relative.parts[-1]
    except Exception:
        os.close(descriptor)
        raise


def run_locked(
    lock_path: Path,
    trusted_root: Path,
    command: list[str],
    *,
    held_environment: str,
    busy_exit: int,
    ready_fd: int | None = None,
) -> int:
    parent_fd, name = private_parent(lock_path, trusted_root)
    try:
        descriptor = os.open(
            name,
            os.O_CREAT | os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW,
            0o600,
            dir_fd=parent_fd,
        )
        details = os.fstat(descriptor)
        if (
            not stat.S_ISREG(details.st_mode)
            or details.st_uid != os.geteuid()
            or details.st_nlink != 1
        ):
            os.close(descriptor)
            raise ValueError("unsafe_lock_member")
        os.fchmod(descriptor, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(descriptor)
            return busy_exit
        if ready_fd is not None:
            os.write(ready_fd, b"ready\n")
        environment = dict(os.environ)
        environment[held_environment] = "1"
        try:
            return subprocess.run(command, env=environment, check=False).returncode
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)
    finally:
        os.close(parent_fd)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", required=True, type=Path)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--held-environment", required=True)
    parser.add_argument("--busy-exit", type=int, default=3)
    parser.add_argument("--ready-fd", type=int)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("a fixed command is required after --")
    try:
        return run_locked(
            args.lock,
            args.root,
            command,
            held_environment=args.held_environment,
            busy_exit=args.busy_exit,
            ready_fd=args.ready_fd,
        )
    except (OSError, ValueError) as exc:
        print(f"ERROR: secure lock admission failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
