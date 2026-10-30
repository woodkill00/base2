"""Regression for bounded trace-header parsing in the deployed dependency."""
import subprocess
import sys

from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


def test_valid_trace_headers_preserve_tracestate():
    context = TraceContextTextMapPropagator().extract({
        'traceparent': '00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01',
        'tracestate': 'vendor=value',
    })
    from opentelemetry.trace import get_current_span
    span = get_current_span(context).get_span_context()
    assert span.is_valid
    assert span.trace_state.get('vendor') == 'value'


def test_oversized_trace_state_finishes_within_bounded_subprocess():
    # A subprocess bounds the negative test even if a vulnerable pin returns.
    result = subprocess.run(
        [sys.executable, '-c',
         'from opentelemetry.trace import TraceState; '
         'assert len(TraceState.from_header([" " * 100000 + "x"])) == 0'],
        capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == 0, result.stderr
