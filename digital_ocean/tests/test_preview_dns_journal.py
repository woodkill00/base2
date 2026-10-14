import json

import pytest

from digital_ocean.scripts.python.full_preview_dns import (
    DnsMigrationError,
    migrate_required_records,
    restore_migration,
)
from digital_ocean.scripts.python.preview_dns_journal import (
    DnsJournal,
    JournaledDnsProvider,
    JournalError,
    reconcile_dns,
)
from digital_ocean.tests.test_full_preview_dns import Provider


def setup(tmp_path):
    journal = DnsJournal(tmp_path / "dns.journal", "base2-full-journal-test", "woodkilldev.com")
    journal.create()
    raw = Provider()
    return journal, raw, JournaledDnsProvider(raw, journal)


def test_each_successful_mutation_has_private_durable_intent_and_result(tmp_path):
    journal, raw, provider = setup(tmp_path)
    receipt = migrate_required_records(provider, journal.domain, "8.8.8.8")
    assert len(journal.load()["operations"]) == 7
    journal.phase("committed")
    journal.phase("restoring")
    restore_migration(provider, receipt)
    journal.phase("restored")
    assert all(op["state"] == "done" for op in journal.load()["operations"])
    assert journal.path.stat().st_mode & 0o777 == 0o600


def test_lost_response_records_intent_and_never_blindly_retries(tmp_path):
    journal, raw, provider = setup(tmp_path)
    original = raw.create_record

    def lost(domain, payload):
        assert journal.load()["operations"][-1]["state"] == "pending"
        original(domain, payload)
        raise TimeoutError("private value")

    raw.create_record = lost
    with pytest.raises(DnsMigrationError):
        migrate_required_records(provider, journal.domain, "8.8.8.8")
    calls = list(raw.calls)
    with pytest.raises(JournalError):
        provider.create_record(journal.domain, {"type": "A", "name": "admin", "data": "8.8.8.8"})
    assert raw.calls == calls
    assert "private value" not in journal.path.read_text()
    with pytest.raises(JournalError):
        journal.phase("restored")
    report = reconcile_dns(journal, raw)
    assert report["pending"][0]["candidateIds"] == ["20"]
    assert report["status"] == "reconciliation-required"
    assert report["mutationSent"] is False
    assert raw.calls == calls


def test_identity_drift_blocks_delete(tmp_path):
    journal, raw, provider = setup(tmp_path)
    provider.list_records(journal.domain)
    raw.rows[0]["data"] = "1.1.1.1"
    with pytest.raises(JournalError, match="identity"):
        provider.delete_record(journal.domain, 10)
    assert raw.calls == []


def test_journal_tamper_and_duplicate_creation_fail_closed(tmp_path):
    journal, raw, provider = setup(tmp_path)
    with pytest.raises(JournalError):
        journal.create()
    data = json.loads(journal.path.read_text())
    data["data"]["phase"] = "restored"
    journal.path.write_text(json.dumps(data))
    with pytest.raises(JournalError):
        journal.load()


def test_wrong_domain_unknown_id_and_unbounded_inventory_are_rejected(tmp_path):
    journal, raw, provider = setup(tmp_path)
    with pytest.raises(JournalError):
        provider.list_records("other.example")
    with pytest.raises(JournalError):
        provider.delete_record(journal.domain, 999)
    raw.list_records = lambda domain: [raw.rows[0]] * 1001
    with pytest.raises(JournalError):
        provider.list_records(journal.domain)
    with pytest.raises(JournalError):
        reconcile_dns(journal, raw)
    assert raw.calls == []


def test_pending_delete_reports_absent_without_mutation(tmp_path):
    journal, raw, provider = setup(tmp_path)
    provider.list_records(journal.domain)
    original = raw.delete_record

    def lost(domain, record_id):
        original(domain, record_id)
        raise TimeoutError()

    raw.delete_record = lost
    with pytest.raises(TimeoutError):
        provider.delete_record(journal.domain, 10)
    before = list(raw.calls)
    assert reconcile_dns(journal, raw)["pending"][0]["observed"] == "absent"
    assert raw.calls == before


def test_symlink_permissions_and_invalid_schema_rejected(tmp_path):
    journal, raw, provider = setup(tmp_path)
    journal.path.chmod(0o644)
    with pytest.raises(JournalError):
        journal.load()
    journal.path.chmod(0o600)
    data = journal.load()
    data["operations"] = [{"unexpected": True}]
    journal.save(data)
    with pytest.raises(JournalError):
        journal.load()
    link = tmp_path / "link"
    link.symlink_to(journal.path)
    linked = DnsJournal(link, journal.run_id, journal.domain)
    with pytest.raises(JournalError):
        linked.load()
    with pytest.raises(JournalError):
        linked.save(data)
    with pytest.raises(JournalError):
        DnsJournal(tmp_path / "other", "../unsafe", journal.domain)
