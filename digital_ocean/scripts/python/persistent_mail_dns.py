"""Pure sending-only DNS planner. No credentials, network or lease ownership.

The caller must supply a complete inventory from the authoritative zone provider.
A ready plan is not proof of propagation or provider domain verification.
"""

import re

from digital_ocean.scripts.python.full_preview_expire import bounded_inventory


def main(argv=None):
    """Supported full-preview mail-dns subcommand; plan is the default."""
    import argparse
    import hashlib
    import json
    import urllib.parse
    import urllib.request
    from pathlib import Path

    from digital_ocean.scripts.python.full_preview_expire import _token
    from digital_ocean.scripts.python.live_preview_provider import DigitalOceanHttpClient
    from digital_ocean.scripts.python.preview_dns_journal import DnsJournal
    from digital_ocean.scripts.python.preview_lease_v2 import FullPreviewLeaseStore

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--credential-file", type=Path, required=True)
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        config = json.loads(args.config.read_text())
        plan_mail_dns(config, [])
        domain = config["domain"]
        # HTTPS recursive observation supplements provider inventory; never infer
        # that owning a dormant provider zone makes it authoritative.
        query = urllib.parse.urlencode({"name": domain, "type": "NS"})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open("https://dns.google/resolve?" + query, timeout=10) as response:
            payload = json.loads(response.read(65537))
        names = {
            row.get("data", "").lower().rstrip(".")
            for row in payload.get("Answer", [])
            if row.get("type") == 2
        }
        if payload.get("Status") != 0 or names != {
            "ns1.digitalocean.com",
            "ns2.digitalocean.com",
            "ns3.digitalocean.com",
        }:
            raise RuntimeError("mail_dns_delegation_unverified")
        provider = DigitalOceanHttpClient(_token(args.credential_file)).domains
        identity = hashlib.sha256(domain.encode()).hexdigest()
        admission = Path.home() / ".local/state/base2-preview-admission" / identity
        with (
            FullPreviewLeaseStore(admission).operation(),
            FullPreviewLeaseStore(args.state_root).operation(),
        ):
            rows = bounded_inventory(provider.list_records(domain), "domain_records")
            result = plan_mail_dns(config, rows)
            if args.apply:
                journal = DnsJournal(
                    args.state_root / ("mail-" + identity + ".json"),
                    "base2-mail-dns-" + identity[:16],
                    domain,
                )
                result = ensure_mail_dns(config, provider, journal)
        print(json.dumps(result, sort_keys=True))
        return 2 if result["status"] == "conflict" else 0
    except Exception as exc:
        # Never print provider exception bodies or credential-bearing arguments.
        print(
            json.dumps(
                {
                    "status": "failed",
                    "errorType": type(exc).__name__,
                    "reason": "mail_dns_operation_failed_requires_review",
                    "secretValuesEmitted": 0,
                }
            )
        )
        return 2


def ensure_mail_dns(config, provider, journal):
    """Caller holds domain lock; journal is persistent and outside preview leases.

    No deletion/update authority is used. Ambiguous writes remain pending and
    block further mutation. Partial successful records remain for reconciliation.
    """
    domain = config["domain"]
    if journal.domain != domain:
        raise ValueError("mail_dns_journal_domain_mismatch")

    def observe():
        rows = bounded_inventory(provider.list_records(domain), "domain_records")
        return plan_mail_dns(config, rows)

    initial = observe()
    if initial["status"] == "conflict":
        raise RuntimeError("mail_dns_conflict")
    if journal.path.exists():
        state = journal.load()
        if any(op["state"] == "pending" for op in state["operations"]):
            raise RuntimeError("mail_dns_uncertain_write_requires_reconciliation")
        if state["phase"] not in {"migrating", "committed"}:
            raise RuntimeError("mail_dns_journal_phase_invalid")
        if state["phase"] == "committed" and initial["status"] != "ready":
            raise RuntimeError("mail_dns_drift_requires_reconciliation")
    else:
        journal.create()
    for desired in initial["create"]:
        current = observe()
        if current["status"] == "conflict":
            raise RuntimeError("mail_dns_conflict")
        if desired not in current["create"]:
            continue

        def create(desired=desired):
            response = provider.create_record(domain, desired)
            row = response.get("domain_record") if isinstance(response, dict) else None
            if (
                not isinstance(row, dict)
                or not row.get("id")
                or plan_mail_dns({**config, "records": [desired]}, [row])["status"] != "ready"
            ):
                raise RuntimeError("mail_dns_create_identity_invalid")
            return {"id": str(row["id"]), "type": row["type"], "name": row["name"]}

        journal.mutate("create", dict(desired), create)
    final = observe()
    if final["status"] != "ready":
        raise RuntimeError("mail_dns_verification_failed")
    journal.phase("committed")
    return {
        **final,
        "providerInventoryVerified": True,
        "propagationVerified": False,
        "receivingEnabled": False,
    }


def plan_mail_dns(config: dict, inventory: list[dict]) -> dict:
    domain = config.get("domain", "")
    records = config.get("records")
    if (
        config.get("schemaVersion") != 1
        or config.get("lifecycle") != "persistent"
        or config.get("receivingEnabled") is not False
        or not isinstance(domain, str)
        or not re.fullmatch(r"[a-z0-9-]+(?:\.[a-z0-9-]+)+", domain)
        or not isinstance(records, list)
        or not records
        or not isinstance(inventory, list)
    ):
        raise ValueError("mail_dns_configuration_invalid")

    def name(value):
        normalized = value.lower().rstrip(".")
        suffix = "." + domain
        return normalized[: -len(suffix)] if normalized.endswith(suffix) else normalized

    def data(row):
        value = row["data"]
        return value.lower().rstrip(".") if row["type"] == "CNAME" else value

    for row in [*records, *inventory]:
        if not isinstance(row, dict) or any(
            not isinstance(row.get(key), str) or not row[key] for key in ("type", "name", "data")
        ):
            raise ValueError("mail_dns_record_invalid")
    names = set()
    for row in records:
        if (
            row["type"] not in {"TXT", "CNAME"}
            or row["name"] in names
            or not re.fullmatch(r"[a-z0-9_-]+(?:\.[a-z0-9_-]+)*", row["name"])
            or type(row.get("ttl")) is not int
            or not 60 <= row["ttl"] <= 86400
        ):
            raise ValueError("mail_dns_record_invalid")
        names.add(row["name"])
    missing, conflicts = [], []
    for desired in records:
        same_name = [row for row in inventory if name(row["name"]) == desired["name"]]
        relevant = [
            row
            for row in same_name
            if row["type"] == desired["type"]
            or row["type"] == "CNAME"
            or desired["type"] == "CNAME"
        ]
        if not relevant:
            missing.append(dict(desired))
        elif (
            len(relevant) != 1
            or relevant[0]["type"] != desired["type"]
            or data(relevant[0]) != data(desired)
        ):
            conflicts.append(desired["name"])
    return {
        "status": "conflict" if conflicts else "changes_required" if missing else "ready",
        "domain": domain,
        "lifecycle": "persistent",
        "create": [] if conflicts else missing,
        "conflicts": sorted(conflicts),
    }
