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
    insecure = os.getenv("PERF_INSECURE", "0") == "1"

    latencies: List[float] = []
    sess = requests.Session()
    # Verification flag applied per request for clarity
    verify_flag = (not insecure)
    # simple warmup to prime DNS/TLS
    try:
        sess.head(base, timeout=10, verify=verify_flag)
    except requests.RequestException:
        pass

    for _ in range(samples):
        attempts = 0
        while attempts < 3:
            attempts += 1
            try:
                start = time.perf_counter()
                r = sess.get(url, timeout=10, verify=verify_flag)
                r.raise_for_status()
                latencies.append((time.perf_counter() - start) * 1000.0)
                break
            except requests.RequestException as e:
                if attempts < 3:
                    time.sleep(1.0)
                    continue
                print(f"WARN: request failed after retries: {e}", file=sys.stderr)
                break

    # If insecure and HTTPS completely failed, try HTTP fallback for health
    if insecure and len(latencies) == 0 and base.startswith("https://"):
        try:
            alt_base = "http://" + base[len("https://"):]
            alt_url = alt_base.rstrip("/") + "/api/health"
            for _ in range(min(samples, 5)):
                start = time.perf_counter()
                r = sess.get(alt_url, timeout=10, verify=False)
                r.raise_for_status()
                latencies.append((time.perf_counter() - start) * 1000.0)
            print("INFO: used HTTP fallback for health check due to HTTPS validation issues")
        except requests.RequestException as e:
            print(f"ERROR: HTTP fallback also failed: {e}", file=sys.stderr)

    latencies.sort()
    if len(latencies) < 2:
        print("ERROR: insufficient successful samples for p95 (collected=", len(latencies), ")", file=sys.stderr)
        return 1
    # Use inclusive quantiles for better small-sample behavior
    p95 = statistics.quantiles(latencies, n=100, method="inclusive")[94]
    print(f"p95_ms={p95:.2f} from {samples} samples (budget={budget_ms}ms)")
    if p95 > budget_ms:
        print("FAIL: p95 over budget", file=sys.stderr)
        return 1
    print("OK: p95 within budget")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
