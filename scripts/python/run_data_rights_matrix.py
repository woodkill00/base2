#!/usr/bin/env python3
"""Run the required data-rights inventory in isolated processes."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


MAX_ATTEMPTS = 3
NATIVE_FAILURES = {-11, 134, 139}
TESTS = (
    'api/tests/contract/test_data_rights_contract.py',
    'api/tests/security/test_data_rights_restore.py',
    'api/tests/test_data_rights_repository.py',
    'api/tests/test_data_rights_worker.py',
    'api/tests/test_data_rights_tasks.py',
)


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    for index, relative in enumerate(TESTS, start=1):
        if not (root / relative).is_file():
            raise RuntimeError(f'data_rights_test_missing:{relative}')
        for attempt in range(1, MAX_ATTEMPTS + 1):
            result = subprocess.run(
                [
                    sys.executable, '-m', 'pytest', '--assert=plain', '-q',
                    '-p', 'no:cov', '-o', 'addopts=-q', relative,
                ],
                cwd=root,
                check=False,
            )
            if result.returncode == 0:
                if attempt > 1:
                    print(
                        f'Data-rights partition {index} recovered after '
                        f'{attempt - 1} native-crash retry attempt(s)',
                        flush=True,
                    )
                break
            if result.returncode not in NATIVE_FAILURES or attempt == MAX_ATTEMPTS:
                raise RuntimeError(
                    f'data_rights_partition_failed:{index}:exit_{result.returncode}'
                )


if __name__ == '__main__':
    main()
