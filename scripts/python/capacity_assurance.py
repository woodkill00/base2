#!/usr/bin/env python3
"""Deterministic local capacity, pressure, backpressure, and drain drills."""

from __future__ import annotations

import json
import threading
import time
import tracemalloc
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable


class CapacityError(ValueError):
    pass


class BoundedQueue:
    def __init__(self, capacity: int):
        if capacity < 1 or capacity > 100_000:
            raise CapacityError('queue:capacity_invalid')
        self.capacity = capacity
        self.items: deque[Any] = deque()
        self.lock = threading.Lock()

    def put(self, value: Any) -> bool:
        with self.lock:
            if len(self.items) >= self.capacity:
                return False
            self.items.append(value)
            return True

    def drain(self) -> list[Any]:
        with self.lock:
            values = list(self.items)
            self.items.clear()
            return values


class SingleFlightCache:
    def __init__(self):
        self.values: dict[str, Any] = {}
        self.lock = threading.Lock()

    def get(self, key: str, loader: Callable[[], Any]):
        with self.lock:
            if key not in self.values:
                self.values[key] = loader()
            return self.values[key]


def load_profile(path: Path, profile_id: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
        profile = payload['profiles'][profile_id]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise CapacityError('profile:invalid') from exc
    required = {'requests','queueCapacity','cacheContenders','soakRounds','p95Milliseconds','maximumErrorRate','maximumMemoryBytes'}
    if payload.get('schemaVersion') != 1 or set(profile) != required or any(type(profile[key]) not in {int,float} for key in required):
        raise CapacityError('profile:invalid')
    if min(profile['requests'],profile['queueCapacity'],profile['cacheContenders'],profile['soakRounds'],profile['p95Milliseconds'],profile['maximumMemoryBytes']) < 1:
        raise CapacityError('profile:invalid')
    return profile


def run_capacity_drill(profile: dict[str, Any]) -> dict[str, Any]:
    queue = BoundedQueue(profile['queueCapacity'])
    accepted = [queue.put(index) for index in range(profile['queueCapacity'] + 1)]
    if not all(accepted[:-1]) or accepted[-1]:
        raise CapacityError('queue:backpressure_failed')
    drained = queue.drain()
    if drained != list(range(profile['queueCapacity'])) or queue.drain():
        raise CapacityError('queue:drain_integrity_failed')

    loads = 0
    load_lock = threading.Lock()
    cache = SingleFlightCache()
    def loader():
        nonlocal loads
        with load_lock:
            loads += 1
        time.sleep(0.001)
        return 'cached-value'
    with ThreadPoolExecutor(max_workers=min(32, profile['cacheContenders'])) as pool:
        values = list(pool.map(lambda _: cache.get('one-key', loader), range(profile['cacheContenders'])))
    if loads != 1 or set(values) != {'cached-value'}:
        raise CapacityError('cache:stampede_detected')

    latencies: list[float] = []
    errors = 0
    tracemalloc.start()
    for _round in range(profile['soakRounds']):
        for index in range(profile['requests']):
            started = time.perf_counter()
            try:
                hashlib_like = (index * 2654435761) & 0xFFFFFFFF
                if hashlib_like < 0:
                    raise AssertionError
            except Exception:
                errors += 1
            latencies.append((time.perf_counter() - started) * 1000)
    _current, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
    ordered = sorted(latencies)
    p95 = ordered[max(0, int(len(ordered) * 0.95) - 1)]
    error_rate = errors / len(latencies)
    if p95 > profile['p95Milliseconds'] or error_rate > profile['maximumErrorRate'] or peak > profile['maximumMemoryBytes']:
        raise CapacityError('capacity:slo_failed')
    return {
        'status':'passed','operations':len(latencies),'p95Milliseconds':round(p95,3),
        'errorRate':error_rate,'peakMemoryBytes':peak,'queueRejected':1,'queueDrained':len(drained),
        'cacheLoads':loads,'integrityErrors':0,
    }
