"""Prometheus metrics exposed on /metrics.

Labels use the route template (for example /api/tasks/<int:task_id>) rather
than the raw path, so the number of time series stays small.
"""
from prometheus_client import Counter, Gauge, Histogram

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests handled, by method, endpoint and status code.",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently being processed.",
)

TASKS_CREATED = Counter("tasks_created_total", "Tasks created since the process started.")

TASKS_CURRENT = Gauge(
    "tasks_current",
    "Tasks currently stored in the database, by status.",
    ["status"],
)

BUILD_INFO = Gauge(
    "task_tracker_build_info",
    "Build information; the value is always 1.",
    ["version", "env"],
)
