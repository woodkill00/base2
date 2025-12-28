from __future__ import annotations

import threading
import time
from collections import deque


class ApiMetrics:
    def __init__(self) -> None:
        self._started_at = time.time()
        self._lock = threading.Lock()
        self._requests_total = 0
        self._responses_by_class: dict[str, int] = {"1xx": 0, "2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0}
        self._latency_ms_sum = 0
        self._latency_ms_count = 0
        self._recent_latencies_ms: deque[int] = deque(maxlen=1024)

    def observe(self, *, status: int, latency_ms: int) -> None:
        status_class = f"{int(status) // 100}xx" if status else "unknown"
        with self._lock:
            self._requests_total += 1
            if status_class in self._responses_by_class:
                self._responses_by_class[status_class] += 1
            self._latency_ms_sum += int(latency_ms)
            self._latency_ms_count += 1
            self._recent_latencies_ms.append(int(latency_ms))

    def _p95_ms(self, samples: list[int]) -> float | None:
        if not samples:
            return None
        samples.sort()
        # Nearest-rank method
        idx = int(round(0.95 * (len(samples) - 1)))
        idx = max(0, min(idx, len(samples) - 1))
        return float(samples[idx])

    def render_prometheus(self) -> str:
        now = time.time()
        with self._lock:
            uptime = max(0.0, now - self._started_at)
            requests_total = int(self._requests_total)
            responses_by_class = dict(self._responses_by_class)
            latency_sum = int(self._latency_ms_sum)
            latency_count = int(self._latency_ms_count)
            recent = list(self._recent_latencies_ms)

        p95 = self._p95_ms(recent)

        lines: list[str] = []
        lines.append("# HELP base2_api_uptime_seconds Uptime of the API process in seconds")
        lines.append("# TYPE base2_api_uptime_seconds gauge")
        lines.append(f"base2_api_uptime_seconds {uptime:.3f}")

        lines.append("# HELP base2_api_requests_total Total number of HTTP requests observed")
        lines.append("# TYPE base2_api_requests_total counter")
        lines.append(f"base2_api_requests_total {requests_total}")

        lines.append("# HELP base2_api_responses_total Total number of HTTP responses by status class")
        lines.append("# TYPE base2_api_responses_total counter")
        for k in ["1xx", "2xx", "3xx", "4xx", "5xx"]:
            lines.append(f"base2_api_responses_total{{status_class=\"{k}\"}} {int(responses_by_class.get(k, 0))}")

        lines.append("# HELP base2_api_request_latency_ms_sum Sum of request latencies in milliseconds")
        lines.append("# TYPE base2_api_request_latency_ms_sum counter")
        lines.append(f"base2_api_request_latency_ms_sum {latency_sum}")

        lines.append("# HELP base2_api_request_latency_ms_count Count of request latencies observed")
        lines.append("# TYPE base2_api_request_latency_ms_count counter")
        lines.append(f"base2_api_request_latency_ms_count {latency_count}")

        if p95 is not None:
            lines.append("# HELP base2_api_request_latency_ms_p95 P95 request latency in milliseconds (rolling window)")
            lines.append("# TYPE base2_api_request_latency_ms_p95 gauge")
            lines.append(f"base2_api_request_latency_ms_p95 {p95:.3f}")

        return "\n".join(lines) + "\n"


metrics = ApiMetrics()
