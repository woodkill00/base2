#!/usr/bin/env python3
"""Run complete FastAPI coverage in isolated, bounded test partitions."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


PARTITION_SIZE = 8
MAX_ATTEMPTS = 2


def partition(values: list[Path], size: int = PARTITION_SIZE) -> list[list[Path]]:
    if size < 1:
        raise ValueError('partition_size_invalid')
    return [values[index : index + size] for index in range(0, len(values), size)]


def _run_bounded(
    command: list[str], *, root: Path, environment: dict[str, str], output: Path | None = None
) -> None:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        if output is not None:
            output.unlink(missing_ok=True)
        completed = subprocess.run(command, cwd=root, env=environment, check=False)
        if completed.returncode == 0:
            return
        if attempt == MAX_ATTEMPTS or completed.returncode not in {-11, 134, 139}:
            raise RuntimeError(f'coverage_command_failed:exit_{completed.returncode}')
    raise RuntimeError('coverage_command_failed')  # pragma: no cover


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    coverage_dir = root / '.artifacts' / 'coverage'
    raw_dir = coverage_dir / 'api-parts'
    if raw_dir.exists():
        shutil.rmtree(raw_dir)
    raw_dir.mkdir(parents=True, mode=0o700)
    tests = sorted((root / 'api' / 'tests').rglob('test_*.py'))
    if not tests:
        raise RuntimeError('api_test_inventory_empty')

    environment = os.environ.copy()
    environment['COVERAGE_CORE'] = 'ctrace'
    environment['COVERAGE_FILE'] = str(raw_dir / '.coverage.api')
    base_command = [
        sys.executable,
        '-m',
        'coverage',
        'run',
        '--source=api',
        '--parallel-mode',
        '-m',
        'pytest',
        '-c',
        'api/pytest.ini',
        '-o',
        'addopts=-q -p no:django',
        '-p',
        'no:cov',
        '--assert=plain',
        '-m',
        'not integration and not perf',
    ]
    for index, group in enumerate(partition(tests), start=1):
        before = set(raw_dir.iterdir())
        for attempt in range(1, MAX_ATTEMPTS + 1):
            completed = subprocess.run(
                [*base_command, *(str(path.relative_to(root)) for path in group)],
                cwd=root,
                env=environment,
                check=False,
            )
            if completed.returncode == 0:
                break
            for artifact in set(raw_dir.iterdir()) - before:
                artifact.unlink(missing_ok=True)
            if attempt == MAX_ATTEMPTS or completed.returncode not in {-11, 134, 139}:
                raise RuntimeError(
                    f'api_coverage_partition_failed:{index}:exit_{completed.returncode}'
                )
        else:  # pragma: no cover - loop always breaks or raises
            raise RuntimeError(f'api_coverage_partition_failed:{index}')

    combined = coverage_dir / '.coverage.api'
    combined.unlink(missing_ok=True)
    combine_environment = {**environment, 'COVERAGE_FILE': str(combined)}
    _run_bounded(
        [sys.executable, '-m', 'coverage', 'combine', '--keep', str(raw_dir)],
        root=root,
        environment=combine_environment,
        output=combined,
    )
    report = coverage_dir / 'api.json'
    _run_bounded(
        [
            sys.executable, '-m', 'coverage', 'json',
            '-o', str(report),
        ],
        root=root,
        environment=combine_environment,
        output=report,
    )
    shutil.rmtree(raw_dir)


if __name__ == '__main__':
    main()
