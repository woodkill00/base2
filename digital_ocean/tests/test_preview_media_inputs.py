import json
from types import SimpleNamespace
import pytest
from digital_ocean.scripts.python.preview_media_inputs import provision_media_inputs


@pytest.mark.parametrize("failure", [None, "exit", "receipt", "permissions"])
def test_fixed_private_media_handoff(tmp_path, failure):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    hosts = tmp_path / "known_hosts"
    key = tmp_path / "key"
    for file in (hosts, key):
        file.write_text("fixture")
        file.chmod(0o600)
    if failure == "permissions":
        key.chmod(0o644)
    calls = []

    def run(argv, **kw):
        calls.append((argv, kw))
        assert "StrictHostKeyChecking=yes" in argv
        assert (
            "docker exec -i -e BASE2_PREVIEW_MEDIA_FIXTURE=true base2-full-preview_api python -m api.scripts.preview_media_fixture"
            == argv[-1]
        )
        assert json.loads(kw["input"])["password"] not in " ".join(argv)
        return SimpleNamespace(
            returncode=1 if failure == "exit" else 0,
            stdout="{}"
            if failure == "receipt"
            else json.dumps({"status": "created", "role": "editor", "secretValuesEmitted": 0}),
        )

    kwargs = dict(
        receipt={
            "runId": "base2-full-20261016-000000",
            "expiresAt": "2026-10-16T00:30:00Z",
            "publicIp": "8.8.8.8",
        },
        receipt_path=evidence / "receipt.json",
        ssh_key=key,
        runner=run,
    )
    if failure:
        with pytest.raises(ValueError):
            provision_media_inputs(**kwargs)
        if failure == "permissions":
            assert not calls
    else:
        result = provision_media_inputs(**kwargs)
        assert result["BASE2_MEDIA_EMAIL"] == "media-base2-full-20261016-000000@example.invalid"
        assert len(result["BASE2_MEDIA_PASSWORD"]) > 32
