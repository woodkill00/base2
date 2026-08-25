#!/usr/bin/env python3
"""Generate review-only child upgrade advice without applying or publishing it."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class UpgradeDenied(ValueError): pass


def advise(*, child_root: Path, target_commit: str, available_modules: dict[str,list[str]]) -> dict[str,Any]:
    if not child_root.is_dir() or child_root.is_symlink(): raise UpgradeDenied('upgrade:child_invalid')
    child=json.loads((child_root/'.base2-child.json').read_text()); provenance=json.loads((child_root/'.base2-provenance.json').read_text()); profile=json.loads((child_root/'factory-profile.json').read_text())
    if len(target_commit)!=40 or any(ch not in '0123456789abcdef' for ch in target_commit): raise UpgradeDenied('upgrade:commit_invalid')
    incompatible=[]
    for module in profile['modules']:
        versions=available_modules.get(module,[])
        if '1.0.0' not in versions: incompatible.append(module)
    status='blocked' if incompatible else 'compatible'
    patch={'schemaVersion':1,'childId':child['id'],'fromCommit':provenance['baseCommit'],'toCommit':target_commit,'status':status,'incompatibleModules':sorted(incompatible),'actions':['regenerate-from-exact-commit','run-child-gate','owner-review'],'authority':{'applied':False,'pushed':False,'merged':False,'deployed':False}}
    patch['digest']=hashlib.sha256(json.dumps(patch,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return patch
