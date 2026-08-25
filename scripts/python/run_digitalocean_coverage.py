#!/usr/bin/env python3
"""Run DigitalOcean coverage in isolated, native-crash-bounded partitions."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


PARTITION_SIZE = 4
MAX_ATTEMPTS = 3
NATIVE_FAILURES = {-11, 134, 139}


def _bounded(command: list[str], *, root: Path, environment: dict[str, str]) -> int:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        result = subprocess.run(command, cwd=root, env=environment, check=False)
        if result.returncode == 0:
            return attempt
        if result.returncode not in NATIVE_FAILURES or attempt == MAX_ATTEMPTS:
            raise RuntimeError(f'digitalocean_coverage_failed:exit_{result.returncode}')
    raise RuntimeError('digitalocean_coverage_failed')  # pragma: no cover


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    coverage_dir = root / '.artifacts' / 'coverage'
    raw_dir = coverage_dir / 'digitalocean-parts'
    if raw_dir.exists():
        shutil.rmtree(raw_dir)
    raw_dir.mkdir(parents=True, mode=0o700)
    tests = sorted((root / 'digital_ocean' / 'tests').rglob('test_*.py'))
    if not tests:
        raise RuntimeError('digitalocean_test_inventory_empty')
    groups = [tests[index : index + PARTITION_SIZE] for index in range(0, len(tests), PARTITION_SIZE)]
    environment = {
        **os.environ,
        'COVERAGE_CORE': 'ctrace',
        'COVERAGE_FILE': str(raw_dir / '.coverage.digitalocean'),
    }
    base = [
        sys.executable, '-m', 'coverage', 'run',
        '--source=digital_ocean/scripts/python', '--parallel-mode',
        '-m', 'pytest', '-o', 'addopts=-q', '-p', 'no:cov', '--assert=plain',
    ]
    for index, group in enumerate(groups, start=1):
        before = set(raw_dir.iterdir())
        for attempt in range(1, MAX_ATTEMPTS + 1):
            result = subprocess.run(
                [*base, *(str(path.relative_to(root)) for path in group)],
                cwd=root, env=environment, check=False,
            )
            if result.returncode == 0:
                if attempt > 1:
                    print(
                        f'DigitalOcean coverage partition {index} recovered after '
                        f'{attempt - 1} native-crash retry attempt(s)',
                        flush=True,
                    )
                break
            for artifact in set(raw_dir.iterdir()) - before:
                artifact.unlink(missing_ok=True)
            if result.returncode not in NATIVE_FAILURES or attempt == MAX_ATTEMPTS:
                raise RuntimeError(
                    f'digitalocean_coverage_partition_failed:{index}:exit_{result.returncode}'
                )

    combined = coverage_dir / '.coverage.digitalocean'
    combined.unlink(missing_ok=True)
    combine_environment = {**environment, 'COVERAGE_FILE': str(combined)}
    attempts = _bounded(
        [sys.executable, '-m', 'coverage', 'combine', '--keep', str(raw_dir)],
        root=root, environment=combine_environment,
    )
    if attempts > 1:
        print(f'DigitalOcean coverage combine recovered after {attempts - 1} retry attempt(s)')
    report = coverage_dir / 'digitalocean.json'
    report.unlink(missing_ok=True)
    attempts = _bounded(
        [sys.executable, '-m', 'coverage', 'json', '-o', str(report)],
        root=root, environment=combine_environment,
    )
    if attempts > 1:
        print(f'DigitalOcean coverage report recovered after {attempts - 1} retry attempt(s)')
    shutil.rmtree(raw_dir)


if __name__ == '__main__':
    main()
