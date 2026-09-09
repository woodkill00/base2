from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).parents[2]
PREFIXES = ("auth.", "identity.", "user.")


def emitted_security_actions() -> set[str]:
    actions: set[str] = set()
    for path in (ROOT / "api").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for keyword in node.keywords:
                value = keyword.value
                if (
                    keyword.arg == "action"
                    and isinstance(value, ast.Constant)
                    and isinstance(value.value, str)
                    and value.value.startswith(PREFIXES)
                ):
                    actions.add(value.value)
    return actions


def test_every_emitted_security_action_has_every_localized_label():
    contract = json.loads(
        (ROOT / "react-app/src/contracts/security-actions.json").read_text(encoding="utf-8")
    )
    assert set(contract) == {"en", "de", "ar"}
    emitted = emitted_security_actions()
    assert emitted
    assert all(set(labels) == emitted for labels in contract.values())
    assert all(
        isinstance(label, str) and label.strip()
        for labels in contract.values()
        for label in labels.values()
    )
