"""Compatibility shim for project logging helpers.

Important: this file is named `logging.py`, so if Python's import search path includes
the `digital_ocean/` directory itself (common when running scripts like
`python digital_ocean/validate_dns.py`), third-party libraries that do `import logging`
can accidentally import *this* module instead of the stdlib `logging`.

To make CLI scripts reliable, we detect that case and transparently forward to the
stdlib module.
"""

from __future__ import annotations

import importlib
import os
import sys


if __name__ == "logging":
    # We were imported as top-level `logging` (shadowing stdlib). Fix by
    # temporarily removing this directory from sys.path, then importing stdlib.
    _this_dir = os.path.dirname(__file__)
    _this_dir_abs = os.path.abspath(_this_dir)
    _orig_path = list(sys.path)
    try:
        sys.path = [p for p in sys.path if os.path.abspath(p) != _this_dir_abs]
        sys.modules.pop("logging", None)
        _real = importlib.import_module("logging")
        sys.modules["logging"] = _real
        globals().update(_real.__dict__)
    finally:
        sys.path = _orig_path
else:
    from .do_logging import (  # noqa: F401
        LEVELS,
        LOG_LEVEL,
        get_logger,
        logger,
        log_exec_error,
        log_exec_start,
        log_exec_success,
        log_info_query_error,
        log_info_query_start,
        log_info_query_success,
    )

    __all__ = [
        "LEVELS",
        "LOG_LEVEL",
        "get_logger",
        "logger",
        "log_exec_error",
        "log_exec_start",
        "log_exec_success",
        "log_info_query_error",
        "log_info_query_start",
        "log_info_query_success",
    ]
