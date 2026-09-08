import base64
import json
import subprocess
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from api.services.content_workspace_storage import PrivateArtifactStore
from scripts.python.production_backup import (
    ProductionBackupError,
    _repeatable_read_snapshot,
    _verify_object_references,
    create_production_backup,
    isolated_restore,
    load_config,
    prune_owned_backups,
    restore_database_isolated,
    verify_receipt,
)


def test_exported_snapshot_uses_a_second_connection_for_the_post_capture_fence():
    connections = []

    class Cursor:
        def __init__(self, index):
            self.index = index
            self.query = ''

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, query):
            self.query = query

        def fetchone(self):
            if 'pg_export_snapshot' in self.query:
                return ('snapshot-1',)
            return (31,)

        def __iter__(self):
            digest = 'a' * 64 if self.index == 0 else 'b' * 64
            return iter([('asset', 'tenant-one', 'media/tenant-one/photo', digest)])

    class Connection:
        def __init__(self, index):
            self.index = index
            self.closed = False

        def set_session(self, **_kwargs):
            pass

        def cursor(self):
            return Cursor(self.index)

        def rollback(self):
            pass

        def close(self):
            self.closed = True

    def connect(_config):
        connection = Connection(len(connections))
        connections.append(connection)
        return connection

    config = {'pgService': 'base2_backup', 'pgServiceFile': '/private/pg.conf'}
    with (
        patch('scripts.python.production_backup._connect_pg_service', side_effect=connect),
        _repeatable_read_snapshot(config) as snapshot,
    ):
        assert '\t' + 'a' * 64 in snapshot['references']
        assert '\t' + 'b' * 64 in snapshot['afterReferences']()
    assert len(connections) == 2
    assert all(connection.closed for connection in connections)


def _config(tmp_path: Path):
    objects = tmp_path / "objects"
    artifact = PrivateArtifactStore(objects, key=b"c" * 32).put(
        namespace="media",
        site_id="tenant-one",
        object_id="photo",
        content=b"actual-object-payload",
    )
    service = tmp_path / "pg_service.conf"
    service.write_text("[base2_backup]\nhost=db\n", encoding="utf-8")
    service.chmod(0o600)
    return {
        "schemaVersion": 1,
        "targetId": "base2-backup",
        "dataSchema": 31,
        "pgServiceFile": str(service),
        "pgService": "base2_backup",
        "objectRoot": str(objects),
        "objectStorageKeyFile": str(tmp_path / "object.key"),
        "backupRoot": str(tmp_path / "backups"),
        "receiptRoot": str(tmp_path / "receipts"),
        "encryptionKeyFile": str(tmp_path / "backup.key"),
        "keyRef": "vaultwarden://base2/production-backup-v1",
        "retentionDays": 30,
        "maximumBackups": 3,
        "operationsReceiptRoot": str(tmp_path / "operations"),
        "operationsReceiptKeyFile": str(tmp_path / "operations.key"),
        "sourceCommit": "a" * 40,
        "_key": b"k" * 32,
        "_operations_key": b"o" * 32,
        "_object_key": b"c" * 32,
        "_test_object_key": artifact.object_key,
        "_test_object_digest": artifact.sha256,
    }


def _runner(command, **kwargs):
    del kwargs
    if command[0] == "psql":
        query = command[-1]
        output = (
            "31\n"
            if "django_migrations" in query
            else "asset:tenant-one:media/tenant-one/photo.bin:"
            + "8caedbe1351cc6ace7e341d8e75f6c1c47cd831f6d6e78a045e6ecfef27b1c3a\n"
        )
        return subprocess.CompletedProcess(command, 0, output, "")
    output = Path(command[command.index("--file") + 1])
    output.write_bytes(b"PGDUMP\x00production-schema-and-data")
    return subprocess.CompletedProcess(command, 0, "", "")


