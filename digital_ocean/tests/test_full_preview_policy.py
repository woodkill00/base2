from __future__ import annotations

from pathlib import Path

import pytest

from digital_ocean.scripts.python.full_preview_policy import (
    PolicyError,
    full_preview_policy,
    select_dynamic_template,
    validate_owner_cidrs,
)


ROOT = Path(__file__).resolve().parents[2]


def test_exact_public_host_cidrs_are_canonical_and_bounded():
    assert validate_owner_cidrs(["8.8.8.8/32", "2606:4700:4700::1111/128"]) == (
        "8.8.8.8/32",
        "2606:4700:4700::1111/128",
    )
    with pytest.raises(PolicyError, match="duplicate"):
        validate_owner_cidrs(["8.8.8.8/32", "8.8.8.8/32"])
    with pytest.raises(PolicyError, match="at most"):
        validate_owner_cidrs([f"8.8.8.{index}/32" for index in range(1, 6)])


@pytest.mark.parametrize(
    "value",
    [
        "127.0.0.1/32",
        "10.0.0.1/32",
        "192.168.1.1/32",
        "169.254.1.1/32",
        "224.0.0.1/32",
        "0.0.0.0/32",
        "192.0.2.1/32",
        "198.51.100.0/24",
        "2001:db8::1/128",
        "::1/128",
        "not-a-network",
    ],
)
def test_hostile_or_nonpublic_owner_networks_fail_closed(value):
    with pytest.raises(PolicyError):
        validate_owner_cidrs([value])


def test_full_preview_route_matrix_is_exact_and_protected():
    policy = full_preview_policy("woodkilldev.com", ["8.8.8.8/32"])
    assert policy["mode"] == "full-preview"
    assert policy["profileId"] == "base2-obsidian"
    assert policy["certificateMode"] == "letsencrypt-staging-only"
    by_service = {row["service"]: row for row in policy["routes"]}
    assert by_service["frontend"]["exposure"] == "public"
    assert by_service["api-index"]["exposure"] == "public"
    for service in ("django-admin", "swagger", "traefik", "pgadmin", "flower"):
        assert by_service[service]["exposure"] == "protected-edge"
        assert by_service[service]["edgeAuth"] is True
        assert by_service[service]["ownerAllowlist"] is True


def test_mode_selection_preserves_minimal_canary_and_rejects_unknown():
    assert select_dynamic_template("minimal-canary").name == "dynamic-canary.yml"
    assert select_dynamic_template("full-preview").name == "dynamic-full-preview.yml"
    assert select_dynamic_template("local").name == "dynamic.yml"
    with pytest.raises(PolicyError, match="mode"):
        select_dynamic_template("production")


def test_full_preview_template_contains_only_expected_host_families_and_staging_config():
    template = (ROOT / "traefik/dynamic-full-preview.yml").read_text()
    for label in ("admin", "swagger", "traefik", "pgadmin", "flower"):
        assert f"{label}." in template or f"${{{label.upper()}_DNS_LABEL}}" in template
    assert "owner-allow-ip" in template
    assert "operator-basic-auth" in template
    static = (ROOT / "traefik/traefik.yml").read_text()
    assert "acme-staging-v02.api.letsencrypt.org" in static
    assert "acme-v02.api.letsencrypt.org/directory" not in static
