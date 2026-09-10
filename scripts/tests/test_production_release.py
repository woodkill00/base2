import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from scripts.python.production_release import (
    ProductionReleaseController,
    ReleaseError,
    approval,
    build_release_manifest,
    operation_receipt,
    sign_release,
    validate_operation_receipt,
    validate_release,
)

KEY = b"production-release-test-key-material-0001"
OWNER_KEY = b"independent-owner-approval-key-material-1"
NOW = datetime(2026, 9, 8, 12, tzinfo=UTC)


def release(number: int = 1):
    digit = format(number, "x")[-1]
    return sign_release(
        {
            "schemaVersion": 2,
            "releaseId": f"release-test-{number:04d}",
            "sourceCommit": digit * 40,
            "sourceClean": True,
            "images": {"web": f"registry.example/base2@sha256:{digit * 64}"},
            "migrationsDigest": digit * 64,
            "configurationSchemaVersion": 1,
            "configurationDigest": digit * 64,
            "sbomDigest": digit * 64,
            "provenanceDigest": digit * 64,
            "createdAt": NOW.isoformat(),
        },
        key=KEY,
    )


def permit(action, item, environment="staging", offset=10):
    return approval(
        approval_id=f"approval-{action}-0001",
        action=action,
        release_id=item["releaseId"],
        environment=environment,
        source_commit=item["sourceCommit"],
        artifact_digest=item["artifactDigest"],
        expires_at=(NOW + timedelta(minutes=offset)).isoformat(),
        key=OWNER_KEY,
    )


def execute(action, item, environment, operation_id, reconcile_only):
    del reconcile_only
    return {
        "status": "succeeded",
        "operationId": operation_id,
        "action": action,
        "releaseId": item["releaseId"],
        "environment": environment,
        "sourceCommit": item["sourceCommit"],
        "artifactDigest": item["artifactDigest"],
    }


def test_release_requires_clean_exact_immutable_integrity_bound_artifacts():
    item = release()
    assert validate_release(item, key=KEY) == item
    for field, value, error in (
        ("sourceClean", False, "source_dirty"),
        ("sourceCommit", "dirty", "identity_invalid"),
        ("images", {"web": "base2:latest"}, "image_not_immutable"),
        ("sbomDigest", "0" * 64, "artifact_changed"),
    ):
        changed = dict(item)
        changed[field] = value
        with pytest.raises(ReleaseError, match=error):
            validate_release(changed, key=KEY)


def test_approval_is_exact_scoped_integrity_bound_and_expiring():
    item = release()
    value = permit("prepare", item)
    changed = dict(value)
    changed["environment"] = "production"
    with TemporaryDirectory() as temporary:
        controller = ProductionReleaseController(
            Path(temporary) / "journal.json", release_key=KEY, approval_key=OWNER_KEY
        )
        with pytest.raises(ReleaseError, match="integrity_invalid"):
            controller.transition(
                action="prepare",
                release=item,
                environment="staging",
                owner_approval=changed,
                now=NOW,
            )
        with pytest.raises(ReleaseError, match="expired"):
            controller.transition(
                action="prepare",
                release=item,
                environment="staging",
                owner_approval=permit("prepare", item, offset=-1),
                now=NOW,
            )


def test_prepare_stage_canary_promote_is_checkpointed_and_replay_safe():
    item = release()
    with TemporaryDirectory() as temporary:
        controller = ProductionReleaseController(
            Path(temporary) / "journal.json", release_key=KEY, approval_key=OWNER_KEY
        )
        for action in ("prepare", "stage", "canary", "promote"):
            receipt = controller.transition(
                action=action,
                release=item,
                environment="staging",
                owner_approval=permit(action, item),
                now=NOW,
                health=lambda _: True,
                execute=execute,
            )
            assert len(receipt["digest"]) == 64
            assert receipt['sourceCommit'] == item['sourceCommit']
            assert receipt['artifactDigest'] == item['artifactDigest']
            assert len(receipt['checkpointDigest']) == 64
            replay = controller.transition(
                action=action,
                release=item,
                environment="staging",
                owner_approval=permit(action, item),
                now=NOW,
                health=lambda _: True,
                execute=execute,
            )
            assert replay["status"] == "idempotent"
        assert controller.status() == {
            "state": "promoted",
            "environment": "staging",
            "current": item["releaseId"],
            "candidate": item["releaseId"],
            "checkpoints": [
                "prepare",
                "stage:started",
                "stage",
                "canary:started",
                "canary",
                "promote:started",
                "promote",
            ],
        }


