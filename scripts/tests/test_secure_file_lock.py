from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from stat import S_IMODE

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
            result = self.lock.run_locked(
                lock_path,
                root,
                ["/bin/sh", "-c", 'test "$LOCK_HELD" = 1'],
                held_environment="LOCK_HELD",
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
                    held_environment="LOCK_HELD",
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
                    held_environment="LOCK_HELD",
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
                    held_environment="LOCK_HELD",
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
                    held_environment="LOCK_HELD",
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


if __name__ == "__main__":
    unittest.main()
