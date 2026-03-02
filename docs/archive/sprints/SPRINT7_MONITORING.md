# Sprint 7.1: Monitoring Minimal Stack

**Version:** 1.0.0
**Status:** ✅ IMPLEMENTED
**Date:** 2025-12-25

---

## Overview

Sprint 7.1 introduces **basic but reliable operational monitoring** for BRAiN's governance and execution systems without touching core logic. The monitoring system follows strict **fail-safe principles**: metrics collection failures MUST NOT affect runtime operations.

**Design Philosophy:**
- **Non-blocking**: Metrics collection never blocks core operations
- **Fail-safe**: Metrics failures → log warning, continue execution
- **Privacy-first**: No secrets, no payload data, no bundle content
- **Pull-based**: Prometheus scrapes metrics endpoint (no push)

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Prometheus Server                   │
│            (Scrapes every 30-60 seconds)            │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP GET /metrics
                       │
┌──────────────────────▼──────────────────────────────┐
│             BRAiN Metrics Endpoint                   │
│              /metrics (Prometheus)                   │
│              /metrics/summary (JSON)                 │
│              /metrics/health (Health Check)          │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│            MetricsCollector (Singleton)              │
│                                                       │
│  • Thread-safe (RLock)                               │
│  • In-memory counters/gauges                         │
│  • Fail-safe collection                              │
└──────────────────────┬──────────────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
┌────────▼────┐ ┌──────▼─────┐ ┌────▼──────────┐
│ Sovereign   │ │   Bundle   │ │   Factory     │
│   Mode      │ │  Manager   │ │  Executors    │
│  Service    │ │            │ │               │
│             │ │            │ │               │
│ Mode        │ │ Quarantine │ │ Execution     │
│ Switches    │ │ Events     │ │ Failures      │
└─────────────┘ └────────────┘ └───────────────┘
```

**Key Components:**

1. **MetricsCollector** (`backend/app/modules/monitoring/metrics.py`)
   - Singleton service
   - Thread-safe in-memory storage
   - Prometheus text format exporter

2. **Metrics Router** (`backend/app/modules/monitoring/router.py`)
   - `/metrics` - Prometheus scrape endpoint
   - `/metrics/summary` - Human-readable JSON
   - `/metrics/health` - Health check

3. **Integration Points:**
   - `sovereign_mode/service.py` - Mode switches
   - `sovereign_mode/bundle_manager.py` - Quarantine events
   - `factory_executor/base.py` - Executor failures/successes

---

## Metrics Specification

### 1. `brain_mode_current` (Gauge)

**Description:** Current operation mode

**Type:** Gauge
**Values:**
- `0` = ONLINE
- `1` = OFFLINE
- `2` = SOVEREIGN
- `3` = QUARANTINE

**Labels:**
- `mode` - String representation (e.g., "sovereign")

**Example:**
```prometheus
# HELP brain_mode_current Current operation mode (0=online, 1=offline, 2=sovereign, 3=quarantine)
# TYPE brain_mode_current gauge
brain_mode_current{mode="sovereign"} 2
```

**Collection:**
- Updated automatically on mode change
- Tracked in `MetricsCollector._current_mode`

---

### 2. `brain_mode_switch_total` (Counter)

**Description:** Total number of mode switches since startup

**Type:** Counter
**Never decreases**

**Example:**
```prometheus
# HELP brain_mode_switch_total Total number of mode switches
# TYPE brain_mode_switch_total counter
brain_mode_switch_total 5
```

**Collection:**
- Incremented in `SovereignModeService.change_mode()`
- Recorded via `metrics.record_mode_switch(new_mode)`

**Integration Point:**
```python
# backend/app/modules/sovereign_mode/service.py:437-443
if METRICS_AVAILABLE:
    try:
        metrics = get_metrics_collector()
        metrics.record_mode_switch(new_mode)
    except Exception as e:
        logger.warning(f"Failed to record mode switch metric: {e}")