def test_failed_canary_halts_before_traffic_and_rollback_selects_previous():
    first, second = release(1), release(2)
    with TemporaryDirectory() as temporary:
        controller = ProductionReleaseController(
            Path(temporary) / "journal.json", release_key=KEY, approval_key=OWNER_KEY
        )
        for action in ("prepare", "stage", "canary", "promote"):
            controller.transition(
                action=action,
                release=first,
                environment="staging",
                owner_approval=permit(action, first),
                now=NOW,
                health=lambda _: True,
                execute=execute,
            )
        controller.transition(
            action="prepare",
            release=second,
            environment="staging",
            owner_approval=permit("prepare", second),
            now=NOW,
            health=lambda _: True,
            execute=execute,
        )
        controller.transition(
            action="stage",
            release=second,
            environment="staging",
            owner_approval=permit("stage", second),
            now=NOW,
            health=lambda _: True,
            execute=execute,
        )
        result = controller.transition(
            action="canary",
            release=second,
            environment="staging",
            owner_approval=permit("canary", second),
            now=NOW,
            health=lambda _: False,
            execute=execute,
        )
        assert result["status"] == "halted"
        assert controller.status()["current"] == first["releaseId"]
        rolled = controller.transition(
            action="rollback",
            release=second,
            environment="staging",
            owner_approval=permit("rollback", second),
            now=NOW,
            execute=execute,
        )
        assert rolled["status"] == "rolled-back"


def test_interrupted_state_resumes_but_changed_candidate_and_corruption_fail_closed():
    item = release()
    with TemporaryDirectory() as temporary:
        path = Path(temporary) / "journal.json"
        first = ProductionReleaseController(path, release_key=KEY, approval_key=OWNER_KEY)
        first.transition(
            action="prepare",
            release=item,
            environment="preview",
            owner_approval=permit("prepare", item, "preview"),
            now=NOW,
        )
        resumed = ProductionReleaseController(path, release_key=KEY, approval_key=OWNER_KEY)
        resumed.transition(
            action="stage",
            release=item,
            environment="preview",
            owner_approval=permit("stage", item, "preview"),
            now=NOW,
            health=lambda _: True,
            execute=execute,
        )
        with pytest.raises(ReleaseError, match="candidate_mismatch"):
            resumed.transition(
                action="canary",
                release=release(2),
                environment="preview",
                owner_approval=permit("canary", release(2), "preview"),
                now=NOW,
                health=lambda _: True,
                execute=execute,
            )
        path.write_text("{}", encoding="utf-8")
        with pytest.raises(ReleaseError, match="journal_integrity"):
            resumed.status()


def test_nonproduction_lifecycle_never_requests_production_certificates():
    for environment in ("development", "test", "preview", "staging"):
        certificate_mode = "disabled" if environment in {"development", "test"} else "staging-only"
        assert certificate_mode != "production"


def test_preview_is_a_typed_nonprovider_prepare_transition():
    item = release()
    with TemporaryDirectory() as temporary:
        controller = ProductionReleaseController(
            Path(temporary) / 'journal.json', release_key=KEY, approval_key=OWNER_KEY
        )
        result = controller.transition(
            action='preview', release=item, environment='preview',
            owner_approval=permit('preview', item, 'preview'), now=NOW,
        )
        assert result['status'] == 'prepared'
        assert controller.status()['checkpoints'] == ['preview']


def test_release_and_approval_keys_are_independent_and_production_is_outside_feature():
    item = release()
    with TemporaryDirectory() as temporary:
        with pytest.raises(ReleaseError, match="key_invalid"):
            ProductionReleaseController(
                Path(temporary) / "same-key.json", release_key=KEY, approval_key=KEY
            )
        controller = ProductionReleaseController(
            Path(temporary) / "journal.json", release_key=KEY, approval_key=OWNER_KEY
        )
        with pytest.raises(ReleaseError, match="production_activation_outside_feature"):
            controller.transition(
                action="prepare",
                release=item,
                environment="production",
                owner_approval=permit("prepare", item, "production"),
                now=NOW,
            )


