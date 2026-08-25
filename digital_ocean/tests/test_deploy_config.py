from __future__ import annotations

from pathlib import Path

import pytest

from digital_ocean.scripts.python.deploy_config import (
    KNOWN_DO_KEYS,
    DeployConfigError,
    load_deploy_config,
    normalize_deploy_config,
    parse_env_text,
    redact_config,
)


def test_quotes_whitespace_crlf_and_comments_are_normalized():
    parsed = parse_env_text(
        '  # comment\r\nDO_API_REGION = "fra1"\r\nDO_APP_NAME=base2-preview # note\r\n'
    )
    assert parsed == {"DO_API_REGION": "fra1", "DO_APP_NAME": "base2-preview"}


def test_hash_inside_quotes_is_preserved():
    assert parse_env_text("DO_API_TOKEN='token#value'\n") == {"DO_API_TOKEN": "token#value"}


@pytest.mark.parametrize(
    "text,match",
    [
        ("DO_API_REGION=fra1\nDO_API_REGION=nyc3\n", "duplicate"),
        ("DO_UNKNOWN=value\n", "unknown DigitalOcean key"),
        ('DO_API_REGION="fra1\n', "unterminated quote"),
        ("NOT A KEY=value\n", "invalid key"),
        ("DO_API_TOKEN\n", "missing equals"),
    ],
)
def test_malformed_or_ambiguous_env_fails(text, match):
    with pytest.raises(DeployConfigError, match=match):
        parse_env_text(text)


@pytest.mark.parametrize(
    "field,value",
    [
        ("DO_API_REGION", "not-a-region"),
        ("DO_APP_NAME", "Bad Name"),
        ("DO_DROPLET_NAME", "-leading-dash"),
        ("DO_API_IMAGE", "bad image!"),
    ],
)
def test_malformed_provider_identity_fails(field, value):
    values = {
        "DO_API_REGION": "fra1",
        "DO_APP_NAME": "base2",
        "DO_DROPLET_NAME": "base2-preview",
        "DO_API_IMAGE": "ubuntu-22-04-x64",
    }
    values[field] = value
    with pytest.raises(DeployConfigError, match=field):
        normalize_deploy_config(values)


def test_templates_expand_before_identity_validation():
    result = normalize_deploy_config(
        {
            "DO_API_REGION": "fra1",
            "DO_APP_NAME": "${PROJECT_NAME}",
            "DO_DROPLET_NAME": "${PROJECT_NAME}-preview",
            "DO_API_IMAGE": "ubuntu-22-04-x64",
        },
        environment={"PROJECT_NAME": "base2"},
    )
    assert result["DO_APP_NAME"] == "base2"
    assert result["DO_DROPLET_NAME"] == "base2-preview"


def test_secret_redaction_never_returns_values():
    redacted = redact_config(
        {
            "DO_API_TOKEN": "secret-value",
            "DO_SPACES_SECRET": "another-secret",
            "DO_API_REGION": "fra1",
        }
    )
    assert redacted == {
        "DO_API_REGION": "fra1",
        "DO_API_TOKEN": "[REDACTED]",
        "DO_SPACES_SECRET": "[REDACTED]",
    }
    assert "secret-value" not in str(redacted)


def test_example_has_no_unknown_provider_keys():
    root = Path(__file__).resolve().parents[2]
    keys = {
        line.strip().split("=", 1)[0]
        for line in (root / ".env.example").read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("DO_") and "=" in line
    }
    assert keys <= KNOWN_DO_KEYS


def test_missing_file_has_typed_sanitized_error(tmp_path):
    with pytest.raises(DeployConfigError, match="environment file is unavailable") as error:
        load_deploy_config(tmp_path / "contains-secret-in-name.env")
    assert "secret" not in str(error.value)
