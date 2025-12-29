# Sprint 4 - Metrics & Telemetry Modules: Phase 0 Analysis

**Modules:** `backend.app.modules.metrics` + `backend.app.modules.telemetry`
**Analysis Date:** 2024-12-28
**Sprint:** Sprint 4 - Data & Analytics Modules (Module 2/3 + 3/3)
**Analyst:** Claude Code
**Estimated Effort:** 1.5 hours (combined - both modules are very small)

---

## Executive Summary

Both Metrics and Telemetry modules are **extremely simple** with minimal code. They are being migrated together for efficiency.

**Combined Characteristics:**
- Very small codebase (~68 lines total)
- Simple functionality (background jobs + WebSocket)
- No complex business logic
- Few event trigger points

**Strategy:** Migrate both modules together in a single implementation phase.

---

## Module 1: Metrics

### Overview

The Metrics module provides background jobs for aggregating system metrics from Redis event streams.

**Purpose:**
- Periodic metric aggregation
- Counter increments based on event data
- Mission status tracking

**Key Features:**
- APScheduler background job (every 30 seconds)
- Redis stream consumption
- Counter abstractions

### File Structure

```
backend/app/modules/metrics/
└── jobs.py                     # Background jobs (29 lines)
```

**Total Lines:** 29 lines
**Complexity:** VERY LOW

### Code Analysis

```python
async def aggregate_mission_metrics():
    """Aggregate mission metrics from Redis streams."""
    client: redis.Redis = get_redis()
    entries = client.xrevrange("brain.events.missions", count=500)

    for _id, fields in entries:
        try:
            data = json.loads(fields[b"data"].decode("utf-8"))
            status = data.get("status")
            inc_counter("mission_status_total", {"status": status})
        except Exception:
            continue

def register_jobs(scheduler: AsyncIOScheduler):
    """Register periodic jobs with scheduler."""
    scheduler.add_job(
        aggregate_mission_metrics,
        "interval",
        seconds=30,
        id="aggregate_mission_metrics",
    )
```

### Event Trigger Points

#### 1. Aggregation Started
**Location:** Start of `aggregate_mission_metrics()`
**Event:** `metrics.aggregation_started`
**Frequency:** Every 30 seconds
**Priority:** LOW

#### 2. Aggregation Completed
**Location:** End of `aggregate_mission_metrics()`
**Event:** `metrics.aggregation_completed`
**Frequency:** Every 30 seconds
**Priority:** LOW

**Payload:**
- job_id
- entries_processed
- duration_ms
- timestamp

#### 3. Aggregation Failed
**Location:** Exception handler in `aggregate_mission_metrics()`
**Event:** `metrics.aggregation_failed`
**Frequency:** Rare (on errors)
**Priority:** MEDIUM

**Payload:**
- job_id
- error_message
- timestamp

---

## Module 2: Telemetry

### Overview

The Telemetry module provides REST API and WebSocket endpoints for robot telemetry data.

**Purpose:**
- Real-time robot metrics streaming (WebSocket)
- REST API for metric queries
- Connection management

**Key Features:**
- WebSocket connections for real-time data
- Active connection tracking
- Robot metrics endpoints (CPU, memory, network, battery)

### File Structure

```
backend/app/modules/telemetry/
├── __init__.py                 # Version info (3 lines)
└── router.py                   # REST + WebSocket API (39 lines)
```

**Total Lines:** 42 lines
**Complexity:** VERY LOW

### Code Analysis

```python
active_connections: Dict[str, WebSocket] = {}

@router.get("/info")
def get_telemetry_info():
    """Get telemetry system info."""
    return {
        "name": "Fleet Telemetry System",
        "version": "1.0.0",
        "features": [...],
        "active_connections": len(active_connections)
    }

@router.websocket("/ws/{robot_id}")
async def telemetry_websocket(websocket: WebSocket, robot_id: str):
    """WebSocket endpoint for real-time telemetry streaming."""
    await websocket.accept()
    active_connections[robot_id] = websocket

    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except:
        del active_connections[robot_id]

@router.get("/robots/{robot_id}/metrics")
async def get_robot_metrics(robot_id: str):
    """Get current robot metrics (mock data)."""
    return {
        "robot_id": robot_id,
        "cpu_usage": 45.2,
        "memory_usage": 62.8,
        ...
    }
```

### Event Trigger Points

#### 1. Connection Established
**Location:** `telemetry_websocket()` after `websocket.accept()`
**Event:** `telemetry.connection_established`
**Frequency:** Low (on new connections)
**Priority:** MEDIUM

