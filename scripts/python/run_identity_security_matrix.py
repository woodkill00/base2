#!/usr/bin/env python3
"""Run the required identity security inventory in isolated processes."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


MAX_ATTEMPTS = 3
NATIVE_FAILURES = {-11, 134, 139}
TESTS = (
    'api/tests/contract/test_identity_security_contract.py',
    'api/tests/test_auth_tokens.py',
    'api/tests/test_auth_rate_limits.py',
    'api/tests/test_oauth_google_option_a.py',
    'api/tests/security/test_identity_realms.py',
    'api/tests/security/test_secret_box.py',
    'api/tests/contract/test_identity_admin_actions.py',
    'api/tests/contract/test_mfa_login_contract.py',
    'api/tests/test_identity_admin_repository.py',
    'api/tests/test_session_revocation.py',
)


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    for index, relative in enumerate(TESTS, start=1):
        if not (root / relative).is_file():
            raise RuntimeError(f'identity_security_test_missing:{relative}')
        for attempt in range(1, MAX_ATTEMPTS + 1):
            result = subprocess.run(
                [
                    sys.executable, '-m', 'pytest', '--assert=plain', '-q',
                    '-p', 'no:cov', '-o', 'addopts=-q -p no:django', relative,
                ],
                cwd=root,
                check=False,
            )
            if result.returncode == 0:
                if attempt > 1:
                    print(
                        f'Identity security partition {index} recovered after '
                        f'{attempt - 1} native-crash retry attempt(s)',
                        flush=True,
                    )
                break
            if result.returncode not in NATIVE_FAILURES or attempt == MAX_ATTEMPTS:
                raise RuntimeError(
                    f'identity_security_partition_failed:{index}:exit_{result.returncode}'
                )


if __name__ == '__main__':
    main()
