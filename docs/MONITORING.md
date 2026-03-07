# Monitoring & Metrics

FamiliePlanner exposes Prometheus metrics for production monitoring and observability.

## Metrics Endpoint

**Endpoint:** `GET /metrics`
**Authentication:** None (public endpoint for monitoring systems)
**Format:** Prometheus text format

## Available Metrics

### HTTP Metrics

**`http_requests_total`** (Counter)
- Total number of HTTP requests
- Labels: `method`, `endpoint`, `status`
- Example: `http_requests_total{method="GET",endpoint="/",status="200"} 142`

**`http_request_duration_seconds`** (Histogram)
- HTTP request latency in seconds
- Labels: `method`, `endpoint`
- Buckets: 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0
- Example: `http_request_duration_seconds_sum{method="GET",endpoint="/"} 5.23`

### Database Metrics

**`db_connections_active`** (Gauge)
- Active database connections
- Note: SQLite uses single connection, always 0 or 1
- Example: `db_connections_active 1`

**`db_query_duration_seconds`** (Histogram)
- Database query execution time in seconds
- Labels: `operation`
- Buckets: 0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0

### Business Metrics

**`events_created_total`** (Counter)
- Total agenda events created
- Example: `events_created_total 127`

**`tasks_created_total`** (Counter)
- Total tasks created
- Example: `tasks_created_total 456`

**`tasks_completed_total`** (Counter)
- Total tasks marked as completed
- Example: `tasks_completed_total 342`

**`meals_created_total`** (Counter)
- Total meals planned
- Example: `meals_created_total 89`

**`photos_uploaded_total`** (Counter)
- Total photos uploaded
- Example: `photos_uploaded_total 234`

## Prometheus Configuration

Add FamiliePlanner to your Prometheus scrape configuration:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'familieplanner'
    static_configs:
      - targets: ['localhost:8000']
    scrape_interval: 15s
    scrape_timeout: 10s
```

Restart Prometheus after configuration change:
```bash
systemctl restart prometheus
# or
docker restart prometheus
```

## Grafana Dashboard

A pre-built Grafana dashboard template is available at `docs/grafana-dashboard.json`.

### Import Dashboard

1. Open Grafana web UI
2. Navigate to **Dashboards** → **Import**
3. Upload `docs/grafana-dashboard.json`
4. Select your Prometheus data source
5. Click **Import**

### Dashboard Panels

The dashboard includes:
- **Request Rate:** HTTP requests per second
- **Request Duration:** p50, p95, p99 latency
- **Error Rate:** HTTP 4xx and 5xx responses
- **Database Connections:** Active connection gauge
- **Business Metrics:** Events/Tasks/Meals created over time
- **Task Completion Rate:** Tasks completed vs created

## Docker Compose Example

Run Prometheus and Grafana alongside FamiliePlanner:

```yaml
version: '3.8'

services:
  familieplanner:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin

volumes:
  prometheus-data:
  grafana-data:
```

Access:
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)
- FamiliePlanner Metrics: http://localhost:8000/metrics

## Querying Metrics

### Prometheus Queries (PromQL)

**Request rate (per second):**
```promql
rate(http_requests_total[5m])
```

**Average request duration:**
```promql
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])
```

**p95 latency:**
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

**Error rate (percentage):**
```promql
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100
```

**Tasks created today:**
```promql
increase(tasks_created_total[24h])
```

**Task completion rate:**
```promql
tasks_completed_total / tasks_created_total * 100
```

## Alerting Rules

Example Prometheus alerting rules (`/etc/prometheus/alerts.yml`):

```yaml
groups:
  - name: familieplanner
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected (>5%)"

      - alert: HighLatency
        expr: |
          histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "p95 latency above 1 second"

      - alert: DatabaseDown
        expr: db_connections_active < 1
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database connection lost"
```

## Troubleshooting

**Metrics endpoint returns 404:**
- Ensure FamiliePlanner is running and accessible
- Check that `/metrics` is not blocked by firewall or reverse proxy

**No metrics collected:**
- Verify Prometheus can reach FamiliePlanner (check Prometheus targets page at `/targets`)
- Check FamiliePlanner logs for errors
- Ensure `prometheus-client` package is installed

**Counters reset to zero:**
- Normal behavior on application restart
- Use `rate()` or `increase()` functions in PromQL to handle resets
- Consider using recording rules for long-term trends

**Memory usage growing:**
- Metrics are stored in-memory
- High cardinality labels can increase memory
- Endpoint normalization reduces cardinality (IDs replaced with `{id}`)

## Best Practices

1. **Scrape Interval:** 15-30 seconds is recommended
2. **Retention:** Configure Prometheus retention based on your needs (default 15 days)
3. **High Availability:** Run multiple Prometheus instances with remote write for production
4. **Dashboards:** Customize the provided Grafana dashboard for your needs
5. **Alerts:** Start with basic alerts and refine based on observed baselines
6. **Security:** If exposing publicly, consider adding basic auth or IP whitelisting to `/metrics`

## Further Reading

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Tutorial](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [prometheus-client Python Library](https://github.com/prometheus/client_python)
