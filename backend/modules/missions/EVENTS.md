# Mission System - EventStream Specification

**Module:** `backend.modules.missions` (LEGACY Implementation)
**Sprint:** 2 - EventStream Integration
**Status:** ✅ Production-Ready
**Role:** PRODUCER (publishes 5 event types)

---

## Overview

The Mission System publishes events for the complete mission execution lifecycle:

- **Queue Operations** - When missions are enqueued
- **Execution Lifecycle** - Start, completion, failure, retry
- **Worker Health** - Implicit via event presence/absence

**Charter v1.0 Compliance:**
- ✅ Non-blocking event publishing
- ✅ Graceful degradation without EventStream
- ✅ Correlation tracking (mission_id)
- ✅ Structured payload with timestamps

---

## Event Types Published (5 Total)

| Event Type | When Emitted | Criticality | Publisher |
|------------|--------------|-------------|-----------|
| `task.created` | Mission enqueued to queue | INFO | `mission_control_runtime` |
| `task.started` | Worker picks mission from queue | INFO | `worker` |
| `task.completed` | Mission execution succeeds | INFO | `worker` |
| `task.failed` | Mission execution fails | WARNING/ERROR | `worker` |
| `task.retrying` | Mission re-enqueued after failure | WARNING | `worker` |

---

## Event 1: `task.created`

**Published By:** `backend.modules.missions.mission_control_runtime.MissionControlRuntime`
**Method:** `enqueue_mission()`
**When:** Mission added to queue via API

### Payload Schema

```json
{
  "task_id": "uuid-string",
  "mission_type": "agent.chat",
  "priority": "NORMAL",
  "created_at": 1735423849.123
}
```

### Example Event

```python
Event(
    id="evt_abc123",
    type=EventType.TASK_CREATED,
    source="api",
    target=None,
    timestamp=datetime(2025, 12, 28, 21, 52, 29),
    payload={
        "task_id": "mission_xyz789",
        "mission_type": "agent.chat",
        "priority": "NORMAL",
    },
    mission_id="mission_xyz789",
    task_id="mission_xyz789",
    meta={
        "schema_version": 1,
        "producer": "event_stream",
        "source_module": "core"
    }
)
```

### Consumer Recommendations

**Who Should Consume:**
- **Analytics** - Mission creation rates, type distribution
- **Audit Log** - Compliance tracking
- **Monitoring** - Queue depth alerts

**Processing:**
- Track mission submission patterns
- Alert on high creation rates (queue backlog)
- Log for audit trails

---

## Event 2: `task.started`

**Published By:** `backend.modules.missions.worker.MissionWorker`
**Method:** `_run_loop()` - after `pop_next()`
**When:** Worker picks mission from queue and begins execution

### Payload Schema

```json
{
  "task_id": "uuid-string",
  "mission_type": "agent.chat",
  "priority": "NORMAL",
  "score": 20.5,
  "retry_count": 0,
  "started_at": 1735423849.456
}
```

### Payload Fields

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | Mission ID (UUID) |
| `mission_type` | string | Mission type identifier |
| `priority` | string | Priority level (LOW, NORMAL, HIGH, CRITICAL) |
| `score` | float | Queue priority score (used for ordering) |
| `retry_count` | int | Current retry attempt (0 = first attempt) |
| `started_at` | float | Unix timestamp when execution started |

### Example Event

```python
Event(
    id="evt_def456",
    type=EventType.TASK_STARTED,
    source="mission_worker",
    target=None,
    timestamp=datetime(2025, 12, 28, 21, 52, 29),
    payload={
        "task_id": "mission_xyz789",
        "mission_type": "agent.chat",
        "priority": "NORMAL",
        "score": 20.5,
        "retry_count": 0,
        "started_at": 1735423849.456
    },
    mission_id="mission_xyz789",
    task_id="mission_xyz789"
)
```

### Consumer Recommendations

**Who Should Consume:**
- **Monitoring** - Track worker activity, detect stalls
- **Analytics** - Execution time analysis (pair with COMPLETED)
- **Dashboards** - Real-time "currently executing" view

**Processing:**
- Start execution timer (compute duration on COMPLETED)
- Update mission status to "running"
- Alert if mission runs too long (timeout detection)

---

