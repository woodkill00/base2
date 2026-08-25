#!/usr/bin/env python3
"""Build an exact generated-child archive and approval-bound live preview plan."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from digital_ocean.scripts.python.live_canary_preflight import binding_digest, build_plan
from scripts.python.create_base2_site import generate


def _tree_digest(root:Path)->str:
    digest=hashlib.sha256()
    for path in sorted(item for item in root.rglob('*') if item.is_file()):
        digest.update(str(path.relative_to(root)).encode()+b'\0'+path.read_bytes())
    return digest.hexdigest()


def _archive(root:Path,output:Path)->str:
    with tarfile.open(output,'w') as archive:
        for path in sorted(root.rglob('*')):
            relative=path.relative_to(root)
            info=archive.gettarinfo(str(path),arcname=str(relative))
            info.uid=info.gid=0; info.uname=info.gname='root'; info.mtime=0
            if path.is_file():
                with path.open('rb') as stream: archive.addfile(info,stream)
            elif path.is_dir(): archive.addfile(info)
            else: raise ValueError('child archive contains unsafe type')
    os.chmod(output,0o600); return hashlib.sha256(output.read_bytes()).hexdigest()


def build(*,env_path:Path,profile_path:Path,output_dir:Path)->dict:
    if output_dir.exists(): raise ValueError('output directory must be absent')
    output_dir.mkdir(parents=True,mode=0o700)
    child=output_dir/'child'; provenance=generate(profile_path=profile_path,output=child)
    archive=output_dir/'source.tar'; archive_digest=_archive(child,archive)
    plan=build_plan(env_path,ROOT)
    label=f'f093-child-{provenance["baseCommit"][:8]}'
    plan.update({
        'sourceArchiveSha256':archive_digest,
        'dropletName':f'{plan["projectName"]}-{label}',
        'ownershipNamespace':f'base2-{label}',
        'dnsMutations':[{'name':label,'type':'A','fqdn':f'{label}.{plan["dnsZone"]}'}],
        'certificateSans':[f'{label}.{plan["dnsZone"]}'],
    })
    binding={key:plan[key] for key in ('sourceCommit','sourceArchiveSha256','projectName','providerProjectId','region','size','image','dropletName','ownershipNamespace','dnsZone','dnsMutations','certificateSans','trialCount','maximumConcurrentDroplets','leaseMinutesPerTrial','totalCostCeilingMinorUnits','hourlyCostMinorUnitsCeiling','currency','certificateMode')}
    plan['planDigest']=binding_digest(binding)
    plan.update({'childProfile':provenance['profileId'],'childId':provenance['childId'],'childTreeDigest':_tree_digest(child),'stateMode':'encrypted-snapshot-restore-required','approvalScope':'three-sequential-generated-child-deploy-verify-destroy-trials'})
    (output_dir/'plan.json').write_text(json.dumps(plan,sort_keys=True,indent=2)+'\n'); os.chmod(output_dir/'plan.json',0o600)
    shutil.rmtree(child)
    return plan


def main()->int:
    parser=argparse.ArgumentParser(); parser.add_argument('--env-path',type=Path,required=True); parser.add_argument('--profile',type=Path,required=True); parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args(); print(json.dumps(build(env_path=args.env_path,profile_path=args.profile,output_dir=args.output_dir),sort_keys=True)); return 0


if __name__=='__main__': raise SystemExit(main())
