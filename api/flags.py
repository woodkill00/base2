from __future__ import annotations

import os


def get_flags() -> dict[str, bool]:
    """Return backend feature flags.

    Current implementation is env-driven:
    - FEATURE_FLAGS=flag_a,flag_b enables listed flags
    - FLAG_<NAME>=true|false enables per-flag

    Flag names are normalized to lowercase.
    """

    flags: dict[str, bool] = {}

    raw_list = os.getenv("FEATURE_FLAGS", "")
    if raw_list:
        for part in raw_list.split(","):
            name = (part or "").strip().lower()
            if not name:
                continue
            flags[name] = True

    for k, v in os.environ.items():
        if not k.startswith("FLAG_"):
            continue
        name = k[len("FLAG_") :].strip().lower()
        if not name:
            continue
        enabled = str(v or "").strip().lower() in {"1", "true", "yes", "on"}
        flags[name] = enabled

    return flags
