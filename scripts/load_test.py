#!/usr/bin/env python3
"""load_test.py - generate realistic traffic against the Task Tracker API.

Uses only the Python standard library. The traffic mix lists, creates,
updates and reads tasks, and deliberately sends a small share of invalid
requests so that 4xx responses show up in the metrics and dashboards.

Usage:
    python3 scripts/load_test.py --url http://localhost:8000 --duration 60 --concurrency 8
"""
import argparse
import json
import random
import statistics
import threading
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor


def call(base, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
            status = resp.status
    except urllib.error.HTTPError as err:
        status = err.code
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        status = 0
    return status, (time.perf_counter() - start) * 1000


def one_request(base, rng, invalid_share):
    roll = rng.random()
    if roll < invalid_share:
        return call(base, "POST", "/api/tasks", {"title": ""})          # 400
    if roll < invalid_share * 1.5:
        return call(base, "GET", f"/api/tasks/{rng.randint(10**6, 10**7)}")  # 404
    if roll < 0.45:
        return call(base, "GET", "/api/tasks")
    if roll < 0.65:
        prio = rng.choice(["low", "medium", "high"])
        return call(base, "POST", "/api/tasks", {"title": f"load-test task {rng.randint(1, 9999)}",
                                                 "priority": prio})
    if roll < 0.80:
        status = rng.choice(["todo", "in_progress", "done"])
        return call(base, "PATCH", f"/api/tasks/{rng.randint(1, 50)}", {"status": status})
    if roll < 0.95:
        return call(base, "GET", f"/api/tasks/{rng.randint(1, 50)}")
    return call(base, "GET", "/health")


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--url", default="http://localhost:8000")
    p.add_argument("--duration", type=float, default=30, help="seconds")
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--invalid-share", type=float, default=0.04)
    p.add_argument("--seed", type=int, default=7)
    args = p.parse_args()

    stop_at = time.time() + args.duration
    statuses, latencies, lock = Counter(), [], threading.Lock()

    def worker(i):
        rng = random.Random(args.seed + i)
        while time.time() < stop_at:
            status, ms = one_request(args.url, rng, args.invalid_share)
            with lock:
                statuses[status] += 1
                latencies.append(ms)

    print(f"Load test: {args.url}  duration={args.duration:.0f}s  concurrency={args.concurrency}")
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        list(pool.map(worker, range(args.concurrency)))
    elapsed = time.time() - t0

    total = sum(statuses.values())
    q = statistics.quantiles(latencies, n=100)
    print(f"  requests     : {total} in {elapsed:.1f}s  ({total / elapsed:.1f} req/s)")
    print("  status codes : " + ", ".join(f"{k}={v}" for k, v in sorted(statuses.items())))
    print(f"  latency (ms) : p50={q[49]:.1f}  p95={q[94]:.1f}  p99={q[98]:.1f}"
          f"  max={max(latencies):.1f}")
    failed = statuses.get(0, 0) + sum(v for k, v in statuses.items() if k >= 500)
    print(f"  server errors / connection failures: {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
