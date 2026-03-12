# Canonical Health Model Specification

**Version:** 1.0  
**Date:** 2026-03-10  
**Sprint:** B - Health System Hardening  
**Status:** Approved  
**Purpose:** Define the unified, deterministic, and auditable health model for BRAiN backend runtime.

---

## Executive Summary

This specification defines the canonical health model that unifies fragmented health surfaces across BRAiN backend. It establishes:

- **Single status vocabulary** with explicit semantics
- **Layered health architecture** from liveness to system aggregate
- **Deterministic status transitions** with explainable degradations
- **Audit/event integration** for health state changes
- **Clear route hierarchy** with canonical vs compatibility designation

**Eliminates:** False-green patterns, route ambiguity, placeholder checks, silent degradation masking

---

## 1. Health Status Vocabulary

### 1.1 Canonical Status Values

| Status | Value | Semantics | Operator Action |
|--------|-------|-----------|----------------|
| **HEALTHY** | `healthy` | All subsystems operational, metrics within thresholds | None - continue monitoring |
| **DEGRADED** | `degraded` | One or more subsystems degraded, non-critical issues present, or subsystem unavailable | Investigate - review bottlenecks and recommendations |
| **CRITICAL** | `critical` | Critical issues detected, system stability at risk | Immediate action required |
| **UNKNOWN** | `unknown` | Insufficient data or health check failed | Verify monitoring systems, check logs |
| **STALE** | `stale` | Health data older than staleness threshold (future use) | Check health monitoring system |

### 1.2 Status Transition Rules

```
UNKNOWN ──┬──> HEALTHY (2+ consecutive successful checks)
          └──> DEGRADED (1 successful check, issues detected)

HEALTHY ──┬──> DEGRADED (1 consecutive failure OR subsystem unavailable)
          └──> CRITICAL (critical issue detected)

DEGRADED ─┬──> HEALTHY (2+ consecutive successes, all issues cleared)
          ├──> CRITICAL (critical issue detected)
          └──> DEGRADED (persist)

CRITICAL ─┬──> DEGRADED (critical issues cleared, warnings remain)
          ├──> HEALTHY (all issues cleared, 2+ consecutive successes)
          └──> CRITICAL (persist)
```

**Key Principle:** Status transitions are asymmetric - degradation is immediate (1 failure), recovery requires proof (2+ successes).

---

## 2. Layered Health Architecture

### 2.1 Layer 1: Liveness Check

**Purpose:** Verify backend process is alive and accepting requests  
**Endpoint:** `/api/health` (legacy, deprecated)  
**Response Time:** < 100ms  
**Check Type:** Minimal - does not query subsystems  

**Success Criteria:**
- Process running
- HTTP server responding
- Returns JSON

**Status:**
- `ok` if process alive and SystemHealthService returns non-critical
- `degraded` if SystemHealthService returns critical
- `unknown` if SystemHealthService fails

**Deprecation:**
- Mark deprecated in OpenAPI spec
- Add `Sunset` header with date 2026-06-01
- Return hint to canonical endpoint: `/api/system/health`

**Implementation:** `backend/app/api/routes/health.py`

---

### 2.2 Layer 2: Service-Level Health Checks

**Purpose:** Monitor individual backend services (database, cache, external APIs)  
**Endpoint:** `/api/health/*` (health_monitor module)  
**Response Time:** < 500ms per check  
**Check Type:** Active probes with thresholds  

**Service Types:**

| Type | Check Method | Healthy Threshold | Degraded Threshold | Unhealthy Threshold |
|------|--------------|-------------------|-------------------|---------------------|
| `database` | `SELECT 1` query | < 100ms, success | 1 failure | 3 consecutive failures |
| `cache` | Redis `PING` | < 50ms, success | 1 failure | 3 consecutive failures |
| `external` | HTTP GET to `probe_url` | 200 OK, < 5s | Non-200 or 1 failure | 3 consecutive failures or timeout |
| `internal` | Module-specific (future) | N/A | N/A | N/A |

**Threshold Semantics:**
- `consecutive_failures >= 3` → `UNHEALTHY`
- `consecutive_failures >= 1` → `DEGRADED`
- `consecutive_successes >= 2` → `HEALTHY`
- Default → `UNKNOWN`

