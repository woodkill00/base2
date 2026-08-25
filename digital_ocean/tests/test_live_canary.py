from __future__ import annotations

import hashlib
import json
from pathlib import Path

from digital_ocean.scripts.python.live_canary import main, run_canaries, validate_plan
from digital_ocean.scripts.python.live_canary_preflight import binding_digest


def approved_plan(archive: Path) -> dict:
    binding = {
        "sourceCommit": "a" * 40,
        "sourceArchiveSha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "projectName": "project1",
        "providerProjectId": "project-id",
        "region": "nyc3",
        "size": "s-2vcpu-4gb",
        "image": "ubuntu-24-04-x64",
        "dropletName": "project1-f093-abc",
        "ownershipNamespace": "base2-f093-aaaaaaaa",
        "dnsZone": "example.com",
        "dnsMutations": [
            {
                "name": "f093-abc",
                "type": "A",
                "fqdn": "f093-abc.example.com",
            }
        ],
        "certificateSans": ["f093-abc.example.com"],
        "trialCount": 3,
        "maximumConcurrentDroplets": 1,
        "leaseMinutesPerTrial": 15,
        "totalCostCeilingMinorUnits": 100,
        "hourlyCostMinorUnitsCeiling": 4,
        "currency": "USD",
        "certificateMode": "letsencrypt-staging-only",
    }
    return {
        "schemaVersion": 1,
        "status": "approval-required",
        "planDigest": binding_digest(binding),
        **binding,
    }


class Droplets:
    def __init__(self):
        self.rows = {}
        self.next_id = 1
        self.created = 0
        self.deleted = 0

    def list(self, tag_name=None):
        rows = list(self.rows.values())
        if tag_name:
            rows = [row for row in rows if tag_name in row["tags"]]
        return {"droplets": rows}

    def create(self, payload):
        self.created += 1
        provider_id = self.next_id
        self.next_id += 1
        row = {
            "id": provider_id,
            "name": payload["name"],
            "status": "active",
            "tags": list(payload["tags"]),
            "networks": {
                "v4": [{"type": "public", "ip_address": f"192.0.2.{provider_id}"}]
            },
        }
        self.rows[provider_id] = row
        return {"droplet": row}

    def get(self, provider_id):
        if int(provider_id) not in self.rows:
            error = RuntimeError("missing")
            error.status_code = 404
            raise error
        return {"droplet": self.rows[int(provider_id)]}

    def delete(self, provider_id):
        self.deleted += 1
        self.rows.pop(int(provider_id), None)


class Domains:
    def __init__(self):
        self.records = []
        self.next_id = 1

    def list_records(self, _zone):
        return {"domain_records": list(self.records)}

    def create_record(self, _zone, payload):
        self.records.append({"id": self.next_id, **payload})
        self.next_id += 1

    def update_record(self, _zone, record_id, payload):
        next(row for row in self.records if row["id"] == record_id).update(payload)

    def delete_record(self, _zone, record_id):
        self.records = [row for row in self.records if row["id"] != record_id]


class Client:
    def __init__(self):
        self.droplets = Droplets()
        self.domains = Domains()


class Remote:
    def __init__(self):
        self.deploys = 0

    def deploy(self, _ip, _config):
        self.deploys += 1

    def health(self, _ip, _fqdn):
        return True


def inputs(tmp_path):
    archive = tmp_path / "source.tar"
    archive.write_bytes(b"source")
    key = tmp_path / "key"
    key.write_text("private", encoding="utf-8")
    key.chmod(0o600)
    return archive, key


def test_three_trials_restore_dns_and_resources(tmp_path, capsys):
    archive, key = inputs(tmp_path)
    plan = approved_plan(archive)
    client, remote = Client(), Remote()
    result = run_canaries(
        plan,
        token="fixture",
        source_archive=archive,
        ssh_private_key=key,
        ssh_key_id=1,
        state_root=tmp_path / "state",
        client_factory=lambda _token: client,
        remote_factory=lambda _known: remote,
        sleep=lambda _delay: None,
    )
    assert result["status"] == "passed" and result["trialCount"] == 3
    assert client.droplets.created == client.droplets.deleted == 3
    assert client.droplets.rows == {} and client.domains.records == []
    assert remote.deploys == 3
    assert json.loads(capsys.readouterr().out)["zeroProviderResources"] is True


def test_plan_tamper_and_archive_tamper_fail_closed(tmp_path):
    archive, _key = inputs(tmp_path)
    plan = approved_plan(archive)
    plan["size"] = "s-4vcpu-8gb"
    try:
        validate_plan(plan, archive)
    except Exception as exc:
        assert "digest" in str(exc)
    else:
        raise AssertionError("changed plan was accepted")
    plan = approved_plan(archive)
    archive.write_bytes(b"changed")
    try:
        validate_plan(plan, archive)
    except Exception as exc:
        assert "archive" in str(exc)
    else:
        raise AssertionError("changed archive was accepted")


def test_cli_dry_run_performs_no_credential_or_network_read(tmp_path, capsys):
    archive, key = inputs(tmp_path)
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(approved_plan(archive)), encoding="utf-8")
    assert (
        main(
            [
                "--plan",
                str(plan_path),
                "--source-archive",
                str(archive),
                "--ssh-private-key",
                str(key),
                "--ssh-key-id",
                "1",
                "--state-root",
                str(tmp_path / "unused"),
                "--dry-run",
            ]
        )
        == 0
    )
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["status"] == "validated-no-network"
    assert receipt["mutationSent"] is False