def test_config_requires_owner_only_external_secret_files(tmp_path):
    config = _config(tmp_path)
    key_file = Path(config["encryptionKeyFile"])
    key_file.write_text(base64.urlsafe_b64encode(b"k" * 32).decode(), encoding="ascii")
    key_file.chmod(0o600)
    operations_key_file = Path(config["operationsReceiptKeyFile"])
    operations_key_file.write_text(base64.urlsafe_b64encode(b"o" * 32).decode(), encoding="ascii")
    operations_key_file.chmod(0o600)
    object_key_file = Path(config["objectStorageKeyFile"])
    object_key_file.write_text(base64.urlsafe_b64encode(b"c" * 32).decode(), encoding="ascii")
    object_key_file.chmod(0o600)
    public = {name: value for name, value in config.items() if not name.startswith("_")}
    config_file = tmp_path / "backup.json"
    config_file.write_text(json.dumps(public), encoding="utf-8")
    config_file.chmod(0o600)
    loaded = load_config(config_file)
    assert loaded["_key"] == b"k" * 32
    assert loaded["_operations_key"] == b"o" * 32
    assert loaded["_object_key"] == b"c" * 32
    key_file.chmod(0o644)
    with pytest.raises(ProductionBackupError, match="private_file_invalid"):
        load_config(config_file)


def test_real_dump_and_object_payload_are_encrypted_verified_and_restorable(tmp_path):
    config = _config(tmp_path)
    now = datetime(2026, 9, 8, tzinfo=UTC)
    receipt = create_production_backup(config, now=now, runner=_runner)
    backup = verify_receipt(receipt, key=config["_key"], backup_root=Path(config["backupRoot"]))
    receipt_path = next(Path(config["receiptRoot"]).glob("*.json"))
    restored = isolated_restore(
        config, receipt_path=receipt_path, restore_root=tmp_path / "isolated-restore"
    )
    assert backup.is_file() and restored["objectCount"] == 1
    assert (Path(config["operationsReceiptRoot"]) / "backup.json").is_file()
    assert Path(restored["databaseDump"]).read_bytes().startswith(b"PGDUMP")
    restored_store = PrivateArtifactStore(Path(restored["objectRoot"]), key=b"c" * 32)
    assert (
        restored_store.get(
            config["_test_object_key"], expected_sha256=config["_test_object_digest"]
        )
        == b"actual-object-payload"
    )


def test_database_object_references_require_exact_decryptable_payload(tmp_path):
    root = tmp_path / "objects"
    store = PrivateArtifactStore(root, key=b"c" * 32)
    artifact = store.put(
        namespace="media", site_id="tenant-one", object_id="photo", content=b"payload"
    )
    ledger = f"asset:tenant-one:{artifact.object_key}:{artifact.sha256}\n"
    _verify_object_references(ledger, object_root=root, key=b"c" * 32)
    with pytest.raises(ProductionBackupError, match="digest_mismatch"):
        _verify_object_references(ledger[:-65] + ("0" * 64) + "\n", object_root=root, key=b"c" * 32)
    (root / artifact.object_key).unlink()
    with pytest.raises(ProductionBackupError, match="referenced_object_missing"):
        _verify_object_references(ledger, object_root=root, key=b"c" * 32)


def test_database_object_reconciliation_rejects_unreferenced_files(tmp_path):
    root = tmp_path / "objects"
    root.mkdir()
    (root / "orphan.bin").write_bytes(b"unreferenced")
    with pytest.raises(ProductionBackupError, match="object_inventory_mismatch"):
        _verify_object_references("", object_root=root, key=b"c" * 32)


def test_retention_deletes_only_verified_owned_expired_artifacts(tmp_path):
    config = _config(tmp_path)
    now = datetime(2026, 1, 1, tzinfo=UTC)
    create_production_backup(config, now=now, runner=_runner)
    unrelated = Path(config["backupRoot"]) / "do-not-touch.bin"
    unrelated.write_bytes(b"unowned")
    result = prune_owned_backups(config, now=now + timedelta(days=31))
    assert result == {"verified": 1, "removed": 1, "rejected": 0, "orphaned": 0}
    assert unrelated.read_bytes() == b"unowned"


