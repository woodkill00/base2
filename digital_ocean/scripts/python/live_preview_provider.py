#!/usr/bin/env python3
"""Bounded live DigitalOcean adapter for an exact approved preview plan."""

from __future__ import annotations

from dataclasses import dataclass
import http.client
import ipaddress
import json
from pathlib import Path
import re
import stat
import time
from typing import Any, Protocol
import urllib.parse


HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SAFE_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
SAFE_ZONE = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
)
SAFE_SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SAFE_TAG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,254}$")


class LiveProviderError(RuntimeError):
    """The live request exceeded or contradicted its reviewed authority."""


class DigitalOceanHttpError(RuntimeError):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


class _DigitalOceanApi:
    def __init__(self, token: str) -> None:
        if not isinstance(token, str) or not token:
            raise LiveProviderError("DigitalOcean token is required")
        self._token = token

    def request(self, method: str, path: str, payload: dict | None = None) -> dict:
        if method not in {"GET", "POST", "PUT", "DELETE"}:
            raise LiveProviderError("HTTP method is outside exact adapter authority")
        if not path.startswith("/v2/") or ".." in path or "//" in path:
            raise LiveProviderError("DigitalOcean API path is unsafe")
        body = None if payload is None else json.dumps(payload, separators=(",", ":"))
        connection = http.client.HTTPSConnection("api.digitalocean.com", timeout=30)
        try:
            connection.request(
                method,
                path,
                body=body,
                headers={
                    "Authorization": "Bearer " + self._token,
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
            response = connection.getresponse()
            raw = response.read()
            if response.status not in {200, 201, 202, 204}:
                raise DigitalOceanHttpError(
                    response.status, f"DigitalOcean API returned HTTP {response.status}"
                )
            return {} if not raw else json.loads(raw.decode("utf-8"))
        finally:
            connection.close()


class _DropletApi:
    def __init__(self, api: _DigitalOceanApi) -> None:
        self.api = api

    def create(self, payload: dict) -> dict:
        return self.api.request("POST", "/v2/droplets", payload)

    def get(self, provider_id: int) -> dict:
        return self.api.request("GET", f"/v2/droplets/{int(provider_id)}")

    def list(self, tag_name: str | None = None) -> dict:
        suffix = ""
        if tag_name:
            suffix = "?" + urllib.parse.urlencode({"tag_name": tag_name, "per_page": 200})
        return self.api.request("GET", "/v2/droplets" + suffix)

    def delete(self, provider_id: int) -> dict:
        return self.api.request("DELETE", f"/v2/droplets/{int(provider_id)}")


class _DomainApi:
    def __init__(self, api: _DigitalOceanApi) -> None:
        self.api = api

    @staticmethod
    def _zone(zone: str) -> str:
        if not SAFE_ZONE.fullmatch(zone):
            raise LiveProviderError("DNS zone is unsafe")
        return urllib.parse.quote(zone, safe="")

    def list_records(self, zone: str) -> dict:
        return self.api.request(
            "GET", f"/v2/domains/{self._zone(zone)}/records?per_page=200"
        )

    def create_record(self, zone: str, payload: dict) -> dict:
        return self.api.request(
            "POST", f"/v2/domains/{self._zone(zone)}/records", payload
        )

    def update_record(self, zone: str, record_id: int, payload: dict) -> dict:
        return self.api.request(
            "PUT", f"/v2/domains/{self._zone(zone)}/records/{int(record_id)}", payload
        )

    def delete_record(self, zone: str, record_id: int) -> dict:
        return self.api.request(
            "DELETE", f"/v2/domains/{self._zone(zone)}/records/{int(record_id)}"
        )


class DigitalOceanHttpClient:
    """Dependency-free client exposing only Droplet and Domain operations."""

    def __init__(self, token: str) -> None:
        api = _DigitalOceanApi(token)
        self.droplets = _DropletApi(api)
        self.domains = _DomainApi(api)


class RemoteBootstrap(Protocol):
    def deploy(self, ip_address: str, config: "LivePreviewConfig") -> None: ...
    def health(self, ip_address: str, fqdn: str) -> bool: ...


@dataclass(frozen=True)
class LivePreviewConfig:
    source_commit: str
    plan_digest: str
    archive_sha256: str
    source_archive: Path
    ssh_private_key: Path
    ssh_key_id: int
    droplet_name: str
    region: str
    size: str
    image: str
    zone: str
    record_name: str
    fqdn: str
    admission_tag: str = ""
    maximum_wait_attempts: int = 60
    wait_interval_seconds: float = 5.0

    def validate(self) -> "LivePreviewConfig":
        if not HEX40.fullmatch(self.source_commit):
            raise LiveProviderError("exact lowercase source commit is required")
        if not HEX64.fullmatch(self.plan_digest) or not HEX64.fullmatch(
            self.archive_sha256
        ):
            raise LiveProviderError("plan and archive digests must be exact SHA-256")
        if not SAFE_LABEL.fullmatch(self.droplet_name):
            raise LiveProviderError("droplet name is unsafe")
        if not SAFE_ZONE.fullmatch(self.zone):
            raise LiveProviderError("DNS zone is unsafe")
        if self.record_name in {"", "@", "*"}:
            raise LiveProviderError("root DNS and wildcard records are forbidden")
        if not SAFE_LABEL.fullmatch(self.record_name):
            raise LiveProviderError("DNS record name is unsafe")
        if self.fqdn != f"{self.record_name}.{self.zone}":
            raise LiveProviderError("fqdn does not match the exact DNS record")
        if self.admission_tag and not SAFE_TAG.fullmatch(self.admission_tag):
            raise LiveProviderError("admission tag is unsafe")
        for label, value in (
            ("region", self.region),
            ("size", self.size),
            ("image", self.image),
        ):
            if not SAFE_SLUG.fullmatch(value):
                raise LiveProviderError(f"{label} is unsafe")
        if not isinstance(self.ssh_key_id, int) or self.ssh_key_id < 1:
            raise LiveProviderError("existing SSH key ID is required")
        if not 1 <= self.maximum_wait_attempts <= 60:
            raise LiveProviderError("wait attempts exceed the bounded policy")
        if not 0 <= self.wait_interval_seconds <= 15:
            raise LiveProviderError("wait interval exceeds the bounded policy")
        for label, path in (
            ("source archive", self.source_archive),
            ("SSH private key", self.ssh_private_key),
        ):
            if not path.is_file() or path.is_symlink():
                raise LiveProviderError(f"{label} must be a real file")
        key_mode = stat.S_IMODE(self.ssh_private_key.stat(follow_symlinks=False).st_mode)
        if key_mode & 0o077:
            raise LiveProviderError("SSH private key permissions are unsafe")
        return self


def _status_code(error: Exception) -> int | None:
    return getattr(error, "status_code", None) or getattr(error, "status", None)


def _public_ipv4(droplet: dict[str, Any]) -> str | None:
    for network in ((droplet.get("networks") or {}).get("v4") or []):
        if network.get("type") != "public":
            continue
        try:
            return str(ipaddress.IPv4Address(str(network.get("ip_address") or "")))
        except ipaddress.AddressValueError:
            continue
    return None


class LiveDigitalOceanProvider:
    """Implements only the provider-neutral preview protocol's exact surface."""

    def __init__(
        self,
        client: Any,
        config: LivePreviewConfig,
        remote: RemoteBootstrap,
        *,
        sleep=time.sleep,
    ) -> None:
        self.client = client
        self.config = config.validate()
        self.remote = remote
        self.sleep = sleep

    @staticmethod
    def _supported(provider: str, kind: str) -> None:
        if (provider, kind) != ("digitalocean", "droplet"):
            raise LiveProviderError("resource provider/kind is outside exact approval")

    def provision(self, ownership_tag: str) -> dict[str, Any]:
        if not SAFE_TAG.fullmatch(ownership_tag):
            raise LiveProviderError("ownership tag is unsafe")
        existing = self.list_owned_resources(ownership_tag)
        if len(existing) > 1:
            raise LiveProviderError("multiple exact-owned resources require owner review")
        if existing:
            row = existing[0]
            if row.get("name") != self.config.droplet_name or not str(row.get("id") or ""):
                raise LiveProviderError("existing exact-owned resource identity differs")
            return row
        tags = [ownership_tag]
        if self.config.admission_tag and self.config.admission_tag != ownership_tag:
            tags.append(self.config.admission_tag)
        payload = {
            "name": self.config.droplet_name,
            "region": self.config.region,
            "size": self.config.size,
            "image": self.config.image,
            "ssh_keys": [self.config.ssh_key_id],
            "backups": False,
            "ipv6": False,
            "monitoring": False,
            "tags": tags,
        }
        try:
            droplet = (self.client.droplets.create(payload) or {}).get("droplet") or {}
        except Exception:
            reconciled = self.list_owned_resources(ownership_tag)
            if (
                len(reconciled) == 1
                and reconciled[0].get("name") == self.config.droplet_name
                and str(reconciled[0].get("id") or "")
            ):
                return reconciled[0]
            raise
        if not str(droplet.get("id") or "") or ownership_tag not in (
            droplet.get("tags") or []
        ):
            raise LiveProviderError("created Droplet lacks exact identity or ownership")
        return droplet

    def _wait_ready(self, provider_id: str) -> tuple[dict[str, Any], str]:
        for attempt in range(self.config.maximum_wait_attempts):
            droplet = self.get_resource("digitalocean", "droplet", provider_id)
            if droplet is None:
                raise LiveProviderError("created Droplet disappeared")
            address = _public_ipv4(droplet)
            if droplet.get("status") == "active" and address:
                return droplet, address
            if attempt + 1 < self.config.maximum_wait_attempts:
                self.sleep(self.config.wait_interval_seconds)
        raise LiveProviderError("Droplet readiness wait exhausted")

    def bootstrap(self, provider_id: str) -> None:
        _droplet, address = self._wait_ready(provider_id)
        self.remote.deploy(address, self.config)

    def dns_values(self, provider_id: str) -> list[str]:
        _droplet, address = self._wait_ready(provider_id)
        return [address]

    def health(self, provider_id: str) -> bool:
        try:
            _droplet, address = self._wait_ready(provider_id)
            return self.remote.health(address, self.config.fqdn) is True
        except Exception:
            return False

    def _records(self, zone: str, name: str, record_type: str) -> list[dict[str, Any]]:
        if (zone, name, record_type) != (
            self.config.zone,
            self.config.record_name,
            "A",
        ):
            raise LiveProviderError("DNS request is outside exact approval")
        rows = (self.client.domains.list_records(zone) or {}).get("domain_records") or []
        return [
            row
            for row in rows
            if row.get("name") == name and row.get("type") == record_type
        ]

    def read_values(self, zone: str, name: str, record_type: str) -> list[str]:
        rows = self._records(zone, name, record_type)
        return sorted(str(row.get("data") or "") for row in rows)

    def replace_values(
        self, zone: str, name: str, record_type: str, values: list[str]
    ) -> None:
        rows = self._records(zone, name, record_type)
        if len(rows) > 1:
            raise LiveProviderError("duplicate exact DNS records require owner review")
        if len(values) > 1:
            raise LiveProviderError("canary DNS requires exactly one or zero values")
        if not values:
            if rows:
                self.client.domains.delete_record(zone, rows[0]["id"])
            return
        try:
            desired = str(ipaddress.IPv4Address(values[0]))
        except ipaddress.AddressValueError as exc:
            raise LiveProviderError("canary DNS value must be one public IPv4 address") from exc
        payload = {"type": "A", "name": name, "data": desired, "ttl": 60}
        if not rows:
            self.client.domains.create_record(zone, payload)
        elif str(rows[0].get("data") or "") != desired:
            self.client.domains.update_record(zone, rows[0]["id"], payload)

    def get_resource(
        self, provider: str, kind: str, provider_id: str
    ) -> dict[str, Any] | None:
        self._supported(provider, kind)
        try:
            return (self.client.droplets.get(int(provider_id)) or {}).get("droplet")
        except Exception as exc:
            if _status_code(exc) == 404:
                return None
            raise

    def delete_resource(self, provider: str, kind: str, provider_id: str) -> None:
        self._supported(provider, kind)
        self.client.droplets.delete(int(provider_id))

    def list_owned_resources(self, ownership_tag: str) -> list[dict[str, Any]]:
        if not SAFE_TAG.fullmatch(ownership_tag):
            raise LiveProviderError("ownership tag is unsafe")
        return (self.client.droplets.list(tag_name=ownership_tag) or {}).get(
            "droplets"
        ) or []
