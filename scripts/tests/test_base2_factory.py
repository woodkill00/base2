import copy
import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from scripts.python.base2_upgrade_advisor import UpgradeDenied, advise
from scripts.python.create_base2_site import FactoryError, generate, load_profile
from scripts.python.validate_generated_site import ChildGateError, validate


ROOT=Path(__file__).parents[2]


def tree_digest(root):
    digest=hashlib.sha256()
    for path in sorted(item for item in root.rglob('*') if item.is_file()):
        digest.update(str(path.relative_to(root)).encode()+b'\0'+path.read_bytes())
    return digest.hexdigest()


class Base2FactoryTests(unittest.TestCase):
    def test_three_profiles_generate_distinct_deterministic_children_and_pass_gate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); digests=[]; inventories=[]
            for name in ('blog-portfolio','saas','marketplace'):
                first=root/f'{name}-a'; second=root/f'{name}-b'; profile=ROOT/f'factory_profiles/{name}.json'
                one=generate(profile_path=profile,output=first); two=generate(profile_path=profile,output=second)
                self.assertEqual(one,two); self.assertEqual(tree_digest(first),tree_digest(second))
                result=validate(first); self.assertEqual('passed',result['status']); self.assertEqual(0,result['executedInputCommands'])
                digests.append(tree_digest(first)); inventories.append(tuple(one['moduleInventory']))
            self.assertEqual(3,len(set(digests))); self.assertEqual(3,len(set(inventories)))

    def test_generation_uses_exact_commit_and_excludes_worktree_untracked_git_cache_logs_receipts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); untracked=ROOT/'factory-untracked-sentinel.txt'; untracked.write_text('must-not-export')
            try:
                child=root/'child'; provenance=generate(profile_path=ROOT/'factory_profiles/blog-portfolio.json',output=child)
                self.assertEqual(subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),provenance['baseCommit'])
                self.assertFalse((child/untracked.name).exists()); self.assertFalse((child/'.git').exists()); validate(child)
                with self.assertRaisesRegex(FactoryError,'output_must_be_absent'): generate(profile_path=ROOT/'factory_profiles/blog-portfolio.json',output=child)
            finally: untracked.unlink(missing_ok=True)

    def test_hostile_profiles_fail_before_output(self):
        base=json.loads((ROOT/'factory_profiles/blog-portfolio.json').read_text())
        mutations=[dict(base,id='../escape'),dict(base,modules=['../bad']),dict(base,secretRefs=['plaintext']),dict(base,owner='bad owner')]
        with tempfile.TemporaryDirectory() as temporary:
            for index,payload in enumerate(mutations):
                path=Path(temporary)/f'p{index}.json'; path.write_text(json.dumps(payload))
                with self.assertRaises(FactoryError): load_profile(path)

    def test_interrupted_archive_removes_partial_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            output=Path(temporary)/'child'
            with patch('scripts.python.create_base2_site._archive',side_effect=FactoryError('interrupted')):
                with self.assertRaisesRegex(FactoryError,'interrupted'):
                    generate(profile_path=ROOT/'factory_profiles/blog-portfolio.json',output=output)
            self.assertFalse(output.exists())

    def test_bash_and_powershell_wrappers_have_argument_parity(self):
        bash=(ROOT/'scripts/create-base2-site.sh').read_text()
        powershell=(ROOT/'scripts/create-base2-site.ps1').read_text()
        self.assertIn('create_base2_site.py',bash); self.assertIn('"$@"',bash)
        self.assertIn('create_base2_site.py',powershell); self.assertIn('@args',powershell)

    def test_upgrade_advisor_blocks_incompatible_and_never_applies(self):
        with tempfile.TemporaryDirectory() as temporary:
            child=Path(temporary)/'child'; generate(profile_path=ROOT/'factory_profiles/saas.json',output=child)
            profile=json.loads((child/'factory-profile.json').read_text())
            compatible={name:['1.0.0'] for name in profile['modules']}
            before=tree_digest(child); result=advise(child_root=child,target_commit='f'*40,available_modules=compatible)
            self.assertEqual('compatible',result['status']); self.assertFalse(any(result['authority'].values())); self.assertEqual(before,tree_digest(child))
            compatible['support']=[]; self.assertEqual('blocked',advise(child_root=child,target_commit='f'*40,available_modules=compatible)['status'])
            with self.assertRaisesRegex(UpgradeDenied,'commit'): advise(child_root=child,target_commit='../bad',available_modules=compatible)


if __name__=='__main__': unittest.main()