```

---

### 3. `brain_override_active` (Gauge)

**Description:** Active override status (0 = inactive, 1 = active)

**Type:** Gauge
**Values:**
- `0` = No override active
- `1` = Override active

**Example:**
```prometheus
# HELP brain_override_active Active override status (0=inactive, 1=active)
# TYPE brain_override_active gauge
brain_override_active 0
```

**Collection:**
- Set via `metrics.set_override_active(True/False)`
- **Note:** Override system not yet implemented - metric available for future use

---

### 4. `brain_quarantine_total` (Counter)

**Description:** Total bundles quarantined since startup

**Type:** Counter
**Never decreases**

**Example:**
```prometheus
# HELP brain_quarantine_total Total bundles quarantined
# TYPE brain_quarantine_total counter
brain_quarantine_total 2
```

**Collection:**
- Incremented in `BundleManager.quarantine_bundle()`
- Recorded via `metrics.record_quarantine()`

**Integration Point:**
```python
# backend/app/modules/sovereign_mode/bundle_manager.py:277-283
if METRICS_AVAILABLE:
    try:
        metrics = get_metrics_collector()
        metrics.record_quarantine()
    except Exception as e:
        logger.warning(f"Failed to record quarantine metric: {e}")
```

---

### 5. `brain_executor_failures_total` (Counter)

**Description:** Total executor hard failures since startup

**Type:** Counter
**Never decreases**

**Example:**
```prometheus
# HELP brain_executor_failures_total Total executor hard failures
# TYPE brain_executor_failures_total counter
brain_executor_failures_total 3
```

**Collection:**
- Incremented in `ExecutorBase.execute_step()` on ExecutionError
- Recorded via `metrics.record_executor_failure()`

**Integration Points:**
```python
# backend/app/modules/factory_executor/base.py:196-202 (timeout)
if METRICS_AVAILABLE:
    try:
        metrics = get_metrics_collector()
        metrics.record_executor_failure()
    except Exception:
        pass  # Fail-safe

# backend/app/modules/factory_executor/base.py:237-243 (unexpected error)
if METRICS_AVAILABLE:
    try:
        metrics = get_metrics_collector()
        metrics.record_executor_failure()
    except Exception:
        pass  # Fail-safe
```

---

### 6. `brain_last_success_timestamp` (Gauge)

**Description:** Unix timestamp of last successful operation

**Type:** Gauge
**Value:** Unix timestamp (seconds since epoch)

**Example:**
```prometheus
# HELP brain_last_success_timestamp Last successful operation (unix timestamp)
# TYPE brain_last_success_timestamp gauge
brain_last_success_timestamp 1735128000.123
```

**Collection:**
- Updated in `ExecutorBase.execute_step()` after successful execution
- Recorded via `metrics.record_success()`
- Initialized to startup time

**Integration Point:**
```python
# backend/app/modules/factory_executor/base.py:210-216
if METRICS_AVAILABLE:
    try:
        metrics = get_metrics_collector()
        metrics.record_success()
    except Exception:
        pass  # Fail-safe
```

**Usage:**
- Monitor staleness: `time() - brain_last_success_timestamp > threshold`
- Alert if no successful operations in X seconds

---

## API Endpoints

### GET `/metrics`

**Description:** Prometheus scrape endpoint (text format)

**Content-Type:** `text/plain; version=0.0.4`

**Example Response:**
```prometheus
# HELP brain_info BRAiN monitoring metadata
# TYPE brain_info gauge
brain_info{version="1.0.0",started_at="1735128000"} 1

# HELP brain_mode_current Current operation mode (0=online, 1=offline, 2=sovereign, 3=quarantine)
# TYPE brain_mode_current gauge
brain_mode_current{mode="sovereign"} 2

# HELP brain_mode_switch_total Total number of mode switches
# TYPE brain_mode_switch_total counter
brain_mode_switch_total 5

# HELP brain_override_active Active override status (0=inactive, 1=active)
# TYPE brain_override_active gauge
brain_override_active 0

# HELP brain_quarantine_total Total bundles quarantined
# TYPE brain_quarantine_total counter
brain_quarantine_total 2

# HELP brain_executor_failures_total Total executor hard failures
# TYPE brain_executor_failures_total counter
brain_executor_failures_total 3

