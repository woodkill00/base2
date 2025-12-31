import json
from pathlib import Path

import pytest
import yaml

from api.main import app


pytestmark = [pytest.mark.contract]


def test_runtime_openapi_includes_contract_paths():
    schema = app.openapi()
    runtime_paths = set((schema.get("paths") or {}).keys())

    contract_path = Path(__file__).parents[3] / "specs" / "001-django-fastapi-react" / "contracts" / "openapi.yaml"
    assert contract_path.exists(), f"Missing contract: {contract_path}"
    with contract_path.open("r", encoding="utf-8") as f:
        contract = yaml.safe_load(f)

    # Traefik strips the '/api' prefix before forwarding to FastAPI.
    # Normalize contract paths by removing the '/api' prefix when present.
    contract_paths_raw = set((contract.get("paths") or {}).keys())
    contract_paths = set(
        p[4:] if p.startswith("/api") else p
        for p in contract_paths_raw
    )

    missing = sorted(p for p in contract_paths if p not in runtime_paths)
    assert not missing, f"Runtime missing contract paths: {json.dumps(missing)}"