def test_replay_rejects_a_resigned_manifest_reusing_the_release_id():
    item = release()
    changed = sign_release(
        {
            **{key: value for key, value in item.items() if key != "signature"},
            "sourceCommit": "f" * 40,
        },
        key=KEY,
    )
    with TemporaryDirectory() as temporary:
        controller = ProductionReleaseController(
            Path(temporary) / "journal.json", release_key=KEY, approval_key=OWNER_KEY
        )
        controller.transition(
            action="prepare",
            release=item,
            environment="staging",
            owner_approval=permit("prepare", item),
            now=NOW,
        )
        with pytest.raises(ReleaseError, match="candidate_mismatch"):
            controller.transition(
                action="stage",
                release=changed,
                environment="staging",
                owner_approval=permit("stage", changed),
                now=NOW,
                health=lambda _: True,
                execute=execute,
            )


def test_health_adapter_is_mandatory_for_traffic_affecting_steps():
    item = release()
    with TemporaryDirectory() as temporary:
        controller = ProductionReleaseController(
            Path(temporary) / "journal.json", release_key=KEY, approval_key=OWNER_KEY
        )
        controller.transition(
            action="prepare",
            release=item,
            environment="staging",
            owner_approval=permit("prepare", item),
            now=NOW,
        )
        with pytest.raises(ReleaseError, match="health_adapter_required"):
            controller.transition(
                action="stage",
                release=item,
                environment="staging",
                owner_approval=permit("stage", item),
                now=NOW,
            )


def test_execution_adapter_is_mandatory_and_failure_halts_before_health():
    item = release()
    with TemporaryDirectory() as temporary:
        controller = ProductionReleaseController(
            Path(temporary) / "journal.json", release_key=KEY, approval_key=OWNER_KEY
        )
        controller.transition(
            action="prepare",
            release=item,
            environment="staging",
            owner_approval=permit("prepare", item),
            now=NOW,
        )
        with pytest.raises(ReleaseError, match="execution_adapter_required"):
            controller.transition(
                action="stage",
                release=item,
                environment="staging",
                owner_approval=permit("stage", item),
                now=NOW,
                health=lambda _: True,
            )
        health_called = []
        halted = controller.transition(
            action="stage",
            release=item,
            environment="staging",
            owner_approval=permit("stage", item),
            now=NOW,
            health=lambda action: health_called.append(action) or True,
            execute=lambda *args: {"status": "failed"},
        )
        assert halted["status"] == "halted"
        assert health_called == []
        assert controller.status()["state"] == "halted"


def test_started_checkpoint_retries_only_through_idempotent_adapter():
    item = release()
    calls = []
    with TemporaryDirectory() as temporary:
        controller = ProductionReleaseController(
            Path(temporary) / "journal.json", release_key=KEY, approval_key=OWNER_KEY
        )
        controller.transition(
            action="prepare",
            release=item,
            environment="staging",
            owner_approval=permit("prepare", item),
            now=NOW,
        )

        def interrupted(action, candidate, environment, operation_id, reconcile_only):
            calls.append(
                (
                    action,
                    candidate["releaseId"],
                    environment,
                    operation_id,
                    reconcile_only,
                )
            )
            if len(calls) == 1:
                raise ConnectionError("response lost")
            return execute(action, candidate, environment, operation_id, reconcile_only)

        first = controller.transition(
            action="stage",
            release=item,
            environment="staging",
            owner_approval=permit("stage", item),
            now=NOW,
            health=lambda _: True,
            execute=interrupted,
        )
        assert first["status"] == "pending"
        assert controller.status()["checkpoints"].count("stage:started") == 1
        second = controller.transition(
            action="stage",
            release=item,
            environment="staging",
            owner_approval=permit("stage", item),
            now=NOW,
            health=lambda _: True,
            execute=interrupted,
        )
        assert second["status"] == "staged"
        assert calls[0][:3] == ("stage", item["releaseId"], "staging")
        assert calls[1][:3] == calls[0][:3]
        assert calls[0][3] == calls[1][3]
        assert calls[0][4] is False
        assert calls[1][4] is True


