#!/usr/bin/env python3
"""Strict, dependency-free Base2 site-manifest loader and canonicalizer."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import stat
from pathlib import Path
from typing import Any

TOP_LEVEL = {
    "schemaVersion",
    "siteId",
    "slug",
    "name",
    "legalName",
    "domains",
    "brand",
    "navigation",
    "seo",
    "legal",
    "locales",
    "defaultLocale",
    "consent",
    "analytics",
    "contact",
    "media",
    "search",
    "modules",
    "operationsProfile",
    "previewPolicy",
}
REQUIRED = TOP_LEVEL - {"legalName"}
EXACT_FIELDS = {
    "domain": {"host", "kind"},
    "brand": {"theme", "logo", "voice"},
    "navigation": {"label", "path", "module"},
    "seo": {"titleTemplate", "description", "indexing"},
    "legal": {"privacyPath", "termsPath", "accessibilityPath"},
    "consent": {"mode"},
    "analytics": {"enabled", "provider"},
    "contact": {"enabled", "retentionDays"},
    "media": {"maxBytes", "allowedTypes"},
    "search": {"enabled"},
    "module": {"id", "version", "enabled", "configRef"},
    "previewPolicy": {"ttlMinutes", "idleAction"},
}
ID = re.compile(r"^[a-z][a-z0-9-]{1,62}$")
SITE_ID = re.compile(r"^[a-z][a-z0-9-]{2,62}$")
HOST = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
)
LOCALE = re.compile(r"^[a-z]{2,3}(?:-[A-Z][a-z]{3})?(?:-(?:[A-Z]{2}|[0-9]{3}))?$")
MIME = re.compile(r"^[a-z0-9][a-z0-9.+-]{0,63}/[a-z0-9][a-z0-9.+-]{0,127}$")
VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
SECRET_KEY = re.compile(r"(?:password|secret|token|private.?key|api.?key|credential)", re.I)
SECRET_VALUE = re.compile(
    r"(?:gh[pousr]_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{16,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|bearer\s+[A-Za-z0-9._~+/-]{12,})",
    re.I,
)


class ManifestError(ValueError):
    """Manifest data is invalid or exceeds the supported contract."""


def _object(value: Any, label: str, *, required: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ManifestError(f"{label} must be an object")
    allowed = EXACT_FIELDS[label]
    unknown = set(value) - allowed
    missing = (required or allowed) - set(value)
    if unknown or missing:
        raise ManifestError(f"{label} fields differ: unknown={sorted(unknown)} missing={sorted(missing)}")
    return value


def _safe_path(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value.startswith("/")
        or value.startswith("//")
        or ".." in value.split("/")
        or any(character in value for character in ("?", "#", "\\", "\x00"))
    ):
        raise ManifestError(f"{label} must be a safe local path")
    return value


def _reject_secrets(value: Any, path: str = "manifest") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if SECRET_KEY.search(str(key)):
                raise ManifestError(f"secret-bearing key is forbidden at {path}")
            _reject_secrets(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_secrets(item, f"{path}[{index}]")
    elif isinstance(value, str) and SECRET_VALUE.search(value):
        raise ManifestError(f"raw secret value is forbidden at {path}")


def _load_catalog(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schemaVersion") != 1 or not isinstance(payload.get("modules"), dict):
        raise ManifestError("module catalog is invalid")
    return payload["modules"]


def validate_manifest(
    payload: Any,
    *,
    catalog_path: Path | None = None,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ManifestError("manifest must be an object")
    unknown = set(payload) - TOP_LEVEL
    missing = REQUIRED - set(payload)
    if unknown or missing:
        raise ManifestError(
            f"manifest fields differ: unknown={sorted(unknown)} missing={sorted(missing)}"
        )
    _reject_secrets(payload)
    if payload["schemaVersion"] != 1:
        raise ManifestError("schemaVersion must be 1")
    if not isinstance(payload["siteId"], str) or not SITE_ID.fullmatch(payload["siteId"]):
        raise ManifestError("siteId is invalid")
    if not isinstance(payload["slug"], str) or not ID.fullmatch(payload["slug"]):
        raise ManifestError("slug is invalid")
    for field, maximum in (("name", 120), ("legalName", 200)):
        value = payload.get(field)
        if value is not None and (not isinstance(value, str) or not 1 <= len(value) <= maximum):
            raise ManifestError(f"{field} is invalid")

    domains = payload["domains"]
    if not isinstance(domains, list) or not domains:
        raise ManifestError("domains must be a non-empty list")
    hosts: set[str] = set()
    canonical = 0
    for item in domains:
        domain = _object(item, "domain")
        host = domain["host"]
        if not isinstance(host, str) or host != host.lower() or not HOST.fullmatch(host):
            raise ManifestError("domain host is not canonical")
        if host in hosts:
            raise ManifestError("duplicate domain host")
        hosts.add(host)
        if domain["kind"] not in {"canonical", "redirect", "preview"}:
            raise ManifestError("domain kind is invalid")
        canonical += domain["kind"] == "canonical"
    if canonical != 1:
        raise ManifestError("exactly one canonical domain is required")

    brand = _object(payload["brand"], "brand")
    if not isinstance(brand["theme"], str) or not ID.fullmatch(brand["theme"]):
        raise ManifestError("brand theme is invalid")
    _safe_path(brand["logo"], "brand logo")
    if not isinstance(brand["voice"], str) or not 1 <= len(brand["voice"]) <= 500:
        raise ManifestError("brand voice is invalid")

    catalog = _load_catalog(
        catalog_path
        or Path(__file__).resolve().parents[2] / "shared" / "config" / "module-catalog.json"
    )
    modules = payload["modules"]
    if not isinstance(modules, list):
        raise ManifestError("modules must be a list")
    installed: dict[str, dict[str, Any]] = {}
    for item in modules:
        module = _object(item, "module", required={"id", "version", "enabled"})
        module_id = module["id"]
        if not isinstance(module_id, str) or not ID.fullmatch(module_id) or module_id in installed:
            raise ManifestError("module ID is invalid or duplicated")
        if module_id not in catalog:
            raise ManifestError("module is not in the compatibility catalog")
        if (
            not isinstance(module["version"], str)
            or not VERSION.fullmatch(module["version"])
            or module["version"] not in catalog[module_id].get("versions", [])
        ):
            raise ManifestError("module version is unsupported")
        if not isinstance(module["enabled"], bool):
            raise ManifestError("module enabled must be Boolean")
        if "configRef" in module and not re.fullmatch(
            r"config://[a-z][a-z0-9-]{1,62}/[a-z][a-z0-9._-]{1,127}", module["configRef"]
        ):
            raise ManifestError("module configRef is unsafe")
        installed[module_id] = module
    for module_id, module in installed.items():
        if not module["enabled"]:
            continue
        for dependency in catalog[module_id].get("requires", []):
            if dependency not in installed or not installed[dependency]["enabled"]:
                raise ManifestError(f"enabled module {module_id} requires {dependency}")

    navigation = payload["navigation"]
    if not isinstance(navigation, list):
        raise ManifestError("navigation must be a list")
    navigation_paths: set[str] = set()
    for item in navigation:
        entry = _object(item, "navigation", required={"label", "path"})
        if not isinstance(entry["label"], str) or not entry["label"].strip():
            raise ManifestError("navigation label is invalid")
        path = _safe_path(entry["path"], "navigation path")
        if path in navigation_paths:
            raise ManifestError("duplicate navigation path")
        navigation_paths.add(path)
        module_id = entry.get("module")
        if module_id and (module_id not in installed or not installed[module_id]["enabled"]):
            raise ManifestError("navigation references a disabled or absent module")

    seo = _object(payload["seo"], "seo")
    if (
        not isinstance(seo["titleTemplate"], str)
        or seo["titleTemplate"].count("%s") != 1
        or not isinstance(seo["description"], str)
        or not 1 <= len(seo["description"]) <= 320
        or seo["indexing"] not in {"allow", "deny"}
    ):
        raise ManifestError("SEO contract is invalid")
    legal = _object(payload["legal"], "legal")
    for key, value in legal.items():
        _safe_path(value, f"legal {key}")

    locales = payload["locales"]
    if (
        not isinstance(locales, list)
        or not locales
        or len(locales) != len(set(locales))
        or any(not isinstance(item, str) or not LOCALE.fullmatch(item) for item in locales)
    ):
        raise ManifestError("locales are invalid or duplicated")
    if payload["defaultLocale"] not in locales:
        raise ManifestError("defaultLocale must be in locales")

    consent = _object(payload["consent"], "consent")
    if consent["mode"] not in {"disabled", "essential-only", "opt-in"}:
        raise ManifestError("consent mode is invalid")
    analytics = _object(payload["analytics"], "analytics")
    if not isinstance(analytics["enabled"], bool) or analytics["provider"] not in {
        "none",
        "adapter",
    }:
        raise ManifestError("analytics contract is invalid")
    if analytics["enabled"] != (analytics["provider"] == "adapter"):
        raise ManifestError("analytics provider and enabled state disagree")
    contact = _object(payload["contact"], "contact")
    if not isinstance(contact["enabled"], bool) or not isinstance(
        contact["retentionDays"], int
    ) or not 1 <= contact["retentionDays"] <= 3650:
        raise ManifestError("contact contract is invalid")
    media = _object(payload["media"], "media")
    if not isinstance(media["maxBytes"], int) or not 1 <= media["maxBytes"] <= 100_000_000:
        raise ManifestError("media maxBytes is invalid")
    allowed_types = media["allowedTypes"]
    if (
        not isinstance(allowed_types, list)
        or not allowed_types
        or len(allowed_types) != len(set(allowed_types))
        or any(not isinstance(item, str) or not MIME.fullmatch(item) for item in allowed_types)
    ):
        raise ManifestError("media allowedTypes are invalid")
    search = _object(payload["search"], "search")
    if not isinstance(search["enabled"], bool):
        raise ManifestError("search enabled must be Boolean")
    if search["enabled"] and ("search" not in installed or not installed["search"]["enabled"]):
        raise ManifestError("search capability requires the enabled search module")
    if payload["operationsProfile"] not in {"local", "preview", "staging", "production"}:
        raise ManifestError("operationsProfile is invalid")
    preview = _object(payload["previewPolicy"], "previewPolicy")
    if (
        not isinstance(preview["ttlMinutes"], int)
        or not 15 <= preview["ttlMinutes"] <= 1440
        or preview["idleAction"] not in {"destroy", "retain"}
    ):
        raise ManifestError("previewPolicy is invalid")
    if payload["operationsProfile"] == "preview" and preview["idleAction"] != "destroy":
        raise ManifestError("preview operations must destroy idle resources")
    return copy.deepcopy(payload)


def canonical_bytes(payload: dict[str, Any]) -> bytes:
    validated = validate_manifest(payload)
    return json.dumps(validated, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def manifest_digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def load_manifest(path: Path) -> dict[str, Any]:
    path = path.expanduser()
    if path.is_symlink():
        raise ManifestError("manifest path must be a real file")
    path = path.resolve()
    if not path.is_file():
        raise ManifestError("manifest path must be a real file")
    mode = stat.S_IMODE(path.stat(follow_symlinks=False).st_mode)
    if mode & 0o002:
        raise ManifestError("manifest must not be world-writable")
    if path.stat().st_size > 1_000_000:
        raise ManifestError("manifest exceeds the size limit")
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ManifestError("manifest is not valid UTF-8 JSON") from exc
    return validate_manifest(payload)
