#!/usr/bin/env python3
"""Provision the inspector spool through one exact, idempotent state transition."""

from __future__ import annotations

import os
import stat
import sys

SPOOL_ROOT = '/var/lib/base2/media-inspector'
PRODUCER_UID = 1000
PRODUCER_GID = 1000
FRESH_STATE = (0, 0, 0o755)
READY_STATE = (PRODUCER_UID, PRODUCER_GID, 0o770)


def main() -> int:
    try:
        info = os.stat(SPOOL_ROOT, follow_symlinks=False)
        if not stat.S_ISDIR(info.st_mode):
            return 75
        state = (info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode))
        if state == READY_STATE:
            return 0
        if state != FRESH_STATE:
            return 75
        # CAP_CHOWN is sufficient: root still owns the fresh directory while
        # chmod executes, and chown is deliberately the final mutation.
        os.chmod(SPOOL_ROOT, READY_STATE[2], follow_symlinks=False)
        os.chown(
            SPOOL_ROOT,
            PRODUCER_UID,
            PRODUCER_GID,
            follow_symlinks=False,
        )
        final = os.stat(SPOOL_ROOT, follow_symlinks=False)
        return (
            0
            if (
                final.st_uid,
                final.st_gid,
                stat.S_IMODE(final.st_mode),
            )
            == READY_STATE
            else 75
        )
    except OSError:
        return 75


if __name__ == '__main__':
    sys.exit(main())
