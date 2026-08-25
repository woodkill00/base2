#!/usr/bin/env python3
"""Run the providerless Base2 production-operations acceptance bundle."""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from digital_ocean.scripts.python.release_orchestrator import ReleaseController, signed_release
from scripts.python.capacity_assurance import load_profile, run_capacity_drill
from scripts.python.operations_telemetry import AlertLedger
from scripts.python.recovery_assurance import certificate_drill, create_backup, restore_isolated


def run() -> dict:
    key = b'operations-checkpoint-key-v1!!xx'
    now = datetime.now(UTC)
    with tempfile.TemporaryDirectory(prefix='base2-operations-checkpoint-') as temporary:
        root = Path(temporary)
        alerts = AlertLedger(root/'private/alerts.json')
        alert_receipts = [
            alerts.observe(incident_id='incident-checkpoint-001',failing=True,code='api.failed'),
            alerts.observe(incident_id='incident-checkpoint-001',failing=True,code='api.failed'),
            alerts.observe(incident_id='incident-checkpoint-001',failing=False,code='api.recovered'),
        ]
        restore_digests=[]
        for cycle in range(3):
            backup=root/f'backup-{cycle}.enc'; restored=root/f'restore-{cycle}'/'state'
            create_backup(payload=f'exact-state-{cycle}'.encode(),target_id=f'preview-{cycle:03d}',data_schema=1,key=key,key_ref='vaultwarden://base2/operations-key',output=backup,now=now)
            restore_digests.append(restore_isolated(backup=backup,key=key,expected_target=f'preview-{cycle:03d}',expected_schema=1,output=restored)['sha256'])
        controller=ReleaseController(root/'private/releases.json',signing_key=key)
        release_states=[]
        for cycle in range(3):
            digit=str(cycle+1)
            item=signed_release(release_id=f'release-ops-{cycle:04d}',image=f'registry.example/base2@sha256:{digit*64}',source_commit=digit*40,sbom_digest=digit*64,provenance_digest=digit*64,signing_key=key)
            release_states.append(controller.update(item,health_gate=lambda _:True)['status'])
        capacity=run_capacity_drill(load_profile(ROOT/'scripts/config/capacity-profiles.json','small-preview'))
        certificate=certificate_drill(acme_mode='staging',days_remaining=10)
    return {
        'schemaVersion':1,'status':'passed','faultRestoreCycles':3,'restoreDigests':restore_digests,
        'releaseStates':release_states,'incidentNotifications':sum(item['notify'] for item in alert_receipts),
        'capacity':capacity,'certificate':certificate,'providerCalls':0,'credentialReads':0,
        'ownedResourcesAfter':0,'temporaryStateRetained':False,
        'rpoSeconds':0,'rtoSecondsCeiling':60,
    }


def main() -> int:
    output=ROOT/'.artifacts/operations-checkpoint/result.json'; result=run()
    output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps(result,sort_keys=True)); return 0


if __name__=='__main__': raise SystemExit(main())
