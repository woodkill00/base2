#!/usr/bin/env python3
"""Mechanical migration/signing helper for repository-owned module manifests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def enrich(data: dict) -> dict:
    module_id = data["id"]
    data.update(
        {
            "conflicts": data.get("conflicts", []),
            "schedules": data.get("schedules", [f"{module_id}.schedule"] if data.get("jobs") else []),
            "storage": data.get(
                "storage",
                {
                    "classes": ["private"] if (data.get("models") or data.get("providerCapabilities")) else [],
                    "maximumBytes": 1_073_741_824 if (data.get("models") or data.get("providerCapabilities")) else 0,
                },
            ),
            "observability": data.get("observability", list(data.get("healthChecks", []))),
            "backup": data.get(
                "backup", {"included": bool(data.get("models")), "restoreRequired": bool(data.get("models"))}
            ),
            "resources": data.get(
                "resources",
                {"cpuMillicores": 100, "memoryMiB": 128, "storageMiB": 1024 if data.get("models") else 0},
            ),
            "testPacks": data.get("testPacks", [f"{module_id}.contract", f"{module_id}.security"]),
            "publisher": "base2",
        }
    )
    unsigned = {key: data[key] for key in data if key != "signature"}
    data["signature"] = "builtin-sha256:" + hashlib.sha256(
        json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return data


def main() -> int:
    for path in sorted((ROOT / "modules").glob("*/module.json")):
        value = enrich(json.loads(path.read_text(encoding="utf-8")))
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