## Event 3: `task.completed`

**Published By:** `backend.modules.missions.worker.MissionWorker`
**Method:** `_run_loop()` - after successful `execute_mission()`
**When:** Mission execution succeeds

### Payload Schema

```json
{
  "task_id": "uuid-string",
  "mission_type": "agent.chat",
  "duration_ms": 123.45,
  "completed_at": 1735423849.789
}
```

### Payload Fields

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | Mission ID (UUID) |
| `mission_type` | string | Mission type identifier |
| `duration_ms` | float | Execution time in milliseconds |
| `completed_at` | float | Unix timestamp when execution completed |

### Example Event

```python
Event(
    id="evt_ghi789",
    type=EventType.TASK_COMPLETED,
    source="mission_worker",
    target=None,
    timestamp=datetime(2025, 12, 28, 21, 52, 29),
    payload={
        "task_id": "mission_xyz789",
        "mission_type": "agent.chat",
        "duration_ms": 123.45,
        "completed_at": 1735423849.789
    },
    mission_id="mission_xyz789",
    task_id="mission_xyz789"
)
```

### Consumer Recommendations

**Who Should Consume:**
- **Analytics** - Success rates, performance metrics
- **Monitoring** - SLA tracking, throughput analysis
- **Dashboards** - Mission success counters

**Processing:**
- Calculate and store execution duration
- Update mission status to "completed"
- Track success rates by mission type
- Alert if duration exceeds SLA threshold

---

## Event 4: `task.failed`

**Published By:** `backend.modules.missions.worker.MissionWorker`
**Method:** `_run_loop()` - in exception handler
**When:** Mission execution fails (with or without retry)

### Payload Schema

```json
{
  "task_id": "uuid-string",
  "mission_type": "agent.chat",
  "error": "ValueError: Invalid input",
  "error_type": "ValueError",
  "retry_count": 1,
  "max_retries": 3,
  "will_retry": true,
  "duration_ms": 45.67,
  "failed_at": 1735423850.123
}
```

### Payload Fields

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | Mission ID (UUID) |
| `mission_type` | string | Mission type identifier |
| `error` | string | Exception message |
| `error_type` | string | Exception class name |
| `retry_count` | int | Current retry attempt (1-indexed after failure) |
| `max_retries` | int | Maximum retry attempts allowed |
| `will_retry` | bool | `true` if retry will occur, `false` if permanent failure |
| `duration_ms` | float | Execution time before failure (milliseconds) |
| `failed_at` | float | Unix timestamp when failure occurred |

### Example Event (Transient Failure - Will Retry)

```python
Event(
    id="evt_jkl012",
    type=EventType.TASK_FAILED,
    source="mission_worker",
    timestamp=datetime(2025, 12, 28, 21, 52, 30),
    payload={
        "task_id": "mission_abc123",
        "mission_type": "agent.chat",
        "error": "Network timeout",
        "error_type": "TimeoutError",
        "retry_count": 1,
        "max_retries": 3,
        "will_retry": true,
        "duration_ms": 45.67,
        "failed_at": 1735423850.123
    },
    mission_id="mission_abc123"
)
```

### Example Event (Permanent Failure - No Retry)

```python
Event(
    id="evt_mno345",
    type=EventType.TASK_FAILED,
    source="mission_worker",
    timestamp=datetime(2025, 12, 28, 21, 52, 35),
    payload={
        "task_id": "mission_def456",
        "mission_type": "data.process",
        "error": "Invalid data format",
        "error_type": "ValidationError",
        "retry_count": 3,
        "max_retries": 3,
        "will_retry": false,
        "duration_ms": 12.34,
        "failed_at": 1735423855.789
    },
    mission_id="mission_def456"
)
```

### Consumer Recommendations

**Who Should Consume:**
- **Alerting** - Critical failures, high retry rates
- **Error Tracking** - Aggregate errors by type/mission
- **Analytics** - Failure rate trends
- **Audit Log** - Compliance tracking

**Processing:**
- Aggregate errors by `error_type` for debugging
- Alert on `will_retry=false` (permanent failures)
- Track retry patterns (how many retries before success?)
- Create incidents for repeated failures of same mission type

### Criticality Matrix

