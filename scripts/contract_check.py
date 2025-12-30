from pathlib import Path
import sys
import argparse
import yaml
from api.main import app


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default="specs/001-django-fastapi-react/contracts/openapi.yaml")
    args = parser.parse_args()
    runtime = app.openapi()
    runtime_paths = set((runtime.get("paths") or {}).keys())
    contract_path = Path(args.contract)
    if not contract_path.exists():
        print(f"Missing contract file: {contract_path}", file=sys.stderr)
        return 2
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    contract_paths = set((contract.get("paths") or {}).keys())
    missing = sorted(p for p in contract_paths if p not in runtime_paths)
    if missing:
        print(f"Runtime missing contract paths: {missing}", file=sys.stderr)
        return 1
    print("Contract check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
import argparse
import sys
from pathlib import Path

# Ensure repo root is on sys.path so `import api` works when running this script.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import yaml


def _load_contract_paths(contract_path: Path) -> set[str]:
    data = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    paths = data.get("paths") or {}
    if not isinstance(paths, dict):
        raise SystemExit("Contract has no 'paths' map")
    out: set[str] = set()
    for p in paths.keys():
        if isinstance(p, str) and p.startswith("/api/"):
            out.add(p[len("/api") :])
        else:
            out.add(str(p))
    return out


def _load_runtime_paths() -> set[str]:
    from api.main import app

    schema = app.openapi()
    paths = schema.get("paths") or {}
    if not isinstance(paths, dict):
        raise SystemExit("Runtime OpenAPI has no 'paths' map")
    return set(paths.keys())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--contract",
        default="specs/001-django-fastapi-react/contracts/openapi.yaml",
        help="Path to OpenAPI contract YAML",
    )
    args = parser.parse_args()

    contract_path = Path(args.contract)
    if not contract_path.exists():
        print(f"Missing contract file: {contract_path}", file=sys.stderr)
        return 2

    contract_paths = _load_contract_paths(contract_path)
    runtime_paths = _load_runtime_paths()

    missing = sorted(contract_paths - runtime_paths)
    if missing:
        print("Missing runtime paths required by contract:", file=sys.stderr)
        for p in missing:
            print(f"- {p}", file=sys.stderr)
        return 1

    # Explicit guardrail: ensure core auth endpoints exist in runtime.
    required_auth = {
        "/users/signup",
        "/users/login",
        "/users/logout",
        "/users/me",
        "/oauth/google/start",
        "/oauth/google/callback",
    }
    missing_auth = sorted(required_auth - runtime_paths)
    if missing_auth:
        print("Missing required auth endpoints in runtime:", file=sys.stderr)
        for p in missing_auth:
            print(f"- {p}", file=sys.stderr)
        return 1

    print("OK: OpenAPI contract paths are present in runtime")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
