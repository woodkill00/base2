from __future__ import annotations

import copy
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from scripts.python.content_workspace_recovery import RecoveryError, create_bundle, restore_bundle

ROOT = Path(__file__).resolve().parents[2]


def snapshot():
    definition = {"id": "definition-1", "typeKey": "article", "version": 1}
    record = {
        "id": "record-1",
        "definitionId": "definition-1",
        "schemaVersion": 1,
        "values": {"title": "Synthetic"},
    }
    return {
        "schemaVersion": 1,
        "siteId": "site-a",
        "collections": {
            "definitions": [definition],
            "fields": [{"id": "field-1", "definitionId": "definition-1"}],
            "workflows": [{"id": "workflow-1", "definitionId": "definition-1"}],
            "records": [record],
            "versions": [{"id": "version-1", "recordId": "record-1", "sha256": "a" * 64}],
            "relationships": [
                {"id": "relationship-1", "sourceId": "record-1", "targetId": "record-1"}
            ],
            "views": [{"id": "view-1", "typeKey": "article"}],
            "importJobs": [{"id": "import-1", "definitionId": "definition-1"}],
            "exportJobs": [{"id": "export-1", "definitionId": "definition-1"}],
            "auditReferences": [{"id": "audit-1", "objectRef": "record-1"}],
            "assets": [{"id": "asset-1", "sha256": "b" * 64}],
            "assetBindings": [{"id": "binding-1", "recordId": "record-1", "assetId": "asset-1"}],
        },
    }


def test_encrypted_bundle_covers_every_workspace_member_and_restores_exactly(tmp_path):
    source = snapshot()
    key = Fernet.generate_key().decode()
    bundle = create_bundle(source, key)
    assert set(bundle) == {"manifest", "ciphertext"}
    assert "Synthetic" not in bundle["ciphertext"]
    assert set(bundle["manifest"]["inventory"]) == set(source["collections"])
    target = tmp_path / "isolated" / "snapshot.json"
    receipt = restore_bundle(bundle, key, target=target)
    assert receipt["status"] == "restored"
    assert target.stat().st_mode & 0o077 == 0
    assert __import__("json").loads(target.read_text()) == source


def test_restore_rejects_existing_live_tampered_and_referentially_invalid_targets(tmp_path):
    key = Fernet.generate_key().decode()
    bundle = create_bundle(snapshot(), key)
    existing = tmp_path / "existing.json"
    existing.write_text("live")
    with pytest.raises(RecoveryError, match="target_unsafe"):
        restore_bundle(bundle, key, target=existing)
    with pytest.raises(RecoveryError, match="target_unsafe"):
        restore_bundle(
            bundle, key, target=tmp_path / "live" / "restore.json", live_roots=(tmp_path / "live",)
        )
    tampered = copy.deepcopy(bundle)
    tampered["manifest"]["byteSize"] += 1
    with pytest.raises(RecoveryError, match="manifest_integrity_failed"):
        restore_bundle(tampered, key, target=tmp_path / "tampered.json")
    invalid = snapshot()
    invalid["collections"]["records"][0]["definitionId"] = "missing"
    with pytest.raises(RecoveryError, match="definition_reference_invalid"):
        create_bundle(invalid, key)


def test_restore_replay_and_wrong_key_fail_closed_without_output(tmp_path):
    key = Fernet.generate_key().decode()
    bundle = create_bundle(snapshot(), key)
    target = tmp_path / "restore.json"
    restore_bundle(bundle, key, target=target)
    with pytest.raises(RecoveryError, match="target_unsafe"):
        restore_bundle(bundle, key, target=target)
    wrong_target = tmp_path / "wrong.json"
    with pytest.raises(RecoveryError, match="ciphertext_integrity_failed"):
        restore_bundle(bundle, Fernet.generate_key().decode(), target=wrong_target)
    assert not wrong_target.exists()


def test_operator_entrypoints_use_fixed_script_and_no_command_evaluation():
    bash = (ROOT / "scripts/bash/content-workspace-recovery.sh").read_text()
    powershell = (ROOT / "scripts/powershell/content-workspace-recovery.ps1").read_text()
    assert 'exec "$root/.venv-api/bin/python"' in bash
    assert "eval" not in bash and "Invoke-Expression" not in powershell
    assert "ValidateSet('backup','restore')" in powershell
    assert "CONTENT_WORKSPACE_RECOVERY_KEY" not in bash + powershell