| `will_retry` | Criticality | Action |
|--------------|-------------|--------|
| `true` | WARNING | Log, track retry count |
| `false` | ERROR | Alert, create incident |
| `retry_count >= max_retries` | CRITICAL | Escalate, investigate |

---

## Event 5: `task.retrying`

**Published By:** `backend.modules.missions.worker.MissionWorker`
**Method:** `_run_loop()` - after re-enqueuing failed mission
**When:** Mission re-enqueued for retry after failure

### Payload Schema

```json
{
  "task_id": "uuid-string",
  "mission_type": "agent.chat",
  "retry_count": 1,
  "max_retries": 3,
  "next_attempt": 2,
  "retried_at": 1735423850.456
}
```

### Payload Fields

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | Mission ID (UUID) |
| `mission_type` | string | Mission type identifier |
| `retry_count` | int | Current retry number (1 = first retry) |
| `max_retries` | int | Maximum retry attempts allowed |
| `next_attempt` | int | Next attempt number (retry_count + 1) |
| `retried_at` | float | Unix timestamp when retry was initiated |

### Example Event

```python
Event(
    id="evt_pqr678",
    type=EventType.TASK_RETRYING,
    source="mission_worker",
    timestamp=datetime(2025, 12, 28, 21, 52, 30),
    payload={
        "task_id": "mission_abc123",
        "mission_type": "agent.chat",
        "retry_count": 1,
        "max_retries": 3,
        "next_attempt": 2,
        "retried_at": 1735423850.456
    },
    mission_id="mission_abc123"
)
```

### Consumer Recommendations

**Who Should Consume:**
- **Monitoring** - Retry rate tracking
- **Analytics** - Reliability metrics
- **Alerting** - High retry rate detection

**Processing:**
- Track retry frequency per mission type
- Alert if retry rate exceeds threshold (e.g., >50% of missions retry)
- Calculate time between retries (for exponential backoff analysis)
- Detect "retry storms" (many missions retrying simultaneously)

---

## Event Flow Scenarios

### Scenario 1: Successful Mission

```
1. task.created     → Mission enqueued
2. task.started     → Worker picks mission
3. task.completed   → Execution succeeds
```

**Timeline:** ~100ms for simple missions

### Scenario 2: Transient Failure with Retry → Success

```
1. task.created     → Mission enqueued
2. task.started     → Worker picks mission (attempt 1)
3. task.failed      → Execution fails (will_retry=true)
4. task.retrying    → Mission re-enqueued
5. task.started     → Worker picks mission (attempt 2)
6. task.completed   → Execution succeeds
```

**Timeline:** ~2-5 seconds (depends on queue depth + poll interval)

### Scenario 3: Permanent Failure (All Retries Exhausted)

```
1. task.created     → Mission enqueued
2. task.started     → Worker picks mission (attempt 1)
3. task.failed      → Execution fails (will_retry=true)
4. task.retrying    → Mission re-enqueued
5. task.started     → Worker picks mission (attempt 2)
6. task.failed      → Execution fails (will_retry=true)
7. task.retrying    → Mission re-enqueued
8. task.started     → Worker picks mission (attempt 3)
9. task.failed      → Execution fails (will_retry=false) ⛔
```

**Timeline:** ~6-15 seconds (3 attempts)

---

## Consumer Patterns

### Pattern 1: Real-Time Dashboard

**Subscribe To:** `task.started`, `task.completed`, `task.failed`

**Use Case:** Display currently executing missions and recent completions

```python
if event.type == EventType.TASK_STARTED:
    dashboard.add_running_mission(event.mission_id)
elif event.type == EventType.TASK_COMPLETED:
    dashboard.remove_running_mission(event.mission_id)
    dashboard.increment_success_counter()
elif event.type == EventType.TASK_FAILED and not event.payload["will_retry"]:
    dashboard.remove_running_mission(event.mission_id)
    dashboard.increment_failure_counter()
```

### Pattern 2: Performance Analytics

**Subscribe To:** `task.started`, `task.completed`

**Use Case:** Calculate execution duration and throughput

```python
if event.type == EventType.TASK_STARTED:
    analytics.record_start(event.mission_id, event.timestamp)
elif event.type == EventType.TASK_COMPLETED:
    duration = event.payload["duration_ms"]
    analytics.record_completion(event.mission_id, duration)
    analytics.calculate_avg_duration(event.payload["mission_type"])
```