# HELP brain_last_success_timestamp Last successful operation (unix timestamp)
# TYPE brain_last_success_timestamp gauge
brain_last_success_timestamp 1735128000.123
```

**Prometheus Configuration:**
```yaml
scrape_configs:
  - job_name: 'brain'
    scrape_interval: 30s
    scrape_timeout: 10s
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

---

### GET `/metrics/summary`

**Description:** Human-readable metrics summary (JSON format)

**Example Response:**
```json
{
  "success": true,
  "metrics": {
    "current_mode": "sovereign",
    "mode_switches_total": 5,
    "override_active": false,
    "quarantine_total": 2,
    "executor_failures_total": 3,
    "last_success_timestamp": 1735128000.123,
    "last_success_iso": "2025-12-25T12:00:00.123000",
    "uptime_seconds": 3600
  }
}
```

**Use Case:** Human inspection, debugging, dashboards

---

### GET `/metrics/health`

**Description:** Metrics collector health check

**Example Response:**
```json
{
  "healthy": true,
  "message": "Metrics collector operational"
}
```

**Failure Response (500):**
```json
{
  "healthy": false,
  "error": "Lock acquisition failed"
}
```

---

## Fail-Safe Design

### Principle: Metrics NEVER Block Runtime

**Implementation:**
1. **Try-Catch Wrappers:** All metrics recording wrapped in try-except
2. **Graceful Degradation:** Metrics failure → log warning, continue
3. **Non-blocking Locks:** RLock for thread safety, never blocking I/O
4. **Import Safety:** Metrics module import failures handled gracefully

**Example Pattern:**
```python
# Sprint 7: Record metric (fail-safe)
if METRICS_AVAILABLE:
    try:
        metrics = get_metrics_collector()
        metrics.record_something()
    except Exception as e:
        logger.warning(f"Failed to record metric: {e}")
        # Continue execution - metrics failure is NOT critical
```

### Constraints

**Security:**
- ❌ No secrets in metrics
- ❌ No payload data
- ❌ No bundle content
- ❌ No user PII
- ✅ Only aggregated counters/gauges

**Performance:**
- Metrics collection < 1ms
- No database queries
- No network calls
- In-memory only

**Reliability:**
- Metrics failures do NOT propagate
- Metrics errors logged at WARNING level
- System continues normally if metrics fail

---

## Alerting Recommendations

### Suggested Prometheus Alerts

```yaml
groups:
  - name: brain_operational
    rules:
      # Alert if mode switches too frequently (potential instability)
      - alert: BrainModeFlapping
        expr: rate(brain_mode_switch_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "BRAiN mode switching frequently"
          description: "Mode switches at {{ $value }} per second (threshold: 0.1/s)"

      # Alert if no successful operations for 10 minutes
      - alert: BrainStaleOperations
        expr: (time() - brain_last_success_timestamp) > 600
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "BRAiN has not completed successful operations"
          description: "Last success: {{ $value }} seconds ago"

      # Alert if executor failures spike
      - alert: BrainExecutorFailures
        expr: rate(brain_executor_failures_total[5m]) > 0.5
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "BRAiN executor failures spiking"
          description: "Failure rate: {{ $value }} per second"

      # Alert if bundles are being quarantined
      - alert: BrainBundleQuarantine
        expr: increase(brain_quarantine_total[1h]) > 0
        labels:
          severity: warning
        annotations:
          summary: "BRAiN quarantined bundles"
          description: "{{ $value }} bundles quarantined in the last hour"

      # Alert if stuck in QUARANTINE mode
      - alert: BrainQuarantineMode
        expr: brain_mode_current{mode="quarantine"} == 3
        for: 15m
        labels:
          severity: critical
        annotations:
          summary: "BRAiN stuck in QUARANTINE mode"
          description: "System has been in quarantine mode for 15+ minutes"
```

---

## Testing

### Manual Testing

**1. Verify Metrics Endpoint:**
```bash
# Test Prometheus endpoint
curl http://localhost:8000/metrics

# Test JSON summary
curl http://localhost:8000/metrics/summary

# Test health check
curl http://localhost:8000/metrics/health
```

