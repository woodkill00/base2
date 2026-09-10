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
            try:
                details = os.fstat(child)
                if not stat.S_ISDIR(details.st_mode) or details.st_uid != os.geteuid():
                    raise ValueError("unsafe_lock_parent")
                os.fchmod(child, 0o700)
            except Exception:
                os.close(child)
                raise
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
    busy_exit: int,
    ready_fd: int | None = None,
) -> int:
    parent_fd, name = private_parent(lock_path, trusted_root)
    descriptor = None
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
            raise ValueError("unsafe_lock_member")
        os.fchmod(descriptor, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return busy_exit
        if ready_fd is not None:
            os.write(ready_fd, b"ready\n")
        environment = dict(os.environ)
        environment["BASE2_SECURE_LOCK_FD"] = str(descriptor)
        return subprocess.run(
            command, env=environment, pass_fds=(descriptor,), check=False
        ).returncode
    finally:
        if descriptor is not None:
            with suppress(OSError):
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)
        os.close(parent_fd)


def verify_locked_fd(lock_path: Path, trusted_root: Path, descriptor: int) -> None:
    parent_fd, name = private_parent(lock_path, trusted_root)
    try:
        expected = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        actual = os.fstat(descriptor)
        if (
            not stat.S_ISREG(actual.st_mode)
            or actual.st_uid != os.geteuid()
            or actual.st_nlink != 1
            or stat.S_IMODE(actual.st_mode) != 0o600
            or (actual.st_dev, actual.st_ino) != (expected.st_dev, expected.st_ino)
        ):
            raise ValueError("invalid_inherited_lock_capability")
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally:
        os.close(parent_fd)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", required=True, type=Path)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--busy-exit", type=int, default=3)
    parser.add_argument("--ready-fd", type=int)
    parser.add_argument("--verify-fd", type=int)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if args.verify_fd is None and not command:
        parser.error("a fixed command is required after --")
    try:
        if args.verify_fd is not None:
            if command:
                parser.error("--verify-fd does not accept a command")
            verify_locked_fd(args.lock, args.root, args.verify_fd)
            return 0
        return run_locked(
            args.lock,
            args.root,
            command,
            busy_exit=args.busy_exit,
            ready_fd=args.ready_fd,
        )
    except (OSError, ValueError) as exc:
        print(f"ERROR: secure lock admission failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
