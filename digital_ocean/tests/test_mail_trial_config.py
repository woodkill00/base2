import json
import os

import pytest

from digital_ocean.scripts.python.mail_trial_config import configure_trial, load_trial


def fixture(tmp_path):
    path = tmp_path / "input.json"
    path.write_text(
        json.dumps(
            {
                "domain": "woodkilldev.com",
                "apiKey": "re_synthetic",
                "fromAddress": "noreply@woodkilldev.com",
                "recipient": "thejunkmailvoid@gmail.com",
                "expiresAt": 2000,
                "maxAttempts": 5,
            }
        )
    )
    path.chmod(0o600)
    return path


def test_private_configuration_and_refuse_budget_reset(tmp_path):
    source = fixture(tmp_path)
    env = tmp_path / ".env"
    env.write_text("BASE2_EMAIL_ADAPTER=local_fake\nUNRELATED=preserved\n")
    root = tmp_path / "private"
    configure_trial(source, env, root, "woodkilldev.com", uid=os.getuid(), now=1000)
    assert "BASE2_EMAIL_ADAPTER=resend" in env.read_text()
    assert "re_synthetic" not in env.read_text()
    assert "UNRELATED=preserved" in env.read_text()
    assert json.loads((root / "budget.json").read_text())["reservations"] == []
    with pytest.raises(RuntimeError, match="already_exists"):
        configure_trial(source, env, root, "woodkilldev.com", uid=os.getuid(), now=1000)


@pytest.mark.parametrize(
    "change",
    [
        {"domain": "other.example"},
        {"recipient": "other@example.com"},
        {"fromAddress": "a@other.example"},
        {"apiKey": "bad\nkey"},
        {"expiresAt": 1000},
        {"expiresAt": 9000},
        {"maxAttempts": 21},
        {"maxAttempts": True},
        {"extra": "unexpected"},
    ],
)
def test_invalid_trial_rejected_before_activation(tmp_path, change):
    path = fixture(tmp_path)
    data = json.loads(path.read_text())
    data.update(change)
    path.write_text(json.dumps(data))
    with pytest.raises((ValueError, RuntimeError)):
        load_trial(path, "woodkilldev.com", now=1000)


def test_public_or_symlink_secret_rejected(tmp_path):
    path = fixture(tmp_path)
    link = tmp_path / "link"
    link.symlink_to(path)
    with pytest.raises(RuntimeError):
        load_trial(link, "woodkilldev.com", now=1000)
    path.chmod(0o644)
    with pytest.raises(RuntimeError):
        load_trial(path, "woodkilldev.com", now=1000)


def test_budget_cannot_outlive_shorter_preview_lease(tmp_path):
    source = fixture(tmp_path)
    with pytest.raises(RuntimeError, match="scope_or_expiry"):
        load_trial(source, "woodkilldev.com", now=1000, ttl_minutes=10)