### Pattern 3: Error Alerting

**Subscribe To:** `task.failed`

**Use Case:** Alert on critical failures

```python
if event.type == EventType.TASK_FAILED:
    if not event.payload["will_retry"]:
        # Permanent failure - critical alert
        alerting.send_critical_alert(
            f"Mission {event.mission_id} permanently failed",
            error=event.payload["error"]
        )
    elif event.payload["retry_count"] >= 2:
        # Multiple retries - warning
        alerting.send_warning(
            f"Mission {event.mission_id} on retry {event.payload['retry_count']}"
        )
```

### Pattern 4: Retry Analysis

**Subscribe To:** `task.failed`, `task.retrying`, `task.completed`

**Use Case:** Track which missions eventually succeed after retries

```python
# State tracking
retry_tracker = {}

if event.type == EventType.TASK_FAILED and event.payload["will_retry"]:
    retry_tracker[event.mission_id] = event.payload["retry_count"]
elif event.type == EventType.TASK_COMPLETED:
    if event.mission_id in retry_tracker:
        retry_count = retry_tracker.pop(event.mission_id)
        analytics.record_retry_success(event.payload["mission_type"], retry_count)
```

---

## Implementation Notes

### Non-Blocking Guarantee

All events are published via `_emit_event_safe()` helper:

```python
async def _emit_event_safe(self, event_type, mission, extra_data):
    """Charter v1.0: Failures NEVER block business logic"""
    if self.event_stream is None:
        return  # Graceful degradation

    try:
        await emit_task_event(...)
    except Exception as e:
        logger.error("Event failed: %s", e)
        # DO NOT raise - mission execution continues
```

**Impact:** Mission execution is **NEVER** blocked by EventStream failures.

### Graceful Degradation

Worker functions without EventStream:

```python
worker = MissionWorker(queue, event_stream=None)  # OK
await worker.start()  # Missions still execute, just no events
```

### Event Ordering

Events for the same mission are published in chronological order:

```
STARTED (t=0ms) → COMPLETED (t=100ms)
STARTED (t=0ms) → FAILED (t=50ms) → RETRYING (t=51ms)
```

**No guarantees** across different missions (parallel execution).

---

## Testing Coverage

**Test File:** `backend/tests/test_missions_events.py`

**11 Integration Tests:**
1. `test_task_started_event_published` ✅
2. `test_task_completed_event_published` ✅
3. `test_task_failed_event_published_with_retry` ✅
4. `test_task_retrying_event_published` ✅
5. `test_task_failed_event_published_permanent` ✅
6. `test_event_lifecycle_success` ✅
7. `test_event_lifecycle_failure_with_retry` ✅
8. `test_event_publishing_failure_does_not_break_mission_execution` ✅
9. `test_worker_works_without_event_stream` ✅
10. `test_event_envelope_structure_charter_compliance` ✅
11. `test_multiple_missions_generate_multiple_events` ✅

**Run Tests:**
```bash
pytest backend/tests/test_missions_events.py -v
# 11 passed in 1.63s ✅
```

---

## Future Events (Not Yet Implemented)

### `task.cancelled`

**When:** Mission cancelled via API endpoint
**Status:** ⚪ Deferred (no cancel endpoint exists yet)
**Payload:**
```json
{
  "task_id": "uuid",
  "cancelled_by": "user_id",
  "cancelled_at": 1735423860.789,
  "reason": "User requested cancellation"
}
```

**Implementation Required:**
1. Add `POST /api/missions/{id}/cancel` endpoint
2. Implement cancellation logic in worker
3. Publish event on successful cancellation

---

## References

- **Worker Implementation:** `backend/modules/missions/worker.py`
- **Runtime Implementation:** `backend/modules/missions/mission_control_runtime.py`
- **Event Tests:** `backend/tests/test_missions_events.py`
- **Charter v1.0:** EventStream envelope specification
- **Sprint 2 Analysis:** `SPRINT2_MISSIONS_ARCHITECTURE_DECISION.md`

---

**Last Updated:** 2025-12-28 (Sprint 2 EventStream Migration)
**Maintained By:** BRAiN Platform Team
**Status:** ✅ Production-Ready
