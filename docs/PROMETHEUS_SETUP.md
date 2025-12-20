# Prometheus Monitoring Setup

**Version:** Phase 2 - Monitoring & Observability  
**Status:** COMPLETE  
**Last Updated:** 2025-12-20

---

## Overview

BRAiN Core now includes comprehensive Prometheus metrics for monitoring:

- **HTTP Metrics**: Request count, latency, throughput, errors
- **Database Metrics**: Connection pool usage, query performance
- **Redis Metrics**: Operations, cache hit/miss ratio, connection status
- **Mission System Metrics**: Queue size, completion rate, retry count
- **Agent Metrics**: Active agents, call duration, success rate
- **LLM Metrics**: Request count, token usage, latency
- **Application Metrics**: Errors, uptime, health status

---

## Metrics Endpoint

**URL:** `http://localhost:8000/metrics`

The `/metrics` endpoint exposes all metrics in Prometheus exposition format.

**Example Output:**
```
# HELP brain_http_requests_total Total HTTP requests
# TYPE brain_http_requests_total counter
brain_http_requests_total{method="GET",endpoint="/api/health",status="200"} 42.0

# HELP brain_http_request_duration_seconds HTTP request latency
# TYPE brain_http_request_duration_seconds histogram
brain_http_request_duration_seconds_bucket{le="0.005",method="GET",endpoint="/api/health"} 35.0
brain_http_request_duration_seconds_sum{method="GET",endpoint="/api/health"} 0.185
brain_http_request_duration_seconds_count{method="GET",endpoint="/api/health"} 42.0

# HELP brain_db_pool_size Total database connection pool size
# TYPE brain_db_pool_size gauge
brain_db_pool_size 20.0

# HELP brain_db_connections_active Number of active database connections
# TYPE brain_db_connections_active gauge
brain_db_connections_active 5.0

# HELP brain_missions_queue_size Number of missions in queue
# TYPE brain_missions_queue_size gauge
brain_missions_queue_size{priority="NORMAL"} 3.0
brain_missions_queue_size{priority="HIGH"} 1.0
```

---

## Prometheus Configuration

### Docker Compose Setup

Create `docker-compose.monitoring.yml`:

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: brain-prometheus
    restart: unless-stopped
    
    ports:
      - "9090:9090"
    
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'
    
    networks:
      - brain_network

  grafana:
    image: grafana/grafana:latest
    container_name: brain-grafana
    restart: unless-stopped
    
    ports:
      - "3030:3000"
    
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
    
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin  # Change in production!
      - GF_USERS_ALLOW_SIGN_UP=false
    
    networks:
      - brain_network

volumes:
  prometheus_data:
  grafana_data:

networks:
  brain_network:
    external: true
```

### Prometheus Config (`prometheus/prometheus.yml`)

```yaml
global:
  scrape_interval: 15s  # Scrape every 15 seconds
  evaluation_interval: 15s  # Evaluate rules every 15 seconds
  external_labels:
    cluster: 'brain-production'
    environment: 'production'

# Alerting configuration (optional)
alerting:
  alertmanagers:
    - static_configs:
        - targets:
          # - 'alertmanager:9093'

# Rule files (for alerting rules)
rule_files:
  - 'alerts/*.yml'

# Scrape configurations
scrape_configs:
  # BRAiN Backend
  - job_name: 'brain-backend'
    static_configs:
      - targets: ['backend:8000']  # Docker service name
    metrics_path: '/metrics'
    scrape_interval: 10s
    scrape_timeout: 5s
    
    # Optional: relabeling
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
        replacement: 'brain-backend'

  # Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Node Exporter (optional - for host metrics)
  # - job_name: 'node-exporter'
  #   static_configs:
  #     - targets: ['node-exporter:9100']
```

---

## Starting Monitoring Stack

```bash
# Start Prometheus + Grafana
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

# View Prometheus UI
open http://localhost:9090