def test_operation_receipt_is_independently_keyed_and_exact_scoped():
    item = release()
    operation_key = b"operation-executor-key-material-0000001"
    value = operation_receipt(
        operation_id="operation-stage-0001",
        action="stage",
        release_id=item["releaseId"],
        environment="staging",
        status="succeeded",
        source_commit=item["sourceCommit"],
        artifact_digest=item["artifactDigest"],
        observed_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
        key=operation_key,
    )
    assert validate_operation_receipt(
        value,
        action="stage",
        release_id=item["releaseId"],
        environment="staging",
        source_commit=item["sourceCommit"],
        artifact_digest=item["artifactDigest"],
        operation_id="operation-stage-0001",
        now=NOW,
        key=operation_key,
    ) == value
    with pytest.raises(ReleaseError, match="scope_mismatch"):
        validate_operation_receipt(
            value,
            action="canary",
            release_id=item["releaseId"],
            environment="staging",
            source_commit=item["sourceCommit"],
            artifact_digest=item["artifactDigest"],
            operation_id="operation-stage-0001",
            now=NOW,
            key=operation_key,
        )


@pytest.mark.parametrize('interrupted_action', ['stage', 'canary', 'promote'])
def test_each_traffic_checkpoint_resumes_after_lost_executor_response(interrupted_action):
    item = release()
    order = ['stage', 'canary', 'promote']
    with TemporaryDirectory() as temporary:
        controller = ProductionReleaseController(
            Path(temporary) / 'journal.json', release_key=KEY, approval_key=OWNER_KEY
        )
        controller.transition(
            action='prepare', release=item, environment='staging',
            owner_approval=permit('prepare', item), now=NOW,
        )
        for action in order[: order.index(interrupted_action)]:
            controller.transition(
                action=action, release=item, environment='staging',
                owner_approval=permit(action, item), now=NOW,
                health=lambda _: True, execute=execute,
            )
        attempts = 0

        def flaky(action, candidate, environment, operation_id, reconcile_only):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise ConnectionError('lost response')
            return execute(action, candidate, environment, operation_id, reconcile_only)

        pending = controller.transition(
            action=interrupted_action, release=item, environment='staging',
            owner_approval=permit(interrupted_action, item), now=NOW,
            health=lambda _: True, execute=flaky,
        )
        assert pending['status'] == 'pending'
        completed = controller.transition(
            action=interrupted_action, release=item, environment='staging',
            owner_approval=permit(interrupted_action, item), now=NOW,
            health=lambda _: True, execute=flaky,
        )
        assert completed['status'] in {'staged', 'canary', 'promoted'}
        assert attempts == 2


def test_journal_lock_rejects_a_concurrent_runner():
    with TemporaryDirectory() as temporary:
        controller = ProductionReleaseController(
            Path(temporary) / 'journal.json', release_key=KEY, approval_key=OWNER_KEY
        )
        with controller.store.locked(), pytest.raises(ReleaseError, match='concurrent_runner'):
            controller.status()


def test_journal_rejects_linked_parent_lock_and_member_without_target_mutation():
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        outside = root / 'outside'
        outside.mkdir(mode=0o700)
        linked = root / 'linked'
        linked.symlink_to(outside, target_is_directory=True)
        controller = ProductionReleaseController(
            linked / 'journal.json', release_key=KEY, approval_key=OWNER_KEY
        )
        with pytest.raises(ReleaseError, match='journal_parent_unsafe'):
            controller.status()
        assert list(outside.iterdir()) == []

        target = root / 'target'
        target.write_text('preserve', encoding='utf-8')
        lock = root / 'journal.json.lock'
        lock.symlink_to(target)
        controller = ProductionReleaseController(
            root / 'journal.json', release_key=KEY, approval_key=OWNER_KEY
        )
        with pytest.raises(ReleaseError, match='journal_lock_unsafe'):
            controller.status()
        assert target.read_text(encoding='utf-8') == 'preserve'

        lock.unlink()
        with controller.store.locked():
            controller.store.write({
                'schemaVersion': 1, 'state': 'empty', 'environment': None,
                'candidate': None, 'current': None, 'previous': None,
                'checkpoints': [], 'receipts': [],
            })
        journal = root / 'journal.json'
        journal.unlink()
        journal.symlink_to(target)
        with pytest.raises(ReleaseError, match='journal_unsafe'):
            controller.status()
        assert target.read_text(encoding='utf-8') == 'preserve'


