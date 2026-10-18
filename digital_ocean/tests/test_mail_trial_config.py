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
    budget = root / 'budget.json'
    state = json.loads(budget.read_text())
    state['reservations'] = ['a' * 64]
    budget.write_text(json.dumps(state))
    before = {path: path.read_bytes() for path in (budget, root / 'key', env)}
    with pytest.raises(RuntimeError, match="already_exists"):
        configure_trial(source, env, root, "woodkilldev.com", uid=os.getuid(), now=1000)
    assert all(path.read_bytes() == contents for path, contents in before.items())


def test_approved_disposable_alias_is_the_only_activated_recipient(tmp_path):
    source = fixture(tmp_path)
    data = json.loads(source.read_text())
    data['recipient'] = 'thejunkmailvoid+base2-test@gmail.com'
    source.write_text(json.dumps(data))
    env = tmp_path / '.env'
    env.write_text('BASE2_EMAIL_ALLOWED_RECIPIENTS=thejunkmailvoid@gmail.com\n')
    root = tmp_path / 'private'
    configure_trial(source, env, root, 'woodkilldev.com', uid=os.getuid(), now=1000)
    recipients = [line for line in env.read_text().splitlines()
                  if line.startswith('BASE2_EMAIL_ALLOWED_RECIPIENTS=')]
    assert recipients == ['BASE2_EMAIL_ALLOWED_RECIPIENTS=thejunkmailvoid+base2-test@gmail.com']


@pytest.mark.parametrize('recipient', [
    'thejunkmailvoid+other@gmail.com',
    'thejunkmailvoid+base2-test@gmail.com.evil.test',
    'thejunkmailvoid+base2-test@gmail.com,other@example.com',
    'thejunkmailvoid+base2-test@gmail.com\nOTHER=value',
    ['thejunkmailvoid+base2-test@gmail.com'],
])
def test_alias_approval_does_not_allow_other_recipients(tmp_path, recipient):
    source = fixture(tmp_path)
    data = json.loads(source.read_text())
    data['recipient'] = recipient
    source.write_text(json.dumps(data))
    with pytest.raises(RuntimeError, match='scope_or_expiry'):
        load_trial(source, 'woodkilldev.com', now=1000)


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
