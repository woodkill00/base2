#!/usr/bin/env python3
"""Verify test-only HTTPS endpoints against an isolated pinned trust store."""

from __future__ import annotations

import argparse
import socket
import ssl
import time
from pathlib import Path


class StagingTLSProbeError(RuntimeError):
    pass


def verify_host(
    *, hostname: str, connect_ip: str, port: int, ca_file: Path, timeout: float
) -> tuple[str, ...]:
    if not ca_file.is_file():
        raise StagingTLSProbeError("staging_trust_store_missing")
    context = ssl.create_default_context(cafile=str(ca_file))
    if context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname:
        raise StagingTLSProbeError("staging_tls_verification_disabled")
    with (
        socket.create_connection((connect_ip, port), timeout=timeout) as raw,
        context.wrap_socket(raw, server_hostname=hostname) as secured,
    ):
        certificate = secured.getpeercert()
    sans = tuple(
        value
        for kind, value in certificate.get("subjectAltName", ())
        if kind == "DNS"
    )
    if not sans:
        raise StagingTLSProbeError("staging_certificate_dns_san_missing")
    return sans


def wait_for_hosts(
    *,
    hosts: list[str],
    connect_ip: str,
    port: int,
    ca_file: Path,
    wait_seconds: int,
    retry_seconds: float = 5.0,
) -> dict[str, tuple[str, ...]]:
    deadline = time.monotonic() + wait_seconds
    pending = set(hosts)
    verified: dict[str, tuple[str, ...]] = {}
    errors: dict[str, str] = {}
    while pending and time.monotonic() < deadline:
        for host in sorted(pending):
            try:
                verified[host] = verify_host(
                    hostname=host,
                    connect_ip=connect_ip,
                    port=port,
                    ca_file=ca_file,
                    timeout=5,
                )
                pending.remove(host)
            except (OSError, ssl.SSLError, StagingTLSProbeError) as error:
                errors[host] = type(error).__name__
        if pending:
            time.sleep(retry_seconds)
    if pending:
        detail = ",".join(f"{host}:{errors.get(host, 'unverified')}" for host in sorted(pending))
        raise StagingTLSProbeError(f"staging_tls_wait_expired:{detail}")
    return verified


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ca-file", type=Path, required=True)
    parser.add_argument("--connect-ip", required=True)
    parser.add_argument("--port", type=int, default=443)
    parser.add_argument("--wait-seconds", type=int, default=600)
    parser.add_argument("--hosts", nargs="+", required=True)
    args = parser.parse_args(argv)
    try:
        verified = wait_for_hosts(
            hosts=args.hosts,
            connect_ip=args.connect_ip,
            port=args.port,
            ca_file=args.ca_file,
            wait_seconds=args.wait_seconds,
        )
    except StagingTLSProbeError as error:
        print(f"ERROR: {error}")
        return 2
    for host, sans in sorted(verified.items()):
        print(f"OK: {host} verified; sans={','.join(sans)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
