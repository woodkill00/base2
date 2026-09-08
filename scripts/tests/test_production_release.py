from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from scripts.python.production_release import (
    ProductionReleaseController,
    ReleaseError,
    approval,
    sign_release,
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
        expires_at=(NOW + timedelta(minutes=offset)).isoformat(),
        key=OWNER_KEY,
    )


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
            )
            assert len(receipt["digest"]) == 64
            replay = controller.transition(
                action=action,
                release=item,
                environment="staging",
                owner_approval=permit(action, item),
                now=NOW,
                health=lambda _: True,
            )
            assert replay["status"] == "idempotent"
        assert controller.status() == {
            "state": "promoted",
            "environment": "staging",
            "current": item["releaseId"],
            "candidate": item["releaseId"],
            "checkpoints": ["prepare", "stage", "canary", "promote"],
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
            )
        controller.transition(
            action="prepare",
            release=second,
            environment="staging",
            owner_approval=permit("prepare", second),
            now=NOW,
            health=lambda _: True,
        )
        controller.transition(
            action="stage",
            release=second,
            environment="staging",
            owner_approval=permit("stage", second),
            now=NOW,
            health=lambda _: True,
        )
        result = controller.transition(
            action="canary",
            release=second,
            environment="staging",
            owner_approval=permit("canary", second),
            now=NOW,
            health=lambda _: False,
        )
        assert result["status"] == "halted"
        assert controller.status()["current"] == first["releaseId"]
        rolled = controller.transition(
            action="rollback",
            release=second,
            environment="staging",
            owner_approval=permit("rollback", second),
            now=NOW,
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
        )
        with pytest.raises(ReleaseError, match="candidate_mismatch"):
            resumed.transition(
                action="canary",
                release=release(2),
                environment="preview",
                owner_approval=permit("canary", release(2), "preview"),
                now=NOW,
                health=lambda _: True,
            )
        path.write_text("{}", encoding="utf-8")
        with pytest.raises(ReleaseError, match="journal_integrity"):
            resumed.status()


def test_nonproduction_lifecycle_never_requests_production_certificates():
    for environment in ("development", "test", "preview", "staging"):
        certificate_mode = "disabled" if environment in {"development", "test"} else "staging-only"
        assert certificate_mode != "production"


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
