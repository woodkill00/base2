"""Private operational ledger for a bounded mail trial, never reset by workers."""

import fcntl
import hashlib
import json
import math
import os
import re
import stat
import time


def reserve_send(path: str, delivery_key: str, *, now: float | None = None) -> None:
    """Reserve before sending; uncertain sends consume budget and cannot replay.

    The same inode must be mounted for every worker. A partial interrupted write
    leaves invalid JSON and blocks further sending rather than resetting the budget.
    """
    if not os.path.isabs(path) or not delivery_key:
        raise RuntimeError('email_budget_configuration_invalid')
    current = time.time() if now is None else now
    try:
        fd = os.open(path, os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'r+', encoding='utf-8') as stream:
            info = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_nlink != 1
                or info.st_uid != os.geteuid()
                or info.st_mode & 0o077
                or info.st_size > 16384
            ):
                raise RuntimeError('email_budget_file_unsafe')
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            state = json.load(stream)
            if not isinstance(state, dict) or set(state) != {
                'schemaVersion',
                'expiresAt',
                'maxAttempts',
                'reservations',
            }:
                raise RuntimeError('email_budget_schema_invalid')
            expiry, cap, reservations = (
                state['expiresAt'],
                state['maxAttempts'],
                state['reservations'],
            )
            if (
                state['schemaVersion'] != 1
                or type(cap) is not int
                or not 1 <= cap <= 20
                or type(expiry) not in {int, float}
                or not math.isfinite(expiry)
                or not isinstance(reservations, list)
                or len(reservations) > cap
                or any(
                    not isinstance(value, str) or not re.fullmatch('[a-f0-9]{64}', value)
                    for value in reservations
                )
                or len(set(reservations)) != len(reservations)
            ):
                raise RuntimeError('email_budget_schema_invalid')
            if not math.isfinite(current) or not current < expiry <= current + 86400:
                raise RuntimeError('email_budget_expired_or_invalid')
            digest = hashlib.sha256(delivery_key.encode()).hexdigest()
            if digest in reservations:
                raise RuntimeError('email_budget_duplicate_requires_reconciliation')
            if len(reservations) >= cap:
                raise RuntimeError('email_budget_exhausted')
            reservations.append(digest)
            stream.seek(0)
            stream.truncate()
            json.dump(state, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
    except (OSError, ValueError, TypeError):
        raise RuntimeError('email_budget_unavailable_or_corrupt') from None
