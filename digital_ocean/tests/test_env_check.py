
"""
Pytest self-tests for env_check.py
Checks that missing required variables cause failure and all set variables pass.
"""
import os
import sys
import pytest
from importlib import reload

from digital_ocean import env_check

@pytest.mark.parametrize("missing_var", env_check.REQUIRED_VARS)
def test_missing_env_var(monkeypatch, missing_var):
    # Unset all required vars, then set all except one
    for var in env_check.REQUIRED_VARS:
        monkeypatch.delenv(var, raising=False)
    for var in env_check.REQUIRED_VARS:
        if var != missing_var:
            monkeypatch.setenv(var, "dummy")
    # Should exit with error
    with pytest.raises(SystemExit) as e:
        env_check.check_required_env_vars()
    assert e.value.code == 1

def test_all_required_vars_set(monkeypatch):
    for var in env_check.REQUIRED_VARS:
        monkeypatch.setenv(var, "dummy")
    # Should not exit
    env_check.check_required_env_vars()
