import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).parents[1] / 'python' / 'run_api_coverage.py'
SPEC = importlib.util.spec_from_file_location('run_api_coverage', MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_partition_preserves_order_exactly_once_and_bounds_each_process():
    values = [Path(f'test_{index}.py') for index in range(19)]
    groups = MODULE.partition(values, size=4)
    assert [len(group) for group in groups] == [4, 4, 4, 4, 3]
    assert [item for group in groups for item in group] == values


def test_partition_rejects_unbounded_or_empty_size():
    with pytest.raises(ValueError, match='partition_size_invalid'):
        MODULE.partition([Path('test_one.py')], size=0)


def test_interpreter_corruption_signature_is_narrow_and_does_not_match_app_errors():
    observed = """
    /usr/lib/python3.12/re/_compiler.py:263
    elif op is RANGE:
    TypeError: 'str' object is not callable
    """
    assert MODULE._retryable_interpreter_corruption(observed)
    assert not MODULE._retryable_interpreter_corruption(
        "api/routes/settings.py:10 TypeError: 'str' object is not callable"
    )
    assert not MODULE._retryable_interpreter_corruption(
        "/usr/lib/python3.12/re/_compiler.py AssertionError: expected 200"
    )


def test_bounded_command_retries_native_abort_and_removes_partial_output(monkeypatch, tmp_path):
    output = tmp_path / 'partial.json'
    calls = []

    def run(*_args, **_kwargs):
        calls.append(len(calls))
        if len(calls) == 1:
            output.write_text('partial', encoding='utf-8')
            return type('Result', (), {'returncode': 139})()
        assert not output.exists()
        return type('Result', (), {'returncode': 0})()

    monkeypatch.setattr(MODULE.subprocess, 'run', run)
    MODULE._run_bounded(
        ['fixture'], root=tmp_path, environment={}, output=output
    )
    assert len(calls) == 2


def test_bounded_command_does_not_retry_ordinary_failure(monkeypatch, tmp_path):
    calls = []

    def run(*_args, **_kwargs):
        calls.append(1)
        return type('Result', (), {'returncode': 7})()

    monkeypatch.setattr(MODULE.subprocess, 'run', run)
    with pytest.raises(RuntimeError, match='coverage_command_failed:exit_7'):
        MODULE._run_bounded(['fixture'], root=tmp_path, environment={})
    assert len(calls) == 1
