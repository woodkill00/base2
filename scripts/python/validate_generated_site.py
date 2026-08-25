#!/usr/bin/env python3
"""Applicable complete gate for a generated Base2 child repository."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.python.module_registry import ModuleRegistry


class ChildGateError(ValueError): pass


def validate(root: Path) -> dict:
    if root.is_symlink() or not root.is_dir() or (root/'.git').exists(): raise ChildGateError('child:unsafe_root')
    required=['.base2-child.json','.base2-provenance.json','factory-profile.json','README.md','LICENSE','NOTICE','SECURITY.md','.github/CODEOWNERS','.github/BRANCH_PROTECTION.md','.github/dependabot.yml','secret-refs.json']
    if any(not (root/name).is_file() for name in required): raise ChildGateError('child:governance_missing')
    child=json.loads((root/'.base2-child.json').read_text()); provenance=json.loads((root/'.base2-provenance.json').read_text()); profile=json.loads((root/'factory-profile.json').read_text()); refs=json.loads((root/'secret-refs.json').read_text())
    if child.get('id')!=provenance.get('childId') or profile.get('id')!=provenance.get('profileId'): raise ChildGateError('child:identity_mismatch')
    if provenance.get('sourceMode')!='git-archive-exact-commit' or not re.fullmatch(r'[0-9a-f]{40}',provenance.get('baseCommit','')): raise ChildGateError('child:provenance_invalid')
    modules=[json.loads(path.read_text()) for path in sorted((root/'modules').glob('*/module.json'))]
    plan=ModuleRegistry(modules).install_plan()
    if sorted(item['id'] for item in plan)!=sorted(profile['modules']): raise ChildGateError('child:module_inventory_mismatch')
    if refs.get('refs')!=profile['secretRefs'] or any(not item.startswith('vaultwarden://') for item in refs['refs']): raise ChildGateError('child:secret_ref_invalid')
    forbidden={'.artifacts','.git','node_modules','.venv','.venv-api','.venv-django','local_run_logs','test-results','__pycache__'}
    for path in root.rglob('*'):
        relative=path.relative_to(root)
        if set(relative.parts)&forbidden or path.name.endswith(('.log','.pyc')) or 'receipt' in path.name.lower(): raise ChildGateError(f'child:forbidden_artifact:{relative}')
    digest=hashlib.sha256(json.dumps({'child':child,'provenance':provenance,'modules':[item['id'] for item in plan]},sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {'status':'passed','childId':child['id'],'baseCommit':provenance['baseCommit'],'moduleCount':len(modules),'governanceFiles':len(required),'digest':digest,'executedInputCommands':0,'providerCalls':0,'credentialReads':0}


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument('root',type=Path); args=parser.parse_args(); print(json.dumps(validate(args.root),sort_keys=True)); return 0


if __name__=='__main__': raise SystemExit(main())