**Event Publication:**
- Health state transitions publish to EventStream (optional)
- `health.degraded` event on transition to DEGRADED/UNHEALTHY
- `health.recovered` event on transition to HEALTHY from DEGRADED/UNHEALTHY
- `health.critical` event on transition to UNHEALTHY

**Implementation:** `backend/app/modules/health_monitor/`

---

### 2.3 Layer 3: System-Wide Health Aggregation

**Purpose:** Aggregate health across all subsystems (immune, runtime, mission, agent)  
**Endpoint:** `/api/system/health` (canonical)  
**Response Time:** < 1000ms  
**Check Type:** Aggregation + analysis  

**Subsystems:**

| Subsystem | Data Source | Availability Handling |
|-----------|-------------|----------------------|
| Immune System | `immune_orchestrator` or legacy `immune` | `None` → DEGRADED |
| Threats System | `threats` module | `None` → ignored (placeholder) |
| Mission Queue | `missions` compat layer | `None` → DEGRADED |
| Agent System | `agent_management` | `None` → ignored (count-only) |
| Runtime Auditor | `runtime_auditor` | `None` → DEGRADED |

**Overall Status Determination Logic:**

```python
if any subsystem has critical issues:
    return CRITICAL

if multiple critical subsystems unavailable (>= 2):
    return UNKNOWN

if any subsystem unavailable:
    degrade_status = True
    # Continue checking for critical before returning

if edge_of_chaos_score not in [0.3, 0.8]:
    return DEGRADED

if audit_metrics.starvation or cascade_failure:
    return DEGRADED

if mission_queue_depth > 1000:
    return DEGRADED

if degrade_status:
    return DEGRADED

return HEALTHY
```

**Bottleneck Detection:**
- P95 latency > 1000ms → HIGH/MEDIUM bottleneck
- Memory usage > 1GB → HIGH/MEDIUM bottleneck
- Mission queue depth > 500 → MEDIUM bottleneck

**Optimization Recommendations:**
- Generated based on overall status, bottlenecks, audit metrics
- Priority levels: CRITICAL, HIGH, MEDIUM, LOW
- Categories: stability, performance, monitoring

**Implementation:** `backend/app/modules/system_health/`

---

### 2.4 Layer 4: Runtime Anomaly Detection

**Purpose:** Continuous passive monitoring with anomaly detection  
**Subsystem:** `runtime_auditor`  
**Integration:** Publishes critical anomalies to `immune_orchestrator`  
**Check Type:** Background collection loop  

**Metrics Collected:**
- Memory usage (MB) with trend analysis
- Request latency (P95, P99) from middleware (future)
- Queue depth from mission system (future)
- Edge-of-chaos score

**Anomaly Types:**
- `memory_leak` → severity: critical
- `deadlock` → severity: critical
- `cascade_failure` → severity: high
- `latency_spike` → severity: high
- `queue_saturation` → severity: high

**Anomaly Publishing:**
- Prefer `immune_orchestrator.ingest_signal()` over legacy `immune_service.publish_event()`
- Create `IncidentSignal` with:
  - `source`: `"runtime_auditor"`
  - `signal_type`: anomaly type
  - `severity`: mapped from anomaly severity
  - `metadata`: metric_value, threshold, recommendation

**Implementation:** `backend/app/modules/runtime_auditor/`

---

## 3. Route Hierarchy

### 3.1 Canonical Routes

| Route | Layer | Purpose | Auth | Status |
|-------|-------|---------|------|--------|
| `/api/system/health` | 3 | System-wide health aggregation | Optional | **Canonical** |
| `/api/system/health/status` | 3 | Lightweight summary | Optional | **Canonical** |

**Contract:** These routes are the authoritative health source for operators, monitoring, and alerting.

### 3.2 Service-Level Routes

| Route | Layer | Purpose | Auth | Status |
|-------|-------|---------|------|--------|
| `/api/health/services` | 2 | List registered services | Required | Active |
| `/api/health/services/{name}` | 2 | Service detail | Required | Active |
| `/api/health/services/{name}/history` | 2 | Service check history | Required | Active |
| `/api/health/check-all` | 2 | Trigger all checks | Required | Active |

