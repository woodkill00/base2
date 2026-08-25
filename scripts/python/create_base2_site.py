#!/usr/bin/env python3
"""Generate an independent Base2 child from an exact immutable Git commit."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
GENERATOR_VERSION = '1.0.0'
PROFILE_KEYS = {'schemaVersion','id','name','description','modules','owner','license','secretRefs'}
ID = re.compile(r'^[a-z][a-z0-9-]{2,62}$')
MODULE = re.compile(r'^[a-z][a-z0-9-]{1,62}$')
OWNER = re.compile(r'^@[A-Za-z0-9][A-Za-z0-9_-]{1,38}$')
SECRET_REF = re.compile(r'^vaultwarden://[A-Za-z0-9][A-Za-z0-9._/-]{2,254}$')
SECRET = re.compile(r'(?i)(?:api[_-]?key|token|password|secret)\s*[=:]\s*["\']?[A-Za-z0-9+/_.-]{16,}')
EXCLUDED_PARTS = {'.git','.artifacts','.venv','.venv-api','.venv-django','node_modules','__pycache__','.pytest_cache','.ruff_cache','local_run_logs','test-results','coverage'}


class FactoryError(ValueError):
    pass


def _run(args: list[str], *, cwd: Path = ROOT) -> str:
    completed=subprocess.run(args,cwd=cwd,text=True,capture_output=True,check=False)
    if completed.returncode:
        raise FactoryError('factory:git_failed')
    return completed.stdout.strip()


def load_profile(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 65536:
        raise FactoryError('profile:unsafe_path')
    try: value=json.loads(path.read_text(encoding='utf-8'))
    except (OSError,UnicodeError,json.JSONDecodeError) as exc: raise FactoryError('profile:invalid_json') from exc
    if not isinstance(value,dict) or set(value)!=PROFILE_KEYS or value.get('schemaVersion')!=1:
        raise FactoryError('profile:invalid_fields')
    if not ID.fullmatch(value.get('id','')) or not isinstance(value.get('name'),str) or not 3<=len(value['name'])<=120 or not isinstance(value.get('description'),str) or not 10<=len(value['description'])<=500:
        raise FactoryError('profile:identity_invalid')
    modules=value.get('modules'); refs=value.get('secretRefs')
    if not isinstance(modules,list) or not modules or len(modules)!=len(set(modules)) or any(not isinstance(x,str) or not MODULE.fullmatch(x) for x in modules):
        raise FactoryError('profile:modules_invalid')
    if not OWNER.fullmatch(value.get('owner','')) or value.get('license') not in {'UNLICENSED','MIT','Apache-2.0'}:
        raise FactoryError('profile:governance_invalid')
    if not isinstance(refs,list) or len(refs)!=len(set(refs)) or any(not isinstance(x,str) or not SECRET_REF.fullmatch(x) for x in refs):
        raise FactoryError('profile:secret_refs_invalid')
    for module in modules:
        if not (ROOT/'modules'/module/'module.json').is_file(): raise FactoryError(f'profile:module_unknown:{module}')
    return value


def _safe_member(name: str) -> bool:
    path=PurePosixPath(name)
    return not path.is_absolute() and '..' not in path.parts and not set(path.parts)&EXCLUDED_PARTS and not name.endswith(('.log','.pyc')) and 'receipt' not in name.lower()


def _archive(commit: str, target: Path) -> None:
    completed=subprocess.run(['git','archive','--format=tar',commit],cwd=ROOT,capture_output=True,check=False)
    if completed.returncode: raise FactoryError('factory:archive_failed')
    with tarfile.open(fileobj=io.BytesIO(completed.stdout),mode='r:') as archive:
        for member in archive.getmembers():
            if not _safe_member(member.name): continue
            if member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
                raise FactoryError('factory:archive_member_unsafe')
            destination=(target/member.name).resolve()
            if target.resolve() not in destination.parents and destination!=target.resolve(): raise FactoryError('factory:archive_traversal')
            if member.isdir(): destination.mkdir(parents=True,exist_ok=True); continue
            destination.parent.mkdir(parents=True,exist_ok=True)
            source=archive.extractfile(member)
            if source is None: raise FactoryError('factory:archive_member_invalid')
            destination.write_bytes(source.read())
            os.chmod(destination, member.mode & 0o755)


def generate(*, profile_path: Path, output: Path, commit: str = 'HEAD') -> dict[str, Any]:
    profile=load_profile(profile_path)
    exact=_run(['git','rev-parse','--verify',f'{commit}^{{commit}}'])
    if not re.fullmatch(r'[0-9a-f]{40}',exact): raise FactoryError('factory:commit_invalid')
    tree=_run(['git','show','-s','--format=%T',exact])
    if output.exists() or output.is_symlink(): raise FactoryError('factory:output_must_be_absent')
    output.parent.mkdir(parents=True,exist_ok=True)
    temporary=Path(tempfile.mkdtemp(prefix=f'.{output.name}.',dir=output.parent))
    try:
        _archive(exact,temporary)
        for module_dir in (temporary/'modules').iterdir():
            if module_dir.is_dir() and module_dir.name not in profile['modules']: shutil.rmtree(module_dir)
        if any(not (temporary/'modules'/module/'module.json').is_file() for module in profile['modules']):
            raise FactoryError('factory:module_missing_from_commit')
        profile_digest=hashlib.sha256(json.dumps(profile,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        provenance={'schemaVersion':1,'generatorVersion':GENERATOR_VERSION,'baseCommit':exact,'baseTree':tree,'profileId':profile['id'],'profileDigest':profile_digest,'childId':f'base2-child-{profile["id"]}','moduleInventory':profile['modules'],'transformations':['filter-modules','write-child-identity','write-governance'],'sourceMode':'git-archive-exact-commit'}
        (temporary/'.base2-child.json').write_text(json.dumps({'schemaVersion':1,'id':provenance['childId'],'name':profile['name'],'description':profile['description'],'baseVersion':'2.0.0'},sort_keys=True,indent=2)+'\n')
        (temporary/'.base2-provenance.json').write_text(json.dumps(provenance,sort_keys=True,indent=2)+'\n')
        (temporary/'factory-profile.json').write_text(json.dumps(profile,sort_keys=True,indent=2)+'\n')
        (temporary/'README.md').write_text(f'# {profile["name"]}\n\n{profile["description"]}\n\nGenerated from Base2 commit `{exact}`. Provider activation and deployment require separate approval.\n')
        (temporary/'LICENSE').write_text(profile['license']+'\n')
        (temporary/'NOTICE').write_text(f'{profile["name"]} derives from Base2; see .base2-provenance.json.\n')
        (temporary/'SECURITY.md').write_text('Report vulnerabilities privately to the repository owner. Never include secrets in an issue.\n')
        (temporary/'.github').mkdir(exist_ok=True)
        (temporary/'.github/CODEOWNERS').write_text(f'* {profile["owner"]}\n')
        (temporary/'.github/BRANCH_PROTECTION.md').write_text('Require pull requests, required generated-child gate checks, resolved review, and non-force updates on the default branch.\n')
        dependabot={'version':2,'updates':[{'package-ecosystem':'npm','directory':'/react-app','schedule':{'interval':'weekly'}},{'package-ecosystem':'pip','directory':'/api','schedule':{'interval':'weekly'}}]}
        (temporary/'.github/dependabot.yml').write_text(json.dumps(dependabot,sort_keys=True,indent=2)+'\n')
        (temporary/'secret-refs.json').write_text(json.dumps({'schemaVersion':1,'refs':profile['secretRefs']},sort_keys=True,indent=2)+'\n')
        generated_paths = [
            temporary/'.base2-child.json', temporary/'.base2-provenance.json',
            temporary/'factory-profile.json', temporary/'README.md', temporary/'LICENSE',
            temporary/'NOTICE', temporary/'SECURITY.md', temporary/'.github/CODEOWNERS',
            temporary/'.github/BRANCH_PROTECTION.md', temporary/'.github/dependabot.yml',
            temporary/'secret-refs.json',
        ]
        for path in generated_paths:
            if SECRET.search(path.read_text(encoding='utf-8')):
                raise FactoryError(f'factory:secret_detected:{path.relative_to(temporary)}')
        os.replace(temporary,output)
    except Exception:
        shutil.rmtree(temporary,ignore_errors=True); shutil.rmtree(output,ignore_errors=True); raise
    return provenance


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument('--profile',type=Path,required=True); parser.add_argument('--output',type=Path,required=True); parser.add_argument('--commit',default='HEAD')
    args=parser.parse_args(); print(json.dumps(generate(profile_path=args.profile,output=args.output,commit=args.commit),sort_keys=True)); return 0


if __name__=='__main__': raise SystemExit(main())
