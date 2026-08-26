#!/usr/bin/env python3
"""Normalize and classify independently sourced DNS convergence evidence."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from datetime import datetime

DOMAIN = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
SOURCE_CLASSES = {"provider-authoritative", "public-recursive", "system-recursive"}


class DnsConvergenceError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def classify_dns_observation(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != {
        "schemaVersion",
        "domain",
        "expectedAddress",
        "requiredHosts",
        "sources",
    }:
        raise DnsConvergenceError("DNS_OBSERVATION_INVALID", "DNS observation shape is invalid")
    domain = str(payload["domain"]).casefold()
    if payload["schemaVersion"] != 1 or not DOMAIN.fullmatch(domain):
        raise DnsConvergenceError("DNS_OBSERVATION_INVALID", "DNS observation identity is invalid")
    try:
        expected = str(ipaddress.IPv4Address(payload["expectedAddress"]))
    except ipaddress.AddressValueError as exc:
        raise DnsConvergenceError("DNS_OBSERVATION_INVALID", "expected address is invalid") from exc
    hosts = payload["requiredHosts"]
    if not isinstance(hosts, list) or not hosts or len(set(hosts)) != len(hosts):
        raise DnsConvergenceError("DNS_OBSERVATION_INVALID", "required hosts are invalid")
    normalized_hosts = []
    for host in hosts:
        host = str(host).casefold().rstrip(".")
        if host != domain and not host.endswith("." + domain):
            raise DnsConvergenceError(
                "DNS_OBSERVATION_INVALID", "required host is outside the domain"
            )
        normalized_hosts.append(host)
    sources = payload["sources"]
    if not isinstance(sources, list) or not sources:
        raise DnsConvergenceError("DNS_OBSERVATION_INVALID", "DNS sources are missing")
    normalized_sources = []
    for source in sources:
        if not isinstance(source, dict) or set(source) != {
            "sourceClass",
            "sourceName",
            "observedAt",
            "answers",
        }:
            raise DnsConvergenceError("DNS_OBSERVATION_INVALID", "DNS source shape is invalid")
        source_class = source["sourceClass"]
        if source_class not in SOURCE_CLASSES or not str(source["sourceName"]).strip():
            raise DnsConvergenceError("DNS_OBSERVATION_INVALID", "DNS source identity is invalid")
        try:
            datetime.fromisoformat(str(source["observedAt"]).replace("Z", "+00:00"))
        except ValueError as exc:
            raise DnsConvergenceError(
                "DNS_OBSERVATION_INVALID", "DNS observation time is invalid"
            ) from exc
        answers = []
        identities = set()
        for answer in source["answers"]:
            if not isinstance(answer, dict) or not {"host", "type", "address"} <= set(answer) <= {
                "host",
                "type",
                "address",
                "ttl",
            }:
                raise DnsConvergenceError("DNS_OBSERVATION_INVALID", "DNS answer shape is invalid")
            host = str(answer["host"]).casefold().rstrip(".")
            kind = answer["type"]
            if host not in normalized_hosts or kind not in {"A", "AAAA"}:
                raise DnsConvergenceError(
                    "DNS_OBSERVATION_INVALID", "DNS answer identity is invalid"
                )
            try:
                address = str(ipaddress.ip_address(answer["address"]))
            except ValueError as exc:
                raise DnsConvergenceError(
                    "DNS_OBSERVATION_INVALID", "DNS answer address is invalid"
                ) from exc
            if (kind == "A") != (ipaddress.ip_address(address).version == 4):
                raise DnsConvergenceError(
                    "DNS_OBSERVATION_INVALID", "DNS answer type mismatches address"
                )
            ttl = answer.get("ttl")
            if ttl is not None and (not isinstance(ttl, int) or not 0 <= ttl <= 86400):
                raise DnsConvergenceError("DNS_OBSERVATION_INVALID", "DNS TTL is invalid")
            identity = (host, kind, address)
            if identity in identities:
                raise DnsConvergenceError("DNS_OBSERVATION_INVALID", "DNS answer is duplicated")
            identities.add(identity)
            answers.append({"host": host, "type": kind, "address": address, "ttl": ttl})
        normalized_sources.append(
            {
                "sourceClass": source_class,
                "sourceName": str(source["sourceName"]),
                "observedAt": str(source["observedAt"]),
                "answers": sorted(
                    answers, key=lambda row: (row["host"], row["type"], row["address"])
                ),
            }
        )
    authoritative = [
        row for row in normalized_sources if row["sourceClass"] == "provider-authoritative"
    ]
    public = [row for row in normalized_sources if row["sourceClass"] == "public-recursive"]
    if not authoritative or not public:
        raise DnsConvergenceError(
            "DNS_OBSERVATION_INVALID", "authoritative and public sources are required"
        )
    unexpected_ipv6 = any(
        answer["type"] == "AAAA" for row in normalized_sources for answer in row["answers"]
    )

    def wrong(rows: list[dict]) -> list[dict]:
        findings = []
        for row in rows:
            for host in normalized_hosts:
                values = [
                    a["address"] for a in row["answers"] if a["host"] == host and a["type"] == "A"
                ]
                if values != [expected]:
                    findings.append({"source": row["sourceName"], "host": host, "answers": values})
        return findings

    core_wrong = wrong(authoritative + public)
    system_wrong = wrong(
        [row for row in normalized_sources if row["sourceClass"] == "system-recursive"]
    )
    if unexpected_ipv6:
        code = "DNS_UNEXPECTED_IPV6"
        action = "remove unexpected AAAA routes by exact record identity"
    elif core_wrong:
        code = "DNS_SPLIT_VIEW"
        action = "wait for or repair authoritative/public DNS convergence"
    elif system_wrong:
        code = "DNS_STALE_RECURSIVE"
        action = "use exact-address verification and allow recursive TTL expiry"
    else:
        code = "OK"
        action = "none"
    normalized = {
        "schemaVersion": 1,
        "domain": domain,
        "expectedAddress": expected,
        "requiredHosts": normalized_hosts,
        "sources": sorted(
            normalized_sources, key=lambda row: (row["sourceClass"], row["sourceName"])
        ),
    }
    return {
        **normalized,
        "ok": code == "OK",
        "code": code,
        "coreFindings": core_wrong,
        "systemFindings": system_wrong,
        "recommendedAction": action,
        "observationDigest": _digest(normalized),
        "credentialReads": 0,
        "providerActions": 0,
        "secretValuesEmitted": 0,
    }
