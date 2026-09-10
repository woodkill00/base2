#!/usr/bin/env python3
"""Resolve Base2 deployment intent into one bounded lifecycle action."""

from __future__ import annotations

import argparse
from dataclasses import dataclass


class DeploymentModeError(ValueError):
    """The requested flags cannot describe one safe lifecycle action."""


@dataclass(frozen=True)
class DeploymentMode:
    name: str
    action: str


def resolve_deployment_mode(
    *, full: bool, update_only: bool, create_if_missing: bool, target_exists: bool
) -> DeploymentMode:
    if full and update_only:
        raise DeploymentModeError("full_and_update_only_are_mutually_exclusive")
    if create_if_missing and not update_only:
        raise DeploymentModeError("create_if_missing_requires_update_only")
    if full:
        return DeploymentMode("full", "deploy" if target_exists else "provision")
    if update_only or not full:
        if target_exists:
            return DeploymentMode(
                "update-only-create-if-missing" if create_if_missing else "update-only",
                "deploy",
            )
        if create_if_missing:
            return DeploymentMode("update-only-create-if-missing", "provision")
        return DeploymentMode("update-only", "reject-missing-target")
    raise DeploymentModeError("unreachable_deployment_mode")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--update-only", action="store_true")
    parser.add_argument("--create-if-missing", action="store_true")
    parser.add_argument("--target-exists", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = resolve_deployment_mode(
            full=args.full,
            update_only=args.update_only,
            create_if_missing=args.create_if_missing,
            target_exists=args.target_exists,
        )
    except DeploymentModeError as error:
        parser.error(str(error))
    print(result.action)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
