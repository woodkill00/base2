import json
import tempfile
import unittest
from pathlib import Path

from scripts.python.classify_gate_runtime_failure import classify


class GateRuntimeRecoveryTests(unittest.TestCase):
    def evidence(self, root: Path, logs: dict[str, str]):
        checks=[]
        for check_id,text in logs.items():
            name=f'{check_id}.log'; (root/name).write_text(text)
            checks.append({'id':check_id,'status':'failed','artifact':name})
        path=root/'result.json'; path.write_text(json.dumps({'overallStatus':'failed','sourceCommit':'a'*40,'checks':checks}))
        return path

    def test_all_native_corruption_is_recoverable_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=self.evidence(Path(temporary),{'api':'Fatal Python error: Segmentation fault','django':'=== attempt 1 exit -11 ==='})
            result=classify(path)
            self.assertTrue(result['nativeCorruption'])
            self.assertEqual(['api','django'],result['nativeFailedChecks'])

    def test_product_or_mixed_failure_never_authorizes_restart(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=self.evidence(Path(temporary),{'api':'AssertionError: expected 2 got 3'})
            self.assertFalse(classify(path)['nativeCorruption'])
        with tempfile.TemporaryDirectory() as temporary:
            path=self.evidence(Path(temporary),{'api':'Fatal Python error: Segmentation fault','policy':'secret scan found a token'})
            result=classify(path)
            self.assertFalse(result['nativeCorruption']); self.assertEqual(['policy'],result['nonNativeFailedChecks'])

    def test_windows_launcher_is_bounded_and_exact_commit_bound(self):
        source=(Path(__file__).parents[2]/'scripts/run-complete-gate-wsl.ps1').read_text()
        self.assertIn('$attempt -le 2',source)
        self.assertEqual(1,source.count('wsl.exe --shutdown'))
        self.assertIn('$currentCommit -ne $initialCommit',source)
        self.assertIn('$classificationExit -ne 75',source)
        self.assertIn('Tracked or staged changes must be committed',source)


if __name__=='__main__': unittest.main()
