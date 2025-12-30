import os
import sys
import time
from typing import Dict, List, Tuple

import requests


def sample_endpoints(base: str, endpoints: List[str], samples: int, timeout: int = 10) -> Tuple[int, int, Dict[str, int]]:
    total = 0
    errors = 0
    status_counts: Dict[str, int] = {}
    sess = requests.Session()
    for _ in range(samples):
        for ep in endpoints:
            url = base.rstrip("/") + ep
            try:
                r = sess.get(url, timeout=timeout)
                key = f"{r.status_code//100}xx"
                status_counts[key] = status_counts.get(key, 0) + 1
                if r.status_code >= 400:
                    errors += 1
            except Exception:
                status_counts["error"] = status_counts.get("error", 0) + 1
                errors += 1
            finally:
                total += 1
            time.sleep(0.05)
    return total, errors, status_counts


def main() -> int:
    base = os.getenv("SLO_BASE_URL", os.getenv("PERF_BASE_URL", "https://woodkilldev.com"))
    endpoints = os.getenv("SLO_ENDPOINTS", "/,/api/health").split(",")
    endpoints = [e.strip() for e in endpoints if e.strip()]
    samples = int(os.getenv("SLO_SAMPLES", "10"))
    max_error_rate = float(os.getenv("SLO_ERROR_RATE_MAX", "0.05"))

    total, errors, status_counts = sample_endpoints(base, endpoints, samples)
    error_rate = errors / max(total, 1)
    print(f"samples={samples} endpoints={endpoints} total_requests={total} errors={errors} error_rate={error_rate:.4f}")
    print(f"status_counts={status_counts}")
    if error_rate > max_error_rate:
        print("FAIL: error rate exceeds SLO threshold", file=sys.stderr)
        return 1

    # Optional logs check: expects an HTTP endpoint returning JSON {"lines_per_minute": number}
    logs_url = os.getenv("SLO_LOGS_CHECK_URL")
    logs_max_lpm = float(os.getenv("SLO_LOGS_MAX_LPM", "0"))
    if logs_url and logs_max_lpm > 0:
        try:
            r = requests.get(logs_url, timeout=5)
            r.raise_for_status()
            data = r.json()
            lpm = float(data.get("lines_per_minute", 0))
            print(f"logs lines_per_minute={lpm}")
            if lpm > logs_max_lpm:
                print("FAIL: log volume exceeds threshold", file=sys.stderr)
                return 1
        except Exception as e:
            print(f"WARN: logs check skipped due to error: {e}")

    print("OK: error-rate and optional logs check within thresholds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
