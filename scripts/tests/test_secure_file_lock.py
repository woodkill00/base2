from __future__ import annotations

import fcntl
import importlib.util
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from stat import S_IMODE
from unittest.mock import patch

MODULE_PATH = Path(__file__).parents[1] / "python" / "secure_file_lock.py"


def load_module():
    spec = importlib.util.spec_from_file_location("secure_file_lock", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SecureFileLockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = load_module()

    def test_fixed_command_runs_with_private_regular_lock(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lock_path = root / ".artifacts" / "test.lock"
            verification = (
                f"{shlex.quote(sys.executable)} {shlex.quote(str(MODULE_PATH))} "
                f"--lock {shlex.quote(str(lock_path))} --root {shlex.quote(str(root))} "
                '--verify-fd "$BASE2_SECURE_LOCK_FD"'
            )
            result = self.lock.run_locked(
                lock_path,
                root,
                ["/bin/sh", "-c", verification],
                busy_exit=3,
            )
            self.assertEqual(0, result)
            self.assertTrue(lock_path.is_file())
            self.assertEqual(0o700, S_IMODE(lock_path.parent.stat().st_mode))
            self.assertEqual(0o600, S_IMODE(lock_path.stat().st_mode))

    def test_symlink_lock_is_rejected_without_target_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifacts = root / ".artifacts"
            artifacts.mkdir()
            target = root / "target"
            target.write_text("preserve", encoding="utf-8")
            (artifacts / "test.lock").symlink_to(target)
            with self.assertRaises(OSError):
                self.lock.run_locked(
                    artifacts / "test.lock",
                    root,
                    ["/bin/true"],
                    busy_exit=3,
                )
            self.assertEqual("preserve", target.read_text(encoding="utf-8"))
            self.assertEqual(0o644, S_IMODE(target.stat().st_mode))

    def test_symlink_parent_is_rejected_without_external_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root / "outside"
            outside.mkdir()
            (root / ".artifacts").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(OSError):
                self.lock.run_locked(
                    root / ".artifacts" / "test.lock",
                    root,
                    ["/bin/true"],
                    busy_exit=3,
                )
            self.assertEqual([], list(outside.iterdir()))

    def test_hardlink_lock_is_rejected_without_target_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifacts = root / ".artifacts"
            artifacts.mkdir()
            target = root / "target"
            target.write_text("preserve", encoding="utf-8")
            os.link(target, artifacts / "test.lock")
            with self.assertRaisesRegex(ValueError, "unsafe_lock_member"):
                self.lock.run_locked(
                    artifacts / "test.lock",
                    root,
                    ["/bin/true"],
                    busy_exit=3,
                )
            self.assertEqual("preserve", target.read_text(encoding="utf-8"))
            self.assertEqual(0o644, S_IMODE(target.stat().st_mode))

    def test_readiness_uses_inherited_pipe_not_a_fixed_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            read_fd, write_fd = os.pipe()
            try:
                result = self.lock.run_locked(
                    root / ".artifacts" / "test.lock",
                    root,
                    ["/bin/true"],
                    busy_exit=3,
                    ready_fd=write_fd,
                )
                os.close(write_fd)
                write_fd = -1
                self.assertEqual(0, result)
                self.assertEqual(b"ready\n", os.read(read_fd, 32))
                self.assertFalse((root / ".artifacts" / "lock-ready").exists())
            finally:
                os.close(read_fd)
                if write_fd >= 0:
                    os.close(write_fd)

    def test_forged_legacy_environment_cannot_bypass_held_runner_lock(self):
        repo_root = MODULE_PATH.parents[2]
        runner = repo_root / "scripts/bash/e2e-isolated.sh"
        artifacts = repo_root / ".artifacts"
        artifacts.mkdir(mode=0o700, exist_ok=True)
        os.chmod(artifacts, 0o700)
        lock_path = artifacts / "e2e-isolated.lock"
        descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            os.fchmod(descriptor, 0o600)
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            completed = subprocess.run(
                ["bash", str(runner)],
                env={**os.environ, "BASE2_E2E_LOCK_HELD": "1"},
                text=True,
                capture_output=True,
                check=False,
                timeout=10,
            )
            self.assertEqual(3, completed.returncode)
            self.assertIn("already in use", completed.stderr)
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    def test_ready_write_failure_releases_descriptor_and_lock(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lock_path = root / ".artifacts" / "test.lock"
            before = len(os.listdir("/proc/self/fd"))
            with patch.object(
                self.lock.os, "write", side_effect=OSError("fixture write failure")
            ), self.assertRaises(OSError):
                self.lock.run_locked(
                    lock_path,
                    root,
                    ["/bin/true"],
                    busy_exit=3,
                    ready_fd=99,
                )
            self.assertEqual(before, len(os.listdir("/proc/self/fd")))
            self.assertEqual(
                0,
                self.lock.run_locked(lock_path, root, ["/bin/true"], busy_exit=3),
            )

    def test_member_fstat_failure_releases_descriptor_and_parent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lock_path = root / ".artifacts" / "test.lock"
            parent_fd, _ = self.lock.private_parent(lock_path, root)
            os.close(parent_fd)
            before = len(os.listdir("/proc/self/fd"))
            real_fstat = self.lock.os.fstat
            calls = 0

            def fail_member(descriptor):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("fixture fstat failure")
                return real_fstat(descriptor)

            with patch.object(self.lock.os, "fstat", side_effect=fail_member), self.assertRaisesRegex(
                OSError, "fixture fstat failure"
            ):
                self.lock.run_locked(lock_path, root, ["/bin/true"], busy_exit=3)
            self.assertEqual(before, len(os.listdir("/proc/self/fd")))

    def test_member_fchmod_failure_releases_descriptor_and_parent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifacts = root / ".artifacts"
            artifacts.mkdir(mode=0o700)
            lock_path = artifacts / "test.lock"
            before = len(os.listdir("/proc/self/fd"))
            real_fchmod = self.lock.os.fchmod
            calls = 0

            def fail_member(descriptor, mode):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("fixture fchmod failure")
                return real_fchmod(descriptor, mode)

            with patch.object(
                self.lock.os, "fchmod", side_effect=fail_member
            ), self.assertRaisesRegex(OSError, "fixture fchmod failure"):
                self.lock.run_locked(lock_path, root, ["/bin/true"], busy_exit=3)
            self.assertEqual(before, len(os.listdir("/proc/self/fd")))

    def test_body_rejects_wrong_inode_capability_before_docker(self):
        repo_root = MODULE_PATH.parents[2]
        body = repo_root / "scripts/bash/e2e-isolated-body.sh"
        descriptor = os.open("/dev/null", os.O_RDONLY)
        try:
            completed = subprocess.run(
                ["bash", str(body)],
                env={**os.environ, "BASE2_SECURE_LOCK_FD": str(descriptor)},
                pass_fds=(descriptor,),
                text=True,
                capture_output=True,
                check=False,
                timeout=10,
            )
            self.assertEqual(2, completed.returncode)
            self.assertIn("secure lock admission failed", completed.stderr)
        finally:
            os.close(descriptor)

    def test_body_rejects_separate_same_inode_fd_while_owner_holds_lock(self):
        repo_root = MODULE_PATH.parents[2]
        body = repo_root / "scripts/bash/e2e-isolated-body.sh"
        artifacts = repo_root / ".artifacts"
        artifacts.mkdir(mode=0o700, exist_ok=True)
        os.chmod(artifacts, 0o700)
        lock_path = artifacts / "e2e-isolated.lock"
        owner = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        challenger = os.open(lock_path, os.O_RDWR | os.O_NOFOLLOW)
        try:
            os.fchmod(owner, 0o600)
            fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
            completed = subprocess.run(
                ["bash", str(body)],
                env={**os.environ, "BASE2_SECURE_LOCK_FD": str(challenger)},
                pass_fds=(challenger,),
                text=True,
                capture_output=True,
                check=False,
                timeout=10,
            )
            self.assertEqual(2, completed.returncode)
            self.assertIn("secure lock admission failed", completed.stderr)
        finally:
            fcntl.flock(owner, fcntl.LOCK_UN)
            os.close(challenger)
            os.close(owner)

    def test_subprocess_setup_failure_releases_descriptor_and_lock(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lock_path = root / ".artifacts" / "test.lock"
            before = len(os.listdir("/proc/self/fd"))
            with patch.object(
                self.lock.subprocess, "run", side_effect=OSError("fixture child failure")
            ), self.assertRaisesRegex(OSError, "fixture child failure"):
                self.lock.run_locked(lock_path, root, ["/bin/true"], busy_exit=3)
            self.assertEqual(before, len(os.listdir("/proc/self/fd")))
            self.assertEqual(
                0,
                self.lock.run_locked(lock_path, root, ["/bin/true"], busy_exit=3),
            )

    def test_flock_setup_failure_releases_descriptor_and_parent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lock_path = root / ".artifacts" / "test.lock"
            before = len(os.listdir("/proc/self/fd"))
            with patch.object(
                self.lock.fcntl, "flock", side_effect=OSError("fixture flock failure")
            ), self.assertRaisesRegex(OSError, "fixture flock failure"):
                self.lock.run_locked(lock_path, root, ["/bin/true"], busy_exit=3)
            self.assertEqual(before, len(os.listdir("/proc/self/fd")))
            self.assertEqual(
                0,
                self.lock.run_locked(lock_path, root, ["/bin/true"], busy_exit=3),
            )


if __name__ == "__main__":
    unittest.main()