# View Grafana
open http://localhost:3030
# Login: admin / admin
```

---

## Available Metrics

### HTTP Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `brain_http_requests_total` | Counter | Total HTTP requests | method, endpoint, status |
| `brain_http_request_duration_seconds` | Histogram | Request latency | method, endpoint |
| `brain_http_requests_in_progress` | Gauge | Requests being processed | method, endpoint |
| `brain_http_request_size_bytes` | Histogram | Request body size | method, endpoint |
| `brain_http_response_size_bytes` | Histogram | Response body size | method, endpoint |

### Database Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `brain_db_connections_active` | Gauge | Active DB connections | - |
| `brain_db_connections_idle` | Gauge | Idle DB connections | - |
| `brain_db_pool_size` | Gauge | Total pool size | - |
| `brain_db_pool_overflow` | Gauge | Overflow connections | - |
| `brain_db_queries_total` | Counter | Total queries | query_type, status |
| `brain_db_query_duration_seconds` | Histogram | Query latency | query_type |

### Redis Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `brain_redis_operations_total` | Counter | Total Redis operations | operation, status |
| `brain_redis_operation_duration_seconds` | Histogram | Operation latency | operation |
| `brain_redis_cache_hits_total` | Counter | Cache hits | - |
| `brain_redis_cache_misses_total` | Counter | Cache misses | - |
| `brain_redis_connected` | Gauge | Connection status (1/0) | - |

### Mission System Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `brain_missions_queue_size` | Gauge | Missions in queue | priority |
| `brain_missions_total` | Counter | Total missions | status |
| `brain_missions_duration_seconds` | Histogram | Mission execution time | mission_type, status |
| `brain_missions_retries_total` | Counter | Mission retries | mission_type |
| `brain_mission_worker_active` | Gauge | Worker status (1/0) | - |

### Agent Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `brain_agents_active` | Gauge | Active agents | agent_type |
| `brain_agent_calls_total` | Counter | Total agent calls | agent_type, status |
| `brain_agent_call_duration_seconds` | Histogram | Agent call latency | agent_type |

### LLM Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `brain_llm_requests_total` | Counter | Total LLM requests | provider, model, status |
| `brain_llm_request_duration_seconds` | Histogram | LLM request latency | provider, model |
| `brain_llm_tokens_used_total` | Counter | Total tokens used | provider, model, token_type |

### Application Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `brain_app_errors_total` | Counter | Total application errors | error_type, component |
| `brain_app_uptime_seconds` | Gauge | Application uptime | - |
| `brain_app_health_status` | Gauge | Health check status (1/0) | check_type |

---

## Example PromQL Queries

### Request Rate (QPS)
```promql
# Requests per second (last 5 minutes)
rate(brain_http_requests_total[5m])

# Requests per second by endpoint
sum(rate(brain_http_requests_total[5m])) by (endpoint)
```

### Latency
```promql
# P95 latency by endpoint
histogram_quantile(0.95, 
  sum(rate(brain_http_request_duration_seconds_bucket[5m])) by (endpoint, le)
)

# Average latency
sum(rate(brain_http_request_duration_seconds_sum[5m])) 
/ 
sum(rate(brain_http_request_duration_seconds_count[5m]))
```

### Error Rate
```promql
# 5xx error rate
sum(rate(brain_http_requests_total{status=~"5.."}[5m])) 
/ 
sum(rate(brain_http_requests_total[5m]))

# Error rate by endpoint
sum(rate(brain_http_requests_total{status=~"5.."}[5m])) by (endpoint)
```

### Database
```promql
# Connection pool usage percentage
(brain_db_connections_active / brain_db_pool_size) * 100

# Queries per second
rate(brain_db_queries_total[5m])

# P95 query latency
histogram_quantile(0.95, 
  sum(rate(brain_db_query_duration_seconds_bucket[5m])) by (query_type, le)
)
```

### Redis
```promql
# Cache hit ratio
brain_redis_cache_hits_total 
/ 
(brain_redis_cache_hits_total + brain_redis_cache_misses_total)

# Redis operations per second
rate(brain_redis_operations_total[5m])
```

### Mission System
```promql
# Mission completion rate
rate(brain_missions_total{status="completed"}[5m])

# Mission failure rate
rate(brain_missions_total{status="failed"}[5m])

# Average mission duration
sum(rate(brain_missions_duration_seconds_sum[5m])) 
/ 
sum(rate(brain_missions_duration_seconds_count[5m]))
```

---

## Grafana Dashboard

### Importing Dashboard

1. Open Grafana: `http://localhost:3030`
2. Login: `admin` / `admin`
3. Go to **Dashboards** → **Import**
4. Upload JSON file or paste JSON
5. Select Prometheus data source
6. Click **Import**

### Example Dashboard Panels

**Request Rate:**
```json
{
  "title": "Requests per Second",
  "targets": [
    {
      "expr": "sum(rate(brain_http_requests_total[5m])) by (method)",
      "legendFormat": "{{method}}"
    }
  ]
}
```

**Latency P95:**
```json
{
  "title": "Request Latency (P95)",
  "targets": [
    {
      "expr": "histogram_quantile(0.95, sum(rate(brain_http_request_duration_seconds_bucket[5m])) by (endpoint, le))",
      "legendFormat": "{{endpoint}}"
    }
  ]
}
```

