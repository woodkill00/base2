import json
from pathlib import Path

import pytest

from digital_ocean.scripts.python.persistent_mail_dns import ensure_mail_dns, plan_mail_dns
from digital_ocean.scripts.python.preview_dns_journal import DnsJournal

CONFIG = Path(__file__).parents[1] / "config/woodkilldev-resend-dns.json"


class Provider:
    def __init__(self):
        self.rows = []
        self.calls = 0
        self.uncertain = False

    def list_records(self, domain):
        return {"domain_records": self.rows}

    def create_record(self, domain, record):
        self.calls += 1
        row = {**record, "id": self.calls}
        self.rows.append(row)
        if self.uncertain:
            raise RuntimeError("timeout")
        return {"domain_record": row}


def test_create_verify_and_repeat_without_writes(tmp_path):
    provider = Provider()
    journal = DnsJournal(tmp_path / "mail.json", "base2-mail-dns-test", "woodkilldev.com")
    assert ensure_mail_dns(desired(), provider, journal)["status"] == "ready"
    assert provider.calls == 4
    assert ensure_mail_dns(desired(), provider, journal)["status"] == "ready"
    assert provider.calls == 4
    provider.rows.pop()
    with pytest.raises(RuntimeError, match="drift"):
        ensure_mail_dns(desired(), provider, journal)
    assert provider.calls == 4


def test_uncertain_creation_cannot_duplicate_on_retry(tmp_path):
    provider = Provider()
    provider.uncertain = True
    journal = DnsJournal(tmp_path / "mail.json", "base2-mail-dns-test", "woodkilldev.com")
    with pytest.raises(RuntimeError, match="timeout"):
        ensure_mail_dns(desired(), provider, journal)
    with pytest.raises(RuntimeError, match="uncertain"):
        ensure_mail_dns(desired(), provider, journal)
    assert provider.calls == 1


def test_incomplete_inventory_blocks_before_any_writes(tmp_path):
    provider = Provider()
    provider.list_records = lambda _: {"domain_records": [], "links": {"pages": {"next": "more"}}}
    journal = DnsJournal(tmp_path / "mail.json", "base2-mail-dns-test", "woodkilldev.com")
    with pytest.raises(RuntimeError, match="inventory"):
        ensure_mail_dns(desired(), provider, journal)
    assert provider.calls == 0


def desired():
    return json.loads(CONFIG.read_text())


def test_missing_records_are_create_only_and_receiving_is_absent():
    result = plan_mail_dns(desired(), [])
    assert result["status"] == "changes_required"
    assert len(result["create"]) == 4
    assert all(row["type"] != "MX" for row in result["create"])
    assert result["lifecycle"] == "persistent"


def test_matching_records_are_noop_with_provider_name_normalization():
    rows = desired()["records"]
    for row in rows:
        row["name"] += ".woodkilldev.com."
        if row["type"] == "CNAME":
            row["data"] = row["data"].rstrip(".").upper()
        row["ttl"] = 1800
    result = plan_mail_dns(desired(), rows)
    assert result["status"] == "ready"
    assert result["create"] == []


@pytest.mark.parametrize(
    "row",
    [
        {"type": "TXT", "name": "_dmarc", "data": "v=DMARC1; p=reject;"},
        {"type": "A", "name": "send", "data": "8.8.8.8"},
        {"type": "CNAME", "name": "resend._domainkey", "data": "other.example."},
    ],
)
def test_conflict_blocks_whole_batch_without_downgrades(row):
    result = plan_mail_dns(desired(), [row])
    assert result["status"] == "conflict"
    assert result["create"] == []
    assert result["conflicts"] == [row["name"]]


def test_unrelated_inbound_mail_is_not_modified():
    result = plan_mail_dns(desired(), [{"type": "MX", "name": "@", "data": "mail.example."}])
    assert len(result["create"]) == 4


def test_duplicate_existing_identity_blocks_instead_of_creating_again():
    row = desired()["records"][0]
    assert plan_mail_dns(desired(), [row, row])["status"] == "conflict"


@pytest.mark.parametrize("rows", [None, {}, [{}]])
def test_malformed_inventory_fails_closed(rows):
    with pytest.raises(ValueError):
        plan_mail_dns(desired(), rows)


def test_receiving_or_unreviewed_record_types_fail_closed():
    config = desired()
    config["records"].append({"type": "MX", "name": "@", "data": "mail.example.", "ttl": 3600})
    with pytest.raises(ValueError):
        plan_mail_dns(config, [])