**Payload:**
- robot_id
- connection_id
- timestamp

#### 2. Connection Closed
**Location:** `telemetry_websocket()` exception handler
**Event:** `telemetry.connection_closed`
**Frequency:** Low (on disconnections)
**Priority:** MEDIUM

**Payload:**
- robot_id
- connection_id
- duration_seconds
- reason
- timestamp

#### 3. Metrics Published
**Location:** `get_robot_metrics()` (optional)
**Event:** `telemetry.metrics_published`
**Frequency:** Medium (on metric requests)
**Priority:** LOW

**Payload:**
- robot_id
- metrics (cpu, memory, network, battery)
- timestamp

---

## Combined Event Summary

### Metrics Module: 3 Events
1. `metrics.aggregation_started` (LOW)
2. `metrics.aggregation_completed` (LOW)
3. `metrics.aggregation_failed` (MEDIUM)

### Telemetry Module: 3 Events
1. `telemetry.connection_established` (MEDIUM)
2. `telemetry.connection_closed` (MEDIUM)
3. `telemetry.metrics_published` (LOW)

**Total Events:** 6 events

---

## Implementation Strategy

### Approach: Functional Module Pattern

Both modules are **functional** (not class-based), so we'll use **module-level EventStream** pattern (similar to Threats module from Sprint 3).

**Pattern:**
```python
# Module-level EventStream
_event_stream: Optional["EventStream"] = None

def set_event_stream(stream: "EventStream") -> None:
    """Set the EventStream instance (called at startup)."""
    global _event_stream
    _event_stream = stream

async def _emit_event_safe(event_type: str, payload: dict) -> None:
    """Emit event with error handling (non-blocking)."""
    if _event_stream is None or Event is None:
        return

    try:
        event = Event(type=event_type, source="<module>_service", ...)
        await _event_stream.publish(event)
    except Exception as e:
        logger.error("Event failed: %s", e)
```

---

## Metrics Module Migration Plan

### Changes Required

1. **Add EventStream Import** (top of jobs.py)
   ```python
   try:
       from backend.mission_control_core.core import EventStream, Event
   except ImportError:
       EventStream = None
       Event = None
   ```

2. **Add Module-Level Variables**
   ```python
   _event_stream: Optional["EventStream"] = None

   def set_event_stream(stream: "EventStream") -> None:
       global _event_stream
       _event_stream = stream
   ```

3. **Add Event Helper**
   ```python
   async def _emit_event_safe(event_type: str, payload: dict) -> None:
       # Non-blocking event publishing
   ```

4. **Update `aggregate_mission_metrics()`**
   ```python
   async def aggregate_mission_metrics():
       start_time = time.time()

       # EVENT: metrics.aggregation_started
       await _emit_event_safe("metrics.aggregation_started", {...})

       try:
           # ... existing logic ...

           # EVENT: metrics.aggregation_completed
           await _emit_event_safe("metrics.aggregation_completed", {...})
       except Exception as e:
           # EVENT: metrics.aggregation_failed
           await _emit_event_safe("metrics.aggregation_failed", {...})
           raise
   ```

5. **Fix Import Paths**
   - `app.core.redis` → `backend.app.core.redis`
   - `app.core.metrics` → `backend.app.core.metrics`

---

## Telemetry Module Migration Plan

### Changes Required

1. **Add EventStream Import** (top of router.py)
   ```python
   try:
       from backend.mission_control_core.core import EventStream, Event
   except ImportError:
       EventStream = None
       Event = None
   ```

2. **Add Module-Level Variables**
   ```python
   _event_stream: Optional["EventStream"] = None

   def set_event_stream(stream: "EventStream") -> None:
       global _event_stream
       _event_stream = stream
   ```

3. **Add Event Helper**
   ```python
   async def _emit_event_safe(event_type: str, payload: dict) -> None:
       # Non-blocking event publishing
   ```

4. **Update `telemetry_websocket()`**
   ```python
   @router.websocket("/ws/{robot_id}")
   async def telemetry_websocket(websocket: WebSocket, robot_id: str):
       connection_id = f"ws_{robot_id}_{int(time.time())}"
       connect_time = time.time()

       await websocket.accept()
       active_connections[robot_id] = websocket

       # EVENT: telemetry.connection_established
       await _emit_event_safe("telemetry.connection_established", {
           "robot_id": robot_id,
           "connection_id": connection_id,
           "timestamp": connect_time,
       })

       try:
           while True:
               data = await websocket.receive_text()
               await websocket.send_text(f"Echo: {data}")
       except:
           duration = time.time() - connect_time

           # EVENT: telemetry.connection_closed
           await _emit_event_safe("telemetry.connection_closed", {
               "robot_id": robot_id,
               "connection_id": connection_id,
               "duration_seconds": duration,
               "timestamp": time.time(),
           })

           del active_connections[robot_id]
   ```