**Database Connections:**
```json
{
  "title": "Database Connections",
  "targets": [
    {
      "expr": "brain_db_connections_active",
      "legendFormat": "Active"
    },
    {
      "expr": "brain_db_connections_idle",
      "legendFormat": "Idle"
    },
    {
      "expr": "brain_db_pool_size",
      "legendFormat": "Total Pool Size"
    }
  ]
}
```

---

## Alerting Rules

Create `prometheus/alerts/brain.yml`:

```yaml
groups:
  - name: brain_alerts
    interval: 30s
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: |
          (
            sum(rate(brain_http_requests_total{status=~"5.."}[5m]))
            /
            sum(rate(brain_http_requests_total[5m]))
          ) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"

      # High latency
      - alert: HighLatency
        expr: |
          histogram_quantile(0.95,
            sum(rate(brain_http_request_duration_seconds_bucket[5m])) by (endpoint, le)
          ) > 1.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency on {{ $labels.endpoint }}"
          description: "P95 latency is {{ $value }}s"

      # Database connection pool saturation
      - alert: DatabasePoolSaturation
        expr: (brain_db_connections_active / brain_db_pool_size) > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Database pool near capacity"
          description: "Pool usage is {{ $value | humanizePercentage }}"

      # Redis down
      - alert: RedisDown
        expr: brain_redis_connected == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Redis is down"
          description: "Redis connection is unavailable"

      # Mission worker stopped
      - alert: MissionWorkerDown
        expr: brain_mission_worker_active == 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Mission worker is stopped"
          description: "Mission worker is not processing missions"

      # High mission failure rate
      - alert: HighMissionFailureRate
        expr: |
          (
            rate(brain_missions_total{status="failed"}[5m])
            /
            rate(brain_missions_total[5m])
          ) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High mission failure rate"
          description: "Failure rate is {{ $value | humanizePercentage }}"
```

---

## Using Metrics in Code

### Tracking Custom Metrics

```python
from app.core.metrics import MetricsCollector

# Track database query
start = time.time()
result = await db.execute(query)
duration = time.time() - start
MetricsCollector.track_db_query("select", duration, success=True)

# Track Redis operation
start = time.time()
await redis.get(key)
duration = time.time() - start
MetricsCollector.track_redis_operation("GET", duration, success=True)

# Track cache hit/miss
if value := await redis.get(key):
    MetricsCollector.track_cache_hit()
else:
    MetricsCollector.track_cache_miss()

# Track mission
MetricsCollector.track_mission(
    status="completed",
    mission_type="deployment",
    duration=45.2
)

# Track agent call
start = time.time()
result = await agent.run(task)
duration = time.time() - start
MetricsCollector.track_agent_call("ops_agent", duration, success=True)

# Track LLM request
start = time.time()
response = await llm.generate(prompt)
duration = time.time() - start
MetricsCollector.track_llm_request(
    provider="ollama",
    model="llama3.2",
    duration=duration,
    success=True,
    prompt_tokens=150,
    completion_tokens=200
)

# Track errors
MetricsCollector.track_error("DatabaseError", "missions")

# Update health status
MetricsCollector.update_health_status("database", healthy=True)
```

---

## Production Recommendations

1. **Scrape Interval**: 10-15s for production (balance between precision and overhead)
2. **Retention**: 30 days in Prometheus, longer in long-term storage (Thanos, Cortex)
3. **Alerting**: Configure Alertmanager for critical alerts
4. **High Availability**: Run multiple Prometheus instances with federation
5. **Long-term Storage**: Use Thanos or Cortex for historical data
6. **Dashboard**: Create custom Grafana dashboards for your team
7. **Security**: Restrict /metrics endpoint in production (IP whitelist)

---

## Troubleshooting

**Metrics not appearing:**
- Check `/metrics` endpoint: `curl http://localhost:8000/metrics`
- Verify Prometheus is scraping: Check Prometheus targets page
- Check Prometheus logs: `docker logs brain-prometheus`

**High cardinality issues:**
- Endpoint normalization in PrometheusMiddleware prevents this
- UUIDs and numeric IDs are replaced with `{id}` placeholder

**Performance impact:**
- Prometheus middleware adds <1ms overhead per request
- Metrics are in-memory (very fast)
- Scraping is pull-based (no push overhead)

---

## Next Steps

Phase 2 continues with:
- **Sentry Integration** - Error tracking and performance monitoring
- **Structured Logging** - JSON logging with context
- **Distributed Tracing** - OpenTelemetry + Jaeger (Phase 2 optional)

---

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [prometheus-client Python](https://github.com/prometheus/client_python)
- [PromQL Cheatsheet](https://promlabs.com/promql-cheat-sheet/)
