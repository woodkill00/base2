#!/usr/bin/env python3
"""Strict, non-executing parser and normalizer for deployment environment files."""

from __future__ import annotations

import ast
import os
import re
from collections.abc import Mapping

KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
TEMPLATE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
REGION = re.compile(r"^[a-z]{2,4}[0-9]{1,2}$")
NAME = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
IMAGE = re.compile(r"^(?:[0-9]+|[a-z0-9][a-z0-9._-]{1,127})$")
SENSITIVE = re.compile(r"(?:TOKEN|PASSWORD|SECRET|PRIVATE|SPACES_KEY|SSH_KEY_ID)$")

KNOWN_DO_KEYS = {
    "DO_ALERT_EMAIL",
    "DO_API_BASE_URL",
    "DO_API_IMAGE",
    "DO_API_REGION",
    "DO_API_RETRY_COUNT",
    "DO_API_RETRY_DELAY",
    "DO_API_RETRY_DELAY_SECONDS",
    "DO_API_RETRY_LIMIT",
    "DO_API_SIZE",
    "DO_API_SSH_KEYS",
    "DO_API_TIMEOUT",
    "DO_API_TIMEOUT_SECONDS",
    "DO_API_TOKEN",
    "DO_APP_AUTOSCALE",
    "DO_APP_BRANCH",
    "DO_APP_DOMAIN",
    "DO_APP_ENV_EXAMPLE",
    "DO_APP_HEALTHCHECK_INTERVAL",
    "DO_APP_HEALTHCHECK_PATH",
    "DO_APP_HEALTHCHECK_THRESHOLD",
    "DO_APP_HEALTHCHECK_TIMEOUT",
    "DO_APP_MAX_INSTANCES",
    "DO_APP_MIN_INSTANCES",
    "DO_APP_NAME",
    "DO_APP_REPO_URL",
    "DO_APP_SPEC_PATH",
    "DO_BACKUPS_ENABLED",
    "DO_DEPLOY_TIMEOUT",
    "DO_DISABLE_BUILDKIT",
    "DO_DOMAIN",
    "DO_DROPLET_COUNT",
    "DO_DROPLET_IMAGE",
    "DO_DROPLET_NAME",
    "DO_DROPLET_PRIVATE_NETWORKING",
    "DO_DROPLET_SIZE",
    "DO_DROPLET_VOLUME_ID",
    "DO_FIREWALL_ID",
    "DO_GIT_REPO",
    "DO_IMAGE_TAG",
    "DO_IPV6_ENABLED",
    "DO_IPV6_WAIT_TIMEOUT",
    "DO_IP_POLL_INTERVAL_SECONDS",
    "DO_IP_POLL_TIMEOUT_SECONDS",
    "DO_LOG_LEVEL",
    "DO_MONITORING_ENABLED",
    "DO_OAUTH_CLIENT_ID",
    "DO_OAUTH_CLIENT_SECRET",
    "DO_PROJECT_ID",
    "DO_REGISTRY_NAME",
    "DO_REPOSITORY_NAME",
    "DO_SKIP_DNS",
    "DO_SPACES_KEY",
    "DO_SPACES_REGION",
    "DO_SPACES_SECRET",
    "DO_SSH_KEY_ID",
    "DO_TAGS",
    "DO_TEARDOWN_TIMEOUT",
    "DO_USER_DATA_PATH",
    "DO_VPC_UUID",
}


class DeployConfigError(ValueError):
    """Raised for ambiguous or invalid deployment configuration."""


def _parse_value(raw: str, line_number: int) -> str:
    value = raw.strip()
    if not value:
        return ""
    if value[0] in {'"', "'"}:
        quote = value[0]
        if len(value) < 2 or not value.endswith(quote):
            raise DeployConfigError(f"line {line_number}: unterminated quote")
        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError) as exc:
            raise DeployConfigError(f"line {line_number}: invalid quoted value") from exc
        if not isinstance(parsed, str):
            raise DeployConfigError(f"line {line_number}: quoted value must be text")
        return parsed
    return re.split(r"\s+#", value, maxsplit=1)[0].rstrip()


def parse_env_text(text: str) -> dict[str, str]:
    if not isinstance(text, str):
        raise DeployConfigError("environment content must be text")
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise DeployConfigError(f"line {line_number}: missing equals")
        raw_key, raw_value = line.split("=", 1)
        key = raw_key.strip()
        if not KEY.fullmatch(key):
            raise DeployConfigError(f"line {line_number}: invalid key")
        if key in values:
            raise DeployConfigError(f"line {line_number}: duplicate key {key}")
        if key.startswith("DO_") and key not in KNOWN_DO_KEYS:
            raise DeployConfigError(f"line {line_number}: unknown DigitalOcean key {key}")
        values[key] = _parse_value(raw_value, line_number)
    return values


def _expand(value: str, environment: Mapping[str, str]) -> str:
    current = value
    for _ in range(5):
        updated = TEMPLATE.sub(
            lambda match: environment.get(match.group(1), match.group(0)), current
        )
        if updated == current:
            return updated
        current = updated
    return current


def normalize_deploy_config(
    values: Mapping[str, str], *, environment: Mapping[str, str] | None = None
) -> dict[str, str]:
    expansion = {**os.environ, **(environment or {}), **values}
    normalized = {key: _expand(str(value).strip(), expansion) for key, value in values.items()}
    validators = {
        "DO_API_REGION": REGION,
        "DO_APP_NAME": NAME,
        "DO_DROPLET_NAME": NAME,
        "DO_API_IMAGE": IMAGE,
        "DO_DROPLET_IMAGE": IMAGE,
    }
    for key, pattern in validators.items():
        value = normalized.get(key)
        if value is not None and not pattern.fullmatch(value):
            raise DeployConfigError(f"{key} is malformed")
    unresolved = sorted(key for key, value in normalized.items() if "${" in value)
    if unresolved:
        raise DeployConfigError("unresolved template in: " + ", ".join(unresolved))
    return normalized


def load_deploy_config(path: str | os.PathLike[str]) -> dict[str, str]:
    try:
        with open(path, encoding="utf-8", newline=None) as handle:
            return normalize_deploy_config(parse_env_text(handle.read()))
    except OSError as exc:
        raise DeployConfigError("deployment environment file is unavailable") from exc


def redact_config(values: Mapping[str, str]) -> dict[str, str]:
    return {
        key: "[REDACTED]" if SENSITIVE.search(key) else str(value)
        for key, value in sorted(values.items())
    }
