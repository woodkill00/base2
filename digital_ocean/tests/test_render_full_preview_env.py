from __future__ import annotations

import json

import pytest

from digital_ocean.scripts.python.deploy_config import parse_env_text
from digital_ocean.scripts.python import render_full_preview_env
from digital_ocean.scripts.python.render_full_preview_env import RenderError, render


def test_private_full_preview_render_is_explicit_and_secret_silent(tmp_path, capsys):
    source = tmp_path / "source.env"
    source.write_text(
        "PROJECT_NAME=x\nWEBSITE_DOMAIN=x.example\nSITE_PROFILE=ember-studio\n"
        "TRAEFIK_CANARY_MODE=true\nTRAEFIK_PREVIEW_MODE=minimal-canary\n"
        "API_DOCS_ENABLED=false\nDJANGO_ALLOWED_HOSTS=x\nCORS_ALLOW_ORIGINS=x\n"
        "FRONTEND_URL=x\nTRAEFIK_DASH_BASIC_USERS=disabled\nFLOWER_BASIC_USERS=disabled\n"
        "OWNER_ALLOWLIST_CSV=127.0.0.1/32\nTP_DJANGO_SECRET_KEY=YOUR_SECRET\n",
        encoding="utf-8",
    )
    target = tmp_path / "private.env"
    receipt = render(
        source,
        target,
        "woodkilldev.com",
        "base2-full-preview",
        ["8.8.8.8/32"],
        operator_basic_auth="preview:$apr1$abc$hash",
        flower_basic_auth="flower:$apr1$def$hash",
    )
    values = parse_env_text(target.read_text())
    assert values["SITE_PROFILE"] == "base2-obsidian"
    assert values["TRAEFIK_PREVIEW_MODE"] == "full-preview"
    assert values["TRAEFIK_CANARY_MODE"] == "false"
    assert values["API_DOCS_ENABLED"] == "true"
    assert values["OWNER_ALLOWLIST_CSV"] == "8.8.8.8/32"
    assert values["DJANGO_ALLOWED_HOSTS"] == "woodkilldev.com,admin.woodkilldev.com,django,api"
    assert values["CORS_ALLOW_ORIGINS"] == "https://woodkilldev.com"
    assert "$$apr1$$" in values["TRAEFIK_DASH_BASIC_USERS"]
    assert receipt == {"ok": True, "mode": "full-preview", "secretValuesEmitted": 0, "ownerCidrCount": 1}
    assert capsys.readouterr().out == ""
    assert target.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize(
    "operator,flower",
    [
        ("disabled", "flower:$apr1$def$hash"),
        ("preview:plain", "flower:$apr1$def$hash"),
        ("preview:$apr1$abc$hash", "same:$apr1$abc$hash"),
        ("preview:$apr1$abc$hash\nINJECT=1", "flower:$apr1$def$hash"),
    ],
)
def test_invalid_or_reused_edge_credentials_fail_closed(tmp_path, operator, flower):
    source = tmp_path / "source.env"
    source.write_text("PROJECT_NAME=x\nWEBSITE_DOMAIN=x.example\n", encoding="utf-8")
    with pytest.raises(RenderError):
        render(source, tmp_path / "out.env", "woodkilldev.com", "base2-full-preview", ["8.8.8.8/32"], operator_basic_auth=operator, flower_basic_auth=flower)


def test_renderer_rejects_private_or_broad_owner_network_before_output(tmp_path):
    source = tmp_path / "source.env"
    source.write_text("PROJECT_NAME=x\n", encoding="utf-8")
    with pytest.raises(Exception):
        render(source, tmp_path / "out.env", "woodkilldev.com", "base2-full-preview", ["192.168.1.0/24"], operator_basic_auth="preview:$apr1$abc$hash", flower_basic_auth="flower:$apr1$def$hash")
    assert not (tmp_path / "out.env").exists()


def test_renderer_command_entrypoint_reads_private_inputs_without_echoing_them(tmp_path, capsys):
    source = tmp_path / "source.env"
    source.write_text("PROJECT_NAME=x\nWEBSITE_DOMAIN=x.example\n", encoding="utf-8")
    operator = tmp_path / "operator"
    operator.write_text("preview:$apr1$abc$hash\n", encoding="utf-8")
    flower = tmp_path / "flower"
    flower.write_text("flower:$apr1$def$hash\n", encoding="utf-8")
    target = tmp_path / "private.env"
    assert render_full_preview_env.main(
        [
            "--source", str(source),
            "--target", str(target),
            "--domain", "woodkilldev.com",
            "--project", "base2-full-preview",
            "--owner-cidr", "8.8.4.4/32",
            "--operator-basic-auth-file", str(operator),
            "--flower-basic-auth-file", str(flower),
        ]
    ) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt == {
        "mode": "full-preview",
        "ok": True,
        "ownerCidrCount": 1,
        "secretValuesEmitted": 0,
    }
    assert "$apr1$abc$hash" not in json.dumps(receipt)
