import pytest
from digital_ocean.scripts.python.full_preview_dns import DnsMigrationError, migrate_required_records, required_names, restore_migration

class Provider:
    def __init__(self, fail_create=None, fail_delete=None):
        self.rows = [{"id": 10, "type": "A", "name": "admin", "data": "198.51.100.1"}]
        self.next_id = 20
        self.calls = []
        self.fail_create = fail_create
        self.fail_delete = fail_delete
    def list_records(self, domain):
        return [dict(row) for row in self.rows]
    def create_record(self, domain, payload):
        self.calls.append(("create", payload["name"], payload["data"]))
        if self.fail_create == payload["name"]:
            raise RuntimeError("create")
        row = {"id": self.next_id, "type": payload["type"], "name": payload["name"], "data": payload["data"]}
        self.next_id += 1
        self.rows.append(row)
        return {"domain_record": dict(row)}
    def delete_record(self, domain, record_id):
        self.calls.append(("delete", record_id))
        if self.fail_delete == record_id:
            raise RuntimeError("delete")
        self.rows = [row for row in self.rows if row["id"] != record_id]

def test_creates_all_names_before_removing_legacy_and_returns_exact_ids():
    provider = Provider()
    receipt = migrate_required_records(provider, "woodkilldev.com", "8.8.8.8")
    assert [row["name"] for row in receipt["records"]] == list(required_names("woodkilldev.com"))
    assert provider.calls[0] == ("create", "woodkilldev.com", "8.8.8.8")
    assert all(call[:2] != ("create", "@") for call in provider.calls)
    assert provider.calls[-1] == ("delete", 10)
    assert all(call[0] == "create" for call in provider.calls[:6])

def test_create_failure_rolls_back_new_records_without_touching_legacy():
    provider = Provider(fail_create="swagger")
    with pytest.raises(DnsMigrationError, match="rolled back"):
        migrate_required_records(provider, "woodkilldev.com", "8.8.8.8")
    assert provider.rows == [{"id": 10, "type": "A", "name": "admin", "data": "198.51.100.1"}]

def test_hostile_ttl_and_address_reject_before_provider_calls():
    provider = Provider()
    with pytest.raises(DnsMigrationError, match="public IPv4"):
        migrate_required_records(provider, "woodkilldev.com", "127.0.0.1")
    with pytest.raises(DnsMigrationError, match="TTL"):
        migrate_required_records(provider, "woodkilldev.com", "8.8.8.8", ttl=5)
    assert provider.calls == []

def test_accepts_the_real_digitalocean_inventory_shape():
    provider = Provider()
    original = provider.list_records
    provider.list_records = lambda domain: {"domain_records": original(domain)}
    receipt = migrate_required_records(provider, "woodkilldev.com", "8.8.8.8")
    assert receipt["createdRecordCount"] == len(required_names("woodkilldev.com"))


def test_replaces_a_legacy_literal_at_record_but_never_recreates_it_on_success():
    provider = Provider()
    provider.rows.append({"id": 11, "type": "A", "name": "@", "data": "198.51.100.2"})
    receipt = migrate_required_records(provider, "woodkilldev.com", "8.8.8.8")
    assert {row["name"] for row in receipt["replacedRecords"]} == {"admin", "@"}
    assert all(row["name"] != "@" for row in provider.rows)


def test_invalid_domain_rejects_before_provider_access():
    provider = Provider()
    with pytest.raises(DnsMigrationError, match="domain"):
        migrate_required_records(provider, "../unsafe", "8.8.8.8")
    assert provider.calls == []


def test_provider_name_rewrite_fails_closed_and_rolls_back():
    provider = Provider()
    original = provider.create_record

    def rewritten(domain, payload):
        response = original(domain, payload)
        if payload["name"] == domain:
            response["domain_record"]["name"] = "@"
        return response

    provider.create_record = rewritten
    with pytest.raises(DnsMigrationError, match="rolled back"):
        migrate_required_records(provider, "woodkilldev.com", "8.8.8.8")
    assert provider.rows == [{"id": 10, "type": "A", "name": "admin", "data": "198.51.100.1"}]

def test_exact_rollback_restores_the_prior_record_set():
    provider = Provider()
    receipt = migrate_required_records(provider, "woodkilldev.com", "8.8.8.8")
    result = restore_migration(provider, receipt)
    assert result == {"ok": True, "createdRecordsDeleted": 6, "priorRecordsRestored": 1, "secretValuesEmitted": 0}
    assert [(row["type"], row["name"], row["data"]) for row in provider.rows] == [("A", "admin", "198.51.100.1")]
