"""Read one explicitly supplied client ID; no client secret or vault access."""
import os
import re
import stat


def read_client_id(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, encoding='utf-8') as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                    or info.st_uid != os.geteuid() or info.st_mode & 0o077
                    or not 1 <= info.st_size <= 512):
                raise ValueError()
            value = stream.read(513).strip()
        if not re.fullmatch(r'[A-Za-z0-9_-]+\.apps\.googleusercontent\.com', value):
            raise ValueError()
        return value
    except (OSError, ValueError, UnicodeError):
        raise ValueError('google-preview-client-input-invalid') from None