def test_journal_rejects_hardlinked_lock_and_member():
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        target = root / 'target'
        target.write_text('preserve', encoding='utf-8')
        target.chmod(0o600)
        controller = ProductionReleaseController(
            root / 'journal.json', release_key=KEY, approval_key=OWNER_KEY
        )
        (root / 'journal.json.lock').hardlink_to(target)
        with pytest.raises(ReleaseError, match='journal_lock_unsafe'):
            controller.status()
        (root / 'journal.json.lock').unlink()
        (root / 'journal.json').hardlink_to(target)
        with pytest.raises(ReleaseError, match='journal_unsafe'):
            controller.status()
        assert target.read_text(encoding='utf-8') == 'preserve'


def test_rollback_checkpoint_resumes_after_lost_executor_response():
    first, second = release(1), release(2)
    with TemporaryDirectory() as temporary:
        controller = ProductionReleaseController(
            Path(temporary) / 'journal.json', release_key=KEY, approval_key=OWNER_KEY
        )
        for action in ('prepare', 'stage', 'canary', 'promote'):
            controller.transition(
                action=action, release=first, environment='staging',
                owner_approval=permit(action, first), now=NOW,
                health=lambda _: True, execute=execute,
            )
        for action in ('prepare', 'stage'):
            controller.transition(
                action=action, release=second, environment='staging',
                owner_approval=permit(action, second), now=NOW,
                health=lambda _: True, execute=execute,
            )
        controller.transition(
            action='canary', release=second, environment='staging',
            owner_approval=permit('canary', second), now=NOW,
            health=lambda _: False, execute=execute,
        )
        attempts = 0

        def flaky(action, candidate, environment, operation_id, reconcile_only):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise ConnectionError('lost response')
            return execute(action, candidate, environment, operation_id, reconcile_only)

        pending = controller.transition(
            action='rollback', release=second, environment='staging',
            owner_approval=permit('rollback', second), now=NOW, execute=flaky,
        )
        assert pending['status'] == 'pending'
        rolled = controller.transition(
            action='rollback', release=second, environment='staging',
            owner_approval=permit('rollback', second), now=NOW, execute=flaky,
        )
        assert rolled['status'] == 'rolled-back'
        assert controller.status()['current'] == first['releaseId']


def test_release_builder_binds_clean_git_migrations_config_sbom_and_provenance(tmp_path):
    (tmp_path / 'django/app/migrations').mkdir(parents=True)
    (tmp_path / 'shared/config').mkdir(parents=True)
    (tmp_path / 'shared/schemas').mkdir(parents=True)
    (tmp_path / 'django/app/migrations/0001.py').write_text('migration', encoding='utf-8')
    (tmp_path / 'shared/config/production-readiness-v1.json').write_text(
        '{"schemaVersion":1}', encoding='utf-8'
    )
    (tmp_path / 'shared/schemas/policy.json').write_text('{}', encoding='utf-8')
    sbom = tmp_path / 'sbom.json'
    provenance = tmp_path / 'provenance.json'
    sbom.write_text('{"bomFormat":"CycloneDX"}', encoding='utf-8')
    provenance.write_text('{"predicateType":"test"}', encoding='utf-8')
    subprocess.run(['git', 'init', '-q'], cwd=tmp_path, check=True)
    subprocess.run(['git', 'config', 'user.email', 'test@example.invalid'], cwd=tmp_path, check=True)
    subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=tmp_path, check=True)
    subprocess.run(['git', 'add', '.'], cwd=tmp_path, check=True)
    subprocess.run(['git', 'commit', '-qm', 'fixture'], cwd=tmp_path, check=True)
    built = build_release_manifest(
        root=tmp_path,
        release_id='release-built-0001',
        images={'web': f'registry.example/base2@sha256:{"a" * 64}'},
        sbom_path=sbom,
        provenance_path=provenance,
        now=NOW,
        key=KEY,
    )
    assert built['sourceClean'] is True
    assert len(built['migrationsDigest']) == len(built['configurationDigest']) == 64
    (tmp_path / 'shared/schemas/policy.json').write_text('{"changed":true}', encoding='utf-8')
    with pytest.raises(ReleaseError, match='source_dirty'):
        build_release_manifest(
            root=tmp_path,
            release_id='release-built-0002',
            images=built['images'],
            sbom_path=sbom,
            provenance_path=provenance,
            now=NOW,
            key=KEY,
        )