5. **Update `get_robot_metrics()` (Optional)**
   ```python
   @router.get("/robots/{robot_id}/metrics")
   async def get_robot_metrics(robot_id: str):
       metrics = {
           "robot_id": robot_id,
           "cpu_usage": 45.2,
           ...
       }

       # EVENT: telemetry.metrics_published (optional)
       await _emit_event_safe("telemetry.metrics_published", metrics)

       return metrics
   ```

---

## Testing Strategy

### Metrics Module Tests (4 tests)

1. `test_metrics_aggregation_started`
2. `test_metrics_aggregation_completed`
3. `test_metrics_aggregation_failed`
4. `test_metrics_charter_compliance`

### Telemetry Module Tests (5 tests)

1. `test_telemetry_connection_established`
2. `test_telemetry_connection_closed`
3. `test_telemetry_metrics_published`
4. `test_telemetry_multiple_connections`
5. `test_telemetry_charter_compliance`

**Total Tests:** 9 tests

---

## Dependencies

### Metrics Module
**Current:**
- redis
- apscheduler
- app.core.redis (needs path fix)
- app.core.metrics (needs path fix)

**New:**
- mission_control_core (optional import)

### Telemetry Module
**Current:**
- fastapi
- None (very simple)

**New:**
- mission_control_core (optional import)

---

## Complexity Assessment

### Combined Complexity: VERY LOW ✅

**Easy Aspects:**
- ✅ Tiny codebase (68 lines total)
- ✅ Simple functionality
- ✅ No external storage dependencies
- ✅ Clear event trigger points
- ✅ Functional architecture (module-level pattern)

**No Moderate or Complex Aspects**

---

## Risk Assessment

### VERY LOW RISK ✅

**Risks:**
1. **Import Path Fixes** - LOW
   - Straightforward find/replace

2. **WebSocket Event Timing** - LOW
   - Events published before/after WebSocket operations
   - Non-blocking so no issues

3. **Performance** - VERY LOW
   - Events are rare (connections) or periodic (aggregation)
   - No performance impact

**Mitigation:**
- Comprehensive testing
- Charter v1.0 compliance
- Non-blocking event publishing

---

## Effort Estimation

### Combined Total: 1.5 hours

| Phase | Time | Tasks |
|-------|------|-------|
| Phase 0: Analysis | 0.25h | ✅ This document |
| Phase 1: Event Design | 0.25h | Create EVENTS.md (both modules) |
| Phase 2: Implementation | 0.5h | Add EventStream to both modules |
| Phase 4: Testing | 0.25h | Create test suite (9 tests) |
| Phase 5: Documentation | 0.25h | Migration summary + commit |

**Individual Estimates:**
- Metrics: 0.75h
- Telemetry: 0.75h
- **Combined: 1.5h** (parallel implementation)

**Comparison:**
- DNA: 2.5h
- Metrics + Telemetry: **1.5h** ✅ (much faster due to simplicity)

---

## Success Criteria

✅ **Implementation:**
- 6 event types implemented (3 per module)
- Module-level EventStream pattern
- EventStream import with graceful fallback
- Import paths fixed

✅ **Testing:**
- 9 comprehensive tests (4 + 5)
- 100% event type coverage
- Charter v1.0 compliance
- All tests passing

✅ **Documentation:**
- Combined EVENTS.md (500+ lines)
- Migration summary
- Git commit with detailed message

✅ **Quality:**
- Zero breaking changes
- Non-blocking event publishing
- Graceful degradation
- Performance overhead minimal

---

## Next Steps

1. ✅ **Phase 0 Complete** - This analysis document
2. ⏳ **Phase 1** - Create combined EVENTS.md
3. ⏳ **Phase 2** - Implement EventStream for both modules
4. ⏳ **Phase 4** - Create combined test suite
5. ⏳ **Phase 5** - Documentation and git commit

---

**Analysis Complete**
**Ready to proceed to Phase 1: Event Design**

**Strategy:** Implement both modules together for efficiency (1.5 hours total vs 3.0 hours separate)

---

**Document Version:** 1.0
**Last Updated:** 2024-12-28
**Status:** ✅ ANALYSIS COMPLETE
