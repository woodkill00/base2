import itertools
from pathlib import Path

import pytest

from digital_ocean.scripts.python.deployment_mode import (
    DeploymentModeError,
    resolve_deployment_mode,
)


@pytest.mark.parametrize(
    ("full", "update_only", "create_if_missing", "target_exists", "action"),
    [
        (True, False, False, False, "provision"),
        (True, False, False, True, "deploy"),
        (False, True, False, False, "reject-missing-target"),
        (False, True, False, True, "deploy"),
        (False, True, True, False, "provision"),
        (False, True, True, True, "deploy"),
        (False, False, False, False, "reject-missing-target"),
        (False, False, False, True, "deploy"),
    ],
)
def test_resolves_each_supported_state_once(
    full, update_only, create_if_missing, target_exists, action
):
    result = resolve_deployment_mode(
        full=full,
        update_only=update_only,
        create_if_missing=create_if_missing,
        target_exists=target_exists,
    )
    assert result.action == action


@pytest.mark.parametrize("target_exists", [False, True])
def test_rejects_ambiguous_full_update(target_exists):
    with pytest.raises(DeploymentModeError, match="mutually_exclusive"):
        resolve_deployment_mode(
            full=True,
            update_only=True,
            create_if_missing=False,
            target_exists=target_exists,
        )


@pytest.mark.parametrize("full,target_exists", list(itertools.product([False, True], repeat=2)))
def test_rejects_standalone_create_if_missing(full, target_exists):
    with pytest.raises(DeploymentModeError, match="requires_update_only"):
        resolve_deployment_mode(
            full=full,
            update_only=False,
            create_if_missing=True,
            target_exists=target_exists,
        )


def test_authoritative_wrapper_uses_the_resolver_before_provider_provisioning():
    root = Path(__file__).resolve().parents[2]
    source = (root / "digital_ocean/scripts/powershell/deploy.ps1").read_text(
        encoding="utf-8"
    )
    resolver = source.index("deployment_mode.py @modeArgs")
    rejected = source.index("$deploymentAction -eq 'reject-missing-target'", resolver)
    provision = source.index("$deploymentAction -eq 'provision'", rejected)
    orchestrator = source.index("Run-Orchestrator -ProvisionOnly", provision)
    deploy = source.index("$deploymentAction -ne 'deploy'", orchestrator)
    remote = source.index("Remote-Verify -ip", deploy)
    assert resolver < rejected < provision < orchestrator < deploy < remote
    assert "if ($Full -and $UpdateOnly)" in source
    assert "if ($CreateIfMissing -and -not $UpdateOnly)" in source
