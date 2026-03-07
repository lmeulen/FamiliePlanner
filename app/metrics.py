"""Prometheus metrics configuration and middleware."""

import time

from prometheus_client import Counter, Gauge, Histogram
from starlette.middleware.base import BaseHTTPMiddleware

# ── HTTP Metrics ──────────────────────────────────────────────────────
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# ── Database Metrics ──────────────────────────────────────────────────
db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

db_connections = Gauge(
    "db_connections_active",
    "Active database connections",
)

# ── Business Metrics ──────────────────────────────────────────────────
events_created_total = Counter("events_created_total", "Total agenda events created")
tasks_created_total = Counter("tasks_created_total", "Total tasks created")
tasks_completed_total = Counter("tasks_completed_total", "Total tasks marked as completed")
meals_created_total = Counter("meals_created_total", "Total meals planned")
photos_uploaded_total = Counter("photos_uploaded_total", "Total photos uploaded")


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically track HTTP request metrics."""

    async def dispatch(self, request, call_next):
        # Skip metrics endpoint itself to avoid recursive metrics
        if request.url.path == "/metrics":
            return await call_next(request)

        # Skip static files and docs
        if request.url.path.startswith(("/static/", "/api/docs", "/api/redoc")):
            return await call_next(request)

        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        # Normalize endpoint path (remove IDs for cleaner metrics)
        endpoint = self._normalize_endpoint(request.url.path)

        # Record HTTP metrics
        http_requests_total.labels(
            method=request.method,
            endpoint=endpoint,
            status=response.status_code,
        ).inc()

        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=endpoint,
        ).observe(duration)

        return response

    @staticmethod
    def _normalize_endpoint(path: str) -> str:
        """Normalize endpoint path by replacing IDs with placeholders."""
        # Replace numeric IDs with {id}
        parts = path.split("/")
        normalized = []
        for part in parts:
            if part.isdigit():
                normalized.append("{id}")
            else:
                normalized.append(part)
        return "/".join(normalized)
