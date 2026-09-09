from __future__ import annotations

import pytest

from api.tests import test_email_outbox


def test_email_worker_database_rejects_missing_credentials(monkeypatch):
    monkeypatch.delenv("EMAIL_WORKER_DB_USER", raising=False)
    monkeypatch.delenv("EMAIL_WORKER_DB_PASSWORD", raising=False)

    with pytest.raises(pytest.fail.Exception, match="credentials_missing"):
        with test_email_outbox.email_worker_database():
            raise AssertionError("unreachable")


def test_email_worker_database_switches_and_restores_owner(monkeypatch):
    calls: list[str] = []
    monkeypatch.setenv("DB_USER", "owner")
    monkeypatch.setenv("DB_PASSWORD", "owner-password")
    monkeypatch.setenv("EMAIL_WORKER_DB_USER", "worker")
    monkeypatch.setenv("EMAIL_WORKER_DB_PASSWORD", "worker-password")
    monkeypatch.setattr(test_email_outbox, "close_pool", lambda: calls.append("closed"))

    with test_email_outbox.email_worker_database():
        assert test_email_outbox.os.environ["DB_USER"] == "worker"
        assert test_email_outbox.os.environ["DB_PASSWORD"] == "worker-password"

    assert test_email_outbox.os.environ["DB_USER"] == "owner"
    assert test_email_outbox.os.environ["DB_PASSWORD"] == "owner-password"
    assert calls == ["closed", "closed"]


def test_email_worker_database_restores_absent_owner_values(monkeypatch):
    monkeypatch.delenv("DB_USER", raising=False)
    monkeypatch.delenv("DB_PASSWORD", raising=False)
    monkeypatch.setenv("EMAIL_WORKER_DB_USER", "worker")
    monkeypatch.setenv("EMAIL_WORKER_DB_PASSWORD", "worker-password")
    monkeypatch.setattr(test_email_outbox, "close_pool", lambda: None)

    with test_email_outbox.email_worker_database():
        pass

    assert "DB_USER" not in test_email_outbox.os.environ
    assert "DB_PASSWORD" not in test_email_outbox.os.environ
