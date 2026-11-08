#!/usr/bin/env python3
"""analyze_logs.py - summarise the application's JSON access logs.

Reads JSON log lines from files or stdin, e.g.
    docker compose logs app --no-log-prefix | python3 scripts/analyze_logs.py
    python3 scripts/analyze_logs.py logs/app.log
and prints request volume, status-code mix, error rate and latency per endpoint.
"""
import fileinput
import json
import sys
from collections import Counter, defaultdict


def percentile(values, pct):
    if not values:
        return 0.0
    values = sorted(values)
    k = max(0, min(len(values) - 1, round(pct / 100 * len(values) + 0.5) - 1))
    return values[k]


def main():
    requests, other, bad_lines = [], Counter(), 0
    for line in fileinput.input():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            bad_lines += 1
            continue
        if entry.get("logger") == "task_tracker.access":
            requests.append(entry)
        else:
            other[entry.get("level", "?")] += 1

    if not requests:
        print("No access-log entries found.")
        return 1

    total = len(requests)
    by_class = Counter(f"{r['status'] // 100}xx" for r in requests)
    errors_5xx = by_class.get("5xx", 0)
    latency = defaultdict(list)
    for r in requests:
        latency[(r["method"], r["endpoint"])].append(r["duration_ms"])

    first, last = requests[0]["timestamp"], requests[-1]["timestamp"]
    print(f"Access-log summary ({first} -> {last})")
    print(f"  requests analysed : {total}")
    print("  status classes    : " + ", ".join(f"{k}={v}" for k, v in sorted(by_class.items())))
    print(f"  5xx error rate    : {100 * errors_5xx / total:.2f}%")
    print(f"  4xx client errors : {100 * by_class.get('4xx', 0) / total:.2f}%")
    extra = f", unparsable: {bad_lines}" if bad_lines else ""
    print(f"  other log lines   : {dict(other)}{extra}")
    print()
    header = f"  {'METHOD':<7}{'ENDPOINT':<26}{'COUNT':>7}{'p50 ms':>9}{'p95 ms':>9}{'max ms':>9}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for (method, endpoint), vals in sorted(latency.items(), key=lambda kv: -len(kv[1])):
        print(
            f"  {method:<7}{endpoint:<26}{len(vals):>7}"
            f"{percentile(vals, 50):>9.2f}{percentile(vals, 95):>9.2f}{max(vals):>9.2f}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
