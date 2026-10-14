"""Shared synthetic fixture identity; no credentials or provider access."""

import argparse
import re


def fixture_identity(run_id: str, revision: str = "") -> str:
    if not re.fullmatch(r"base2-full-[0-9]{8}-[0-9]{6}", run_id):
        raise ValueError("invalid canary fixture run id")
    if revision and not re.fullmatch(r"-r[1-9][0-9]?", revision):
        raise ValueError("invalid canary fixture revision")
    return run_id + revision


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--revision", default="")
    args = parser.parse_args(argv)
    print(fixture_identity(args.run_id, args.revision))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