**2. Trigger Metrics:**
```bash
# Trigger mode switch
curl -X POST http://localhost:8000/api/sovereign-mode/mode \
  -H "Content-Type: application/json" \
  -d '{"target_mode": "offline", "force": true}'

# Verify mode_switch_total incremented
curl http://localhost:8000/metrics | grep brain_mode_switch_total
```

**3. Verify Fail-Safe:**
```python
# Manually break metrics collector (inject failure)
# Expected: System continues, warning logged
```

### Integration Testing

**Prometheus Test Setup:**
```yaml
# prometheus.yml (test config)
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'brain-test'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

**Run Prometheus:**
```bash
docker run -p 9090:9090 -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus

# Access UI: http://localhost:9090
# Query: brain_mode_current
```

---

## Operational Runbook

### Scenario 1: Metrics Endpoint Unreachable

**Symptoms:**
- Prometheus scrape errors
- `/metrics` returns 500

**Diagnosis:**
```bash
# Check health endpoint
curl http://localhost:8000/metrics/health

# Check logs
docker logs backend | grep -i metrics
```

**Resolution:**
- Metrics collector failure is non-critical
- System continues operating normally
- Investigate logs for root cause
- Metrics will recover automatically if issue resolves

### Scenario 2: Stale Last Success Timestamp

**Symptoms:**
- `brain_last_success_timestamp` not updating
- Alert: BrainStaleOperations

**Diagnosis:**
1. Check if executors are running:
   ```bash
   curl http://localhost:8000/api/factory/status
   ```

2. Check executor logs:
   ```bash
   docker logs backend | grep -i executor
   ```

**Resolution:**
- If executors are not running → investigate executor system
- If executors running but metric not updating → metrics integration issue (non-critical)

### Scenario 3: High Quarantine Count

**Symptoms:**
- `brain_quarantine_total` increasing
- Alert: BrainBundleQuarantine

**Diagnosis:**
```bash
# Check quarantined bundles
curl http://localhost:8000/api/sovereign-mode/bundles?status=quarantined

# Check audit log for quarantine reasons
curl http://localhost:8000/api/sovereign-mode/audit | grep BUNDLE_QUARANTINED
```

**Resolution:**
- Investigate quarantine reasons
- Fix bundle integrity issues
- Re-validate bundles if false positive

---

## Implementation Checklist

✅ **S7.1.1** - MetricsCollector service created
✅ **S7.1.2** - Prometheus /metrics endpoint implemented
✅ **S7.1.3** - 6 required metrics implemented:
  - ✅ `brain_mode_current`
  - ✅ `brain_mode_switch_total`
  - ✅ `brain_override_active` (placeholder)
  - ✅ `brain_quarantine_total`
  - ✅ `brain_executor_failures_total`
  - ✅ `brain_last_success_timestamp`

✅ **S7.1.4** - Metrics are non-blocking (try-except wrappers)
✅ **S7.1.5** - Metrics failures do NOT affect runtime
✅ **S7.1.6** - Integration with sovereign_mode service
✅ **S7.1.7** - Integration with bundle_manager
✅ **S7.1.8** - Integration with factory_executor
✅ **S7.1.9** - Documentation complete

---

## Future Enhancements (Out of Scope for S7.1)

**Not Implemented (Future Work):**
- Grafana dashboards
- Metric persistence (Redis/PostgreSQL)
- Historical metric retention
- Advanced alerting rules
- Metric aggregation across instances
- Custom exporters (StatsD, Datadog, etc.)
- Override system implementation (for `brain_override_active`)

---

## Conclusion

Sprint 7.1 delivers a **minimal but reliable monitoring stack** that provides operational visibility into BRAiN without compromising system stability. The fail-safe design ensures that monitoring never becomes a liability.

**Key Achievements:**
- ✅ Prometheus-compatible metrics endpoint
- ✅ 6 operational metrics tracked
- ✅ Fail-safe collection (never blocks runtime)
- ✅ Privacy-preserving (no secrets/payloads)
- ✅ Zero breaking changes to existing systems

**Operational Impact:**
- Operators can now monitor mode stability
- Quarantine events are now observable
- Executor failures are now measurable
- System health is now quantifiable

---

**Sprint 7.1 Status:** ✅ COMPLETE
**Next:** S7.2 - Evidence Pack Automation