**Contract:** Internal service-level API, not intended for primary monitoring.

### 3.3 Legacy/Compatibility Routes

| Route | Layer | Purpose | Auth | Status |
|-------|-------|---------|------|--------|
| `/api/health` | 1 | Liveness check | None | **Deprecated** |

**Contract:**
- Deprecated with `Sunset: Sat, 01 Jun 2026 00:00:00 GMT` header
- Returns hint: `"enhanced_health_endpoint": "/api/system/health"`
- No longer masks exceptions as `ok`

---

## 4. Audit/Event Integration

### 4.1 Health State Transitions

**Event Types:**
- `health.check` - Periodic service check result (EventStream only, no audit)
- `health.degraded` - Service transitioned to DEGRADED/UNHEALTHY (EventStream, future: audit)
- `health.critical` - Service transitioned to UNHEALTHY (EventStream, future: audit)
- `health.recovered` - Service transitioned to HEALTHY from DEGRADED/UNHEALTHY (EventStream, future: audit)

**Event Payload (EventStream):**
```json
{
  "type": "health.degraded",
  "service_name": "database",
  "timestamp": "2026-03-10T14:23:45Z",
  "data": {
    "previous_status": "healthy",
    "error_message": "Connection timeout",
    "consecutive_failures": 1
  }
}
```

**Future Audit Integration (Sprint C):**
- Health state transitions should create audit records via `write_unified_audit`
- Audit record includes:
  - `event_type`: health transition type
  - `correlation_id`: health check run ID
  - `actor`: "system" (automated)
  - `entity_type`: "health_check"
  - `entity_id`: service name
  - `metadata`: previous_status, new_status, error_message

### 4.2 Anomaly Publishing

**Anomaly → Immune Signal:**
- Runtime auditor detects anomaly → creates `IncidentSignal`
- `immune_orchestrator.ingest_signal()` → decision engine
- Decision audit record created via `write_unified_audit`
- Recovery action triggers if needed

**Signal Contract:**
```python
IncidentSignal(
    id="runtime-anomaly-{uuid}",
    source="runtime_auditor",
    signal_type="memory_leak",  # anomaly.type
    severity=SignalSeverity.CRITICAL,
    description="Memory usage growing at 5.2 MB/min",
    metadata={
        "metric_value": 1024.5,
        "threshold": 1000,
        "recommendation": "Profile memory usage..."
    },
    recurrence=1,
    correlation_id=None,
)
```

---

## 5. Configuration

### 5.1 Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `BRAIN_STARTUP_PROFILE` | `full` | Enable/disable health systems in minimal mode |
| `ENABLE_RUNTIME_AUDITOR` | `true` | Enable runtime auditor background loop |
| `BRAIN_HEALTH_CHECK_INTERVAL` | `60` | Health check interval (seconds) |
| `BRAIN_HEALTH_STALENESS_THRESHOLD` | `300` | Health data staleness threshold (seconds, future) |

### 5.2 Health Monitor Registration

**Database Service:**
```python
HealthCheckCreate(
    service_name="database",
    service_type="database",
    check_interval_seconds=60,
    metadata={}
)
```

**Cache Service:**
```python
HealthCheckCreate(
    service_name="cache",
    service_type="cache",
    check_interval_seconds=30,
    metadata={}
)
```

**External Service:**
```python
HealthCheckCreate(
    service_name="openai_api",
    service_type="external",
    check_interval_seconds=120,
    metadata={
        "probe_url": "https://api.openai.com/v1/models",
        "timeout_seconds": 5
    }
)
```

---

## 6. Verification Matrix

### 6.1 Route Contract Verification

**Test:** All health routes registered and respond with expected schemas

**Coverage:**
- `/api/health` returns `{"status": "ok"|"degraded"|"unknown", ...}`
- `/api/system/health` returns `SystemHealth` schema
- `/api/system/health/status` returns `SystemHealthSummary` schema
- `/api/health/services` returns list of `HealthCheckResponse`

### 6.2 Health Monitor Verification