def test_tampered_receipt_cannot_delete_or_restore(tmp_path):
    config = _config(tmp_path)
    receipt = create_production_backup(config, now=datetime(2026, 9, 8, tzinfo=UTC), runner=_runner)
    receipt["backupFile"] = "../outside"
    with pytest.raises(ProductionBackupError, match="receipt_invalid"):
        verify_receipt(receipt, key=config["_key"], backup_root=Path(config["backupRoot"]))


def test_invalid_receipts_and_exact_owned_orphans_are_quarantined(tmp_path):
    config = _config(tmp_path)
    create_production_backup(config, now=datetime(2026, 9, 8, tzinfo=UTC), runner=_runner)
    receipt_path = next(Path(config["receiptRoot"]).glob("*.json"))
    receipt_path.write_text('{"tampered":true}\n', encoding="utf-8")
    result = prune_owned_backups(config, now=datetime(2026, 9, 9, tzinfo=UTC))
    assert result == {"verified": 0, "removed": 0, "rejected": 1, "orphaned": 1}
    quarantine = Path(config["backupRoot"]) / "quarantine"
    assert len(list(quarantine.glob("rejected-receipt-*.json"))) == 1
    assert len(list(quarantine.glob("orphan-backup-*.tar.enc"))) == 1


def test_quarantine_capacity_fails_closed_without_deleting_excess_unknown_files(tmp_path):
    config = _config(tmp_path)
    receipts = Path(config["receiptRoot"])
    receipts.mkdir()
    for index in range(11):
        path = receipts / f"base2-backup-20260908T0000{index:02d}Z.json"
        path.write_text(json.dumps({"invalid": index}) + "\n", encoding="utf-8")
        path.chmod(0o600)
    with pytest.raises(ProductionBackupError, match="quarantine_capacity_exceeded"):
        prune_owned_backups(config, now=datetime(2026, 9, 8, tzinfo=UTC))
    quarantine = Path(config["backupRoot"]) / "quarantine"
    assert len(list(quarantine.glob("rejected-receipt-*.json"))) == 10
    assert len(list(receipts.glob("*.json"))) == 1


def test_backup_refuses_configuration_schema_that_differs_from_live_ledger(tmp_path):
    config = _config(tmp_path)

    def stale_ledger(command, **kwargs):
        if command[0] == "psql":
            return subprocess.CompletedProcess(command, 0, "28\n", "")
        return _runner(command, **kwargs)

    with pytest.raises(ProductionBackupError, match="schema_mismatch"):
        create_production_backup(config, now=datetime(2026, 9, 8, tzinfo=UTC), runner=stale_ledger)


def test_backup_archives_only_a_private_single_read_object_snapshot(tmp_path):
    config = _config(tmp_path)
    captured = {}
    from scripts.python import production_backup

    real_bundle = production_backup.create_database_object_bundle

    def observe_bundle(**kwargs):
        captured["root"] = kwargs["object_root"]
        assert kwargs["object_root"] != Path(config["objectRoot"])
        assert kwargs["object_root"].parent.name.startswith("base2-production-backup-")
        return real_bundle(**kwargs)

    with patch.object(production_backup, "create_database_object_bundle", observe_bundle):
        create_production_backup(config, now=datetime(2026, 9, 8, tzinfo=UTC), runner=_runner)
    assert not captured["root"].exists()


def test_backup_never_follows_live_object_symlinks(tmp_path):
    config = _config(tmp_path)
    outside = tmp_path / "outside-secret"
    outside.write_bytes(b"must-not-be-archived")
    (Path(config["objectRoot"]) / "unsafe-link").symlink_to(outside)
    with pytest.raises(ProductionBackupError, match="object_symlink_denied"):
        create_production_backup(config, now=datetime(2026, 9, 8, tzinfo=UTC), runner=_runner)
    assert not list(Path(config["backupRoot"]).glob("*.tar.enc"))


