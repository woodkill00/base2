"""Durable DNS intent/receipt log; uncertain writes require reconciliation."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path

from digital_ocean.scripts.python.full_preview_dns import DnsMigrationError, _row, required_names


class JournalError(DnsMigrationError):
    pass


def _encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


class DnsJournal:
    """Caller must hold the preview operation lock throughout use."""

    def __init__(self, path: Path, run_id: str, domain: str):
        from digital_ocean.scripts.python.preview_lease_v2 import RUN_ID

        if not RUN_ID.fullmatch(run_id):
            raise JournalError("invalid journal run")
        required_names(domain)
        self.path = path
        self.run_id = run_id
        self.domain = domain

    def save(self, value):
        if self.path.is_symlink() or self.path.parent.is_symlink():
            raise JournalError("unsafe journal path")
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        body = _encoded(value)
        envelope = _encoded({"data": value, "sha256": hashlib.sha256(body).hexdigest()})
        descriptor, name = tempfile.mkstemp(prefix=".dns-", dir=self.path.parent)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(envelope)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.path)
            directory = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            Path(name).unlink(missing_ok=True)

    def load(self):
        if self.path.is_symlink():
            raise JournalError("unsafe journal path")
        metadata = self.path.stat()
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or metadata.st_uid != os.getuid()
            or metadata.st_mode & 0o077
            or metadata.st_size > 131072
        ):
            raise JournalError("unsafe journal member")
        try:
            envelope = json.loads(self.path.read_text())
            data = envelope["data"]
            if (
                set(envelope) != {"data", "sha256"}
                or envelope["sha256"] != hashlib.sha256(_encoded(data)).hexdigest()
                or set(data) != {"schemaVersion", "runId", "domain", "phase", "operations"}
                or data["schemaVersion"] != 1
                or data["runId"] != self.run_id
                or data["domain"] != self.domain
                or data["phase"] not in {"migrating", "committed", "restoring", "restored"}
                or not isinstance(data["operations"], list)
                or len(data["operations"]) > 64
            ):
                raise ValueError()
            for op in data["operations"]:
                if (
                    set(op) != {"action", "request", "result", "state"}
                    or op["action"] not in {"create", "delete"}
                    or op["state"] not in {"pending", "done"}
                    or not isinstance(op["request"], dict)
                ):
                    raise ValueError()
        except (ValueError, KeyError, TypeError) as exc:
            raise JournalError("journal integrity or schema mismatch") from exc
        return data

    def create(self):
        if self.path.exists() or self.path.is_symlink():
            raise JournalError("journal already exists")
        self.save(
            {
                "schemaVersion": 1,
                "runId": self.run_id,
                "domain": self.domain,
                "phase": "migrating",
                "operations": [],
            }
        )

    def phase(self, phase):
        data = self.load()
        if any(op["state"] == "pending" for op in data["operations"]):
            raise JournalError("uncertain DNS write requires reconciliation")
        data["phase"] = phase
        self.save(data)

    def mutate(self, action, request, call):
        data = self.load()
        if len(data["operations"]) >= 64 or any(
            op["state"] == "pending" for op in data["operations"]
        ):
            raise JournalError("uncertain or exhausted DNS journal")
        op = {"action": action, "request": request, "result": None, "state": "pending"}
        data["operations"].append(op)
        self.save(data)  # Intent is durable before issuing a provider write.
        result = call()
        op["result"] = result
        op["state"] = "done"
        self.save(data)  # A failed write leaves pending; do not blindly retry.
        return result


class JournaledDnsProvider:
    def __init__(self, provider, journal: DnsJournal):
        self.provider = provider
        self.journal = journal
        self.known = {}

    def _domain(self, domain):
        if domain != self.journal.domain:
            raise JournalError("DNS domain differs from journal")

    def list_records(self, domain):
        self._domain(domain)
        result = self.provider.list_records(domain)
        rows = result.get("domain_records") if isinstance(result, dict) else result
        if not isinstance(rows, list) or len(rows) > 1000:
            raise JournalError("DNS inventory unavailable or unbounded")
        for item in rows:
            row = _row(item)
            self.known.setdefault(row["id"], row)
        return result

    def create_record(self, domain, payload):
        self._domain(domain)
        row = self.journal.mutate(
            "create", dict(payload), lambda: _row(self.provider.create_record(domain, payload))
        )
        self.known[row["id"]] = row
        return {
            "domain_record": {
                "id": row["id"],
                "type": row["type"],
                "name": row["name"],
                "data": row["value"],
            }
        }

    def delete_record(self, domain, record_id):
        self._domain(domain)
        expected = self.known.get(str(record_id))
        if expected is None:
            raise JournalError("DNS deletion lacks observed identity")
        result = self.list_records(domain)
        rows = result.get("domain_records") if isinstance(result, dict) else result
        current = next((_row(row) for row in rows if str(row["id"]) == str(record_id)), None)
        if current is not None and current != expected:
            raise JournalError("DNS deletion identity changed")

        def remove():
            if current is not None:
                self.provider.delete_record(domain, int(record_id))
            return {"absent": True}

        return self.journal.mutate("delete", expected, remove)


def reconcile_dns(journal: DnsJournal, provider):
    """Bounded read-only evidence. An uncertain create never grants delete authority."""
    data = journal.load()
    result = provider.list_records(journal.domain)
    rows = result.get("domain_records") if isinstance(result, dict) else result
    if not isinstance(rows, list) or len(rows) > 1000:
        raise JournalError("DNS inventory unavailable or unbounded")
    inventory = [_row(row) for row in rows]
    pending = []
    for index, op in enumerate(data["operations"]):
        if op["state"] != "pending":
            continue
        request = op["request"]
        if op["action"] == "create":
            name = "@" if request["name"] == journal.domain + "." else request["name"]
            candidates = [
                row["id"]
                for row in inventory
                if row["type"] == request["type"]
                and row["name"] == name
                and row["value"] == request["data"]
            ]
            # Even one match can have been created by another actor. Report only.
            pending.append(
                {
                    "operation": index,
                    "action": "create",
                    "candidateIds": candidates,
                    "requiresOwnerReconciliation": True,
                }
            )
        else:
            current = next((row for row in inventory if row["id"] == request["id"]), None)
            pending.append(
                {
                    "operation": index,
                    "action": "delete",
                    "observed": "absent"
                    if current is None
                    else "unchanged"
                    if current == request
                    else "drifted",
                    "requiresOwnerReconciliation": True,
                }
            )
    return {
        "runId": journal.run_id,
        "phase": data["phase"],
        "pending": pending,
        "mutationSent": False,
        "secretValuesEmitted": 0,
        "status": "reconciliation-required"
        if pending or data["phase"] in {"migrating", "restoring"}
        else "journal-terminal",
    }