**Test:** Service registration, threshold transitions, stale/no-data behavior

**Scenarios:**
1. Register database service → check passes → status HEALTHY
2. Simulate 1 failure → status DEGRADED
3. Simulate 3 consecutive failures → status UNHEALTHY
4. Simulate 2 consecutive successes → status HEALTHY (recovered)
5. External service without probe_url → status UNKNOWN

### 6.3 System Health Verification

**Test:** Aggregate rollup correctness, explainable degraded/critical states

**Scenarios:**
1. All subsystems healthy → overall HEALTHY
2. Immune service returns critical issues → overall CRITICAL
3. Mission health unavailable (None) → overall DEGRADED
4. Multiple subsystems unavailable → overall UNKNOWN
5. Edge-of-chaos score < 0.3 → overall DEGRADED

### 6.4 Runtime Auditor Verification

**Test:** Automatic sampling, anomaly detection, background lifecycle

**Scenarios:**
1. Start runtime auditor → background loop runs
2. Detect memory leak (increasing trend) → publish to immune_orchestrator
3. Detect latency spike (P95 > threshold) → publish to immune_orchestrator
4. Stop runtime auditor → background loop stops cleanly

### 6.5 Audit Verification

**Test:** Health transitions create EventStream events

**Scenarios:**
1. Service transitions HEALTHY → DEGRADED → `health.degraded` event published
2. Service transitions DEGRADED → HEALTHY → `health.recovered` event published
3. Service transitions DEGRADED → UNHEALTHY → `health.critical` event published

---

## 7. Migration Plan

### 7.1 Phase 1: Sprint B Completion (Immediate)

**Completed:**
- ✅ Fix legacy `/api/health` fallback-to-ok pattern
- ✅ Replace health_monitor placeholder checks
- ✅ Wire runtime_auditor into startup
- ✅ Fix system_health fallback-to-ok patterns
- ✅ Document canonical health model

**Remaining:**
- Create health-system test suite
- Update RC gate script

### 7.2 Phase 2: Monitoring Integration (Post-Sprint B)

**Actions:**
- Update monitoring/alerting to use `/api/system/health` instead of `/api/health`
- Set up alerts on `status: "critical"` or `status: "degraded"`
- Track health-system SLOs:
  - Availability: 99.9%
  - P95 latency: < 500ms
  - Accuracy: 0 false greens

### 7.3 Phase 3: Enhanced Audit (Sprint C)

**Actions:**
- Add `write_unified_audit` calls to health state transitions
- Capture correlation IDs for health check runs
- Link health degradation → immune decision → recovery action

---

## 8. Done Criteria

**Sprint B is complete when:**

1. ✅ Legacy `/api/health` does not return `status: "ok"` on exception
2. ✅ `health_monitor` has real database/cache/external checks (no placeholders)
3. ✅ `runtime_auditor` starts automatically in `backend/main.py`
4. ✅ `runtime_auditor` publishes anomalies to `immune_orchestrator` not legacy `immune`
5. ✅ `system_health` returns DEGRADED when subsystems unavailable (no fallback-to-ok)
6. ✅ Canonical health model spec exists at `docs/specs/canonical_health_model.md`
7. Health-system test suite covers route contracts, threshold transitions, aggregation logic
8. RC gate script includes health-system verification

**Operator trust restored when:**

- `/api/system/health` never shows `healthy` when issues exist (zero false greens)
- Health status is explainable (bottlenecks + recommendations present)
- Health degradation → recovery is auditable in incident timeline

---

## 9. Related Documents

- `docs/roadmap/BRAIN_HARDENING_ROADMAP.md` (Sprint B scope)
- `docs/architecture/backend_system_map.md` (health surface inventory)
- `docs/architecture/failure_surface_inventory.md` (failure paths)
- `docs/architecture/silent_fail_risks.md` (false green patterns)
- `backend/app/api/routes/health.py` (legacy health endpoint)
- `backend/app/modules/health_monitor/` (service-level checks)
- `backend/app/modules/system_health/` (system aggregation)
- `backend/app/modules/runtime_auditor/` (anomaly detection)

---

**End of Canonical Health Model Specification**
