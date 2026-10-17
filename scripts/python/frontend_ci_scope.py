#!/usr/bin/env python3
"""Conservative exact-range frontend selection; execute the base commit's policy in CI."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

SHA = re.compile(r"[0-9a-f]{40}")
NARRATIVE = re.compile(r"specs/[0-9]{3}-[a-z0-9-]+/(?:spec|plan|tasks|analysis|quickstart|research)\.md")


def git(root: Path, *args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True,
                          timeout=30).stdout


def classify(root: Path, base: str, head: str) -> dict:
    result = {"version": 1, "mode": "full", "reason": "unavailable-comparison",
              "baseCommit": base if SHA.fullmatch(base) else None,
              "sourceCommit": head if SHA.fullmatch(head) else None,
              "browserTests": "required", "secretValuesEmitted": 0}
    if not SHA.fullmatch(base) or not SHA.fullmatch(head):
        return result
    try:
        git(root, "cat-file", "-e", f"{base}^{{commit}}")
        git(root, "cat-file", "-e", f"{head}^{{commit}}")
        # Two-dot tree comparison is conservative for PRs and push events alike:
        # include base-side differences rather than dropping them as merge-base can.
        raw = git(root, "diff", "--raw", "-z", "--no-renames", base, head, "--")
        fields = raw.split(b"\0")
        if fields[-1] != b"" or (len(fields) - 1) % 2:
            return result
        rows = []
        for index in range(0, len(fields) - 1, 2):
            metadata = fields[index].decode("ascii").split()
            path = fields[index + 1].decode("utf-8")
            if len(metadata) != 5 or not NARRATIVE.fullmatch(path):
                return {**result, "reason": "non-narrative-input"}
            old_mode, new_mode, _, _, status = metadata
            if old_mode not in {":000000", ":100644"} or new_mode != "100644" or status not in {"A", "M"}:
                return {**result, "reason": "non-narrative-change"}
            rows.append(path)
        if not rows:
            return {**result, "reason": "empty-comparison"}
        for path in rows:
            body = git(root, "show", f"{head}:{path}")
            if not body or len(body) > 1_000_000 or not body.endswith(b"\n") or b"\0" in body:
                raise ValueError("invalid narrative document")
            try:
                body.decode("utf-8")
            except UnicodeError as exc:
                raise ValueError("invalid narrative encoding") from exc
        git(root, "diff", "--check", base, head, "--")
        return {**result, "mode": "narrative", "reason": "validated-narrative-only",
                "browserTests": "not-run-by-policy", "changedFileCount": len(rows),
                "diffDigest": hashlib.sha256(raw).hexdigest()}
    except (subprocess.SubprocessError, UnicodeError):
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--github-output", type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    try:
        result = classify(args.root, args.base, args.head)
    except ValueError:
        print(json.dumps({"mode": "blocked", "reason": "invalid-narrative", "secretValuesEmitted": 0}))
        return 2
    print(json.dumps(result, sort_keys=True))
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as output:
            output.write(f"mode={result['mode']}\n")
    if args.summary:
        with args.summary.open("a", encoding="utf-8") as output:
            output.write(f"Frontend scope: **{result['mode']}**. Browser tests: {result['browserTests']}.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