def test_backup_removes_output_when_cross_surface_reference_ledger_changes(tmp_path):
    config = _config(tmp_path)
    calls = {"references": 0}

    def changing_ledger(command, **kwargs):
        if command[0] == "psql" and "SELECT kind" in command[-1]:
            calls["references"] += 1
            value = _runner(command).stdout if calls["references"] == 1 else "changed"
            return subprocess.CompletedProcess(command, 0, value, "")
        return _runner(command, **kwargs)

    with pytest.raises(ProductionBackupError, match="cross_surface_snapshot_changed"):
        create_production_backup(
            config, now=datetime(2026, 9, 8, tzinfo=UTC), runner=changing_ledger
        )
    assert not list(Path(config["backupRoot"]).glob("*.tar.enc"))


def test_backup_rejects_aba_even_when_the_reference_ledger_returns_to_the_same_value(tmp_path):
    config = _config(tmp_path)
    fences = iter(["101:102:", "101:104:"])

    def aba_runner(command, **kwargs):
        if command[0] == "psql" and "txid_current_snapshot" in command[-1]:
            return subprocess.CompletedProcess(command, 0, next(fences) + "\n", "")
        return _runner(command, **kwargs)

    with pytest.raises(ProductionBackupError, match="cross_surface_snapshot_changed"):
        create_production_backup(config, now=datetime(2026, 9, 8, tzinfo=UTC), runner=aba_runner)
    assert not list(Path(config["backupRoot"]).glob("*.tar.enc"))


def test_backup_binds_pg_dump_and_reference_ledger_to_one_exported_snapshot(tmp_path):
    config = _config(tmp_path)
    commands = []
    references = _runner(["psql", "SELECT kind"]).stdout

    def recording_runner(command, **kwargs):
        commands.append(command)
        return _runner(command, **kwargs)

    @contextmanager
    def snapshot_factory(_config):
        yield {
            "id": "00000003-1",
            "references": references,
            "schema": 31,
            "afterReferences": lambda: references,
        }

    create_production_backup(
        config,
        now=datetime(2026, 9, 8, tzinfo=UTC),
        runner=recording_runner,
        snapshot_factory=snapshot_factory,
    )
    dump_command = next(command for command in commands if command[0] == "pg_dump")
    assert dump_command[dump_command.index("--snapshot") + 1] == "00000003-1"
    assert not any(command[0] == "psql" for command in commands)


def test_database_restore_requires_exact_empty_isolated_database(tmp_path):
    config = _config(tmp_path)
    create_production_backup(config, now=datetime(2026, 9, 8, tzinfo=UTC), runner=_runner)
    receipt_path = next(Path(config["receiptRoot"]).glob("*.json"))
    restore_service = tmp_path / "restore-pg-service.conf"
    restore_service.write_text("[base2_restore]\nhost=restore-db\n", encoding="utf-8")
    restore_service.chmod(0o600)
    reference_ledger = _runner(["psql", "SELECT kind"]).stdout
    responses = iter(["base2_restore_trial\n", "0\n", "", "3\n", "31\n", reference_ledger])

    def restore_runner(command, **kwargs):
        del kwargs
        return subprocess.CompletedProcess(command, 0, next(responses), "")

    result = restore_database_isolated(
        config,
        receipt_path=receipt_path,
        restore_root=tmp_path / "database-restore",
        pg_service_file=restore_service,
        pg_service="base2_restore",
        expected_database="base2_restore_trial",
        runner=restore_runner,
    )
    assert result["databaseRestoreExecuted"] is True
    assert result["databaseTableCount"] == 3
    assert (Path(config["operationsReceiptRoot"]) / "restore.json").is_file()
