import os
import statistics
import sys
import time
from typing import List

import requests


def main() -> int:
    base = os.getenv("PERF_BASE_URL", "https://woodkilldev.com")
    url = base.rstrip("/") + "/api/health"
    samples = int(os.getenv("PERF_SAMPLES", "10"))
    budget_ms = float(os.getenv("PERF_P95_BUDGET_MS", "5000"))

    latencies: List[float] = []
    sess = requests.Session()
    for _ in range(samples):
        start = time.perf_counter()
        r = sess.get(url, timeout=10)
        r.raise_for_status()
        latencies.append((time.perf_counter() - start) * 1000.0)

    latencies.sort()
    p95 = statistics.quantiles(latencies, n=100)[94]
    print(f"p95_ms={p95:.2f} from {samples} samples (budget={budget_ms}ms)")
    if p95 > budget_ms:
        print("FAIL: p95 over budget", file=sys.stderr)
        return 1
    print("OK: p95 within budget")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
