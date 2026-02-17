# Supervisor Module - EventStream Event Specifications

**Version:** 1.0.0
**Last Updated:** December 29, 2025
**Module:** Supervisor
**Sprint:** Sprint 5 - Resource Management & Hardware (Module 3/4)
**Status:** Specification

---

## Table of Contents

1. [Overview](#overview)
2. [Event Types](#event-types)
3. [Charter v1.0 Compliance](#charter-v10-compliance)
4. [Integration Pattern](#integration-pattern)
5. [Testing](#testing)

---

## Overview

This document specifies EventStream events for the **Supervisor** module. The Supervisor coordinates mission execution and agent management, providing aggregated status information for monitoring and control.

### Event Summary

| Event Type | Priority | Frequency | Use Case |
|------------|----------|-----------|----------|
| supervisor.health_checked | OPTIONAL | Per health check | Availability monitoring |
| supervisor.status_queried | **MEDIUM** | Per status query | **Dashboard updates, load monitoring** |
| supervisor.agents_listed | OPTIONAL | Per agent list query | Agent management tracking |

**Primary Event:** `supervisor.status_queried` - Provides valuable operational insights by tracking when monitoring dashboards query supervisor status.

### Event Naming Convention

All events follow the pattern: `supervisor.{action}_{object}`

---

## Event Types

### 1. supervisor.health_checked (OPTIONAL)

**Purpose:** Track supervisor health check requests
**Frequency:** Per GET /api/supervisor/health
**Priority:** LOW (optional telemetry)

**When Emitted:**
- After successful health check in `get_health()`

**Payload Schema:**
```typescript
{
  status: string;          // Health status ("ok", "degraded", "error")
  checked_at: number;      // Unix timestamp of check
}
```

**Payload Example:**
```json
{
  "status": "ok",
  "checked_at": 1703001234.567
}
```

**Producer:** `supervisor_service` (from `service.py`)
**Target:** `null` (broadcast)

**Use Cases:**
- Monitor health check frequency
- Track supervisor availability
- Aggregate uptime metrics
- Detect monitoring patterns

**Charter Envelope:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "supervisor.health_checked",
  "source": "supervisor_service",
  "target": null,
  "timestamp": 1703001234.567,
  "payload": {
    "status": "ok",
    "checked_at": 1703001234.567
  },
  "meta": {}
}
```

**Implementation Notes:**
- **Optional event** - can be skipped for minimal telemetry
- Low priority due to simple health checks
- Useful for tracking supervisor uptime

---

### 2. supervisor.status_queried (MEDIUM PRIORITY)

**Purpose:** Track supervisor status queries with aggregated mission statistics
**Frequency:** Per GET /api/supervisor/status
**Priority:** MEDIUM (valuable operational insight)

**When Emitted:**
- After aggregating mission statistics in `get_status()`

**Payload Schema:**
```typescript
{
  total_missions: number;      // Total missions in system
  running_missions: number;    // Currently running missions
  pending_missions: number;    // Missions waiting to start
  completed_missions: number;  // Successfully completed missions
  failed_missions: number;     // Failed missions
  cancelled_missions: number;  // Cancelled missions
  agent_count: number;         // Number of registered agents
  queried_at: number;          // Unix timestamp of query
}
```

**Payload Example:**
```json
{
  "total_missions": 150,
  "running_missions": 5,
  "pending_missions": 3,
  "completed_missions": 130,
  "failed_missions": 10,
  "cancelled_missions": 2,
  "agent_count": 0,
  "queried_at": 1703001234.567
}
```

**Producer:** `supervisor_service` (from `service.py`)
**Target:** `null` (broadcast)

**Use Cases:**
- **Dashboard Updates** - Track when UI queries supervisor status
- **Load Monitoring** - Detect high-frequency polling by clients
- **Audit Trail** - Log who's monitoring the system
- **Performance Analysis** - Analyze query patterns and response times
- **Capacity Planning** - Understand mission load over time
- **Alerting** - Trigger alerts when status is queried during incidents

**Why Important:**
- Aggregates mission statistics (expensive operation calling missions.get_stats)
- Called frequently by monitoring dashboards and control UIs
- Reveals system activity patterns and client behavior
- Captures snapshot of system state at query time

**Charter Envelope:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "type": "supervisor.status_queried",
  "source": "supervisor_service",
  "target": null,
  "timestamp": 1703001234.567,
  "payload": {
    "total_missions": 150,
    "running_missions": 5,
    "pending_missions": 3,
    "completed_missions": 130,
    "failed_missions": 10,
    "cancelled_missions": 2,
    "agent_count": 0,
    "queried_at": 1703001234.567
  },
  "meta": {}
}
```

**Implementation Notes:**
- **Recommended event** - high value for monitoring and analytics
- Includes all mission statistics from supervisor status
- Agent count currently always 0 (list_agents stub)
- Future: Add agent details when agent management is implemented

---

### 3. supervisor.agents_listed (OPTIONAL)

**Purpose:** Track agent listing requests
**Frequency:** Per GET /api/supervisor/agents
**Priority:** LOW (stub implementation)

**When Emitted:**
- After retrieving agent list in `list_agents()`

**Payload Schema:**
```typescript
{
  agent_count: number;         // Number of agents returned
  queried_at: number;          // Unix timestamp of query
}
```

**Payload Example:**
```json
{
  "agent_count": 0,
  "queried_at": 1703001234.567
}
```

**Producer:** `supervisor_service` (from `service.py`)
**Target:** `null` (broadcast)

**Use Cases:**
- Track agent listing requests
- Monitor stub endpoint usage
- Prepare patterns for future agent management
- Identify clients interested in agent information

**Charter Envelope:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "type": "supervisor.agents_listed",
  "source": "supervisor_service",
  "target": null,
  "timestamp": 1703001234.567,
  "payload": {
    "agent_count": 0,
    "queried_at": 1703001234.567
  },
  "meta": {}
}
```

**Implementation Notes:**
- **Optional event** - can be skipped until agent management is implemented
- Currently returns empty list (stub)
- Future: Include agent details (id, name, state, heartbeat)

---

## Charter v1.0 Compliance

All events follow the Charter v1.0 specification:

```python
@dataclass
class Event:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str                    # "supervisor.*"
    source: str                  # "supervisor_service"
    target: Optional[str] = None # null (broadcast)
    timestamp: float = field(default_factory=time.time)
    payload: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)
```

### Required Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | UUID string | Auto-generated unique ID | `"550e8400-e29b-41d4-a716-446655440000"` |
| `type` | string | Event type (namespaced) | `"supervisor.status_queried"` |
| `source` | string | Event producer | `"supervisor_service"` |
| `target` | string/null | Event destination | `null` |
| `timestamp` | float | Unix timestamp | `1703001234.567` |
| `payload` | object | Event data | `{"total_missions": 150, ...}` |
| `meta` | object | Metadata (optional) | `{}` |

### Validation Rules

1. ✅ All events have UUID `id`
2. ✅ All events have namespaced `type` (supervisor.*)
3. ✅ All events have consistent `source` (supervisor_service)
4. ✅ All events have auto-generated `timestamp`
5. ✅ All payloads contain required fields
6. ✅ Timestamps are Unix epoch (seconds with decimal)

---

## Integration Pattern

### Module-Level EventStream Pattern

Supervisor module uses **module-level EventStream** (functional architecture):

```python
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Optional EventStream import
try:
    from backend.app.core.event_stream import EventStream, Event
except ImportError:
    EventStream = None
    Event = None

# Module-level state
_event_stream: Optional["EventStream"] = None


def set_event_stream(stream: "EventStream") -> None:
    """Initialize EventStream for Supervisor module."""
    global _event_stream
    _event_stream = stream


async def _emit_event_safe(event_type: str, payload: dict) -> None:
    """Emit supervisor event with error handling (non-blocking).

    Args:
        event_type: Event type (e.g., "supervisor.status_queried")
        payload: Event payload dictionary

    Note:
        - Never raises exceptions
        - Logs failures at ERROR level
        - Gracefully handles missing EventStream
    """
    global _event_stream
    if _event_stream is None or Event is None:
        logger.debug("[SupervisorService] EventStream not available, skipping event")
        return

    try:
        event = Event(
            type=event_type,
            source="supervisor_service",
            target=None,
            payload=payload
        )
        await _event_stream.publish(event)
    except Exception as e:
        logger.error(f"[SupervisorService] Event publishing failed: {e}", exc_info=True)
```

### Implementation in service.py

**Modify get_health() (optional):**
```python
async def get_health() -> SupervisorHealth:
    """Get supervisor health status.

    Returns:
        SupervisorHealth: Health status object

    Events:
        - supervisor.health_checked (optional): Health check performed
    """
    result = SupervisorHealth(status="ok", timestamp=datetime.now(timezone.utc))

    # EVENT: supervisor.health_checked (optional)
    await _emit_event_safe("supervisor.health_checked", {
        "status": result.status,
        "checked_at": result.timestamp.timestamp(),
    })

    return result
```

**Modify get_status() (recommended):**
```python
async def get_status() -> SupervisorStatus:
    """Get supervisor status with mission statistics.

    Returns:
        SupervisorStatus: Status object with mission counts

    Events:
        - supervisor.status_queried: Status queried with statistics
    """
    stats_response = await get_stats()
    stats = stats_response.stats

    def count(status: MissionStatus) -> int:
        return int(stats.by_status.get(status, 0))

    total = int(stats.total)
    running = count(MissionStatus.RUNNING)
    pending = count(MissionStatus.PENDING)
    completed = count(MissionStatus.COMPLETED)
    failed = count(MissionStatus.FAILED)
    cancelled = count(MissionStatus.CANCELLED)

    agents: List[AgentStatus] = []

    result = SupervisorStatus(
        status="ok",
        timestamp=datetime.now(timezone.utc),
        total_missions=total,
        running_missions=running,
        pending_missions=pending,
        completed_missions=completed,
        failed_missions=failed,
        cancelled_missions=cancelled,
        agents=agents,
    )

    # EVENT: supervisor.status_queried (recommended)
    await _emit_event_safe("supervisor.status_queried", {
        "total_missions": result.total_missions,
        "running_missions": result.running_missions,
        "pending_missions": result.pending_missions,
        "completed_missions": result.completed_missions,
        "failed_missions": result.failed_missions,
        "cancelled_missions": result.cancelled_missions,
        "agent_count": len(result.agents),
        "queried_at": time.time(),
    })

    return result
```

**Modify list_agents() (optional):**
```python
async def list_agents() -> List[AgentStatus]:
    """List all supervised agents.

    Returns:
        List[AgentStatus]: List of agent statuses

    Events:
        - supervisor.agents_listed (optional): Agents queried
    """
    result = []  # Stub implementation

    # EVENT: supervisor.agents_listed (optional)
    await _emit_event_safe("supervisor.agents_listed", {
        "agent_count": len(result),
        "queried_at": time.time(),
    })

    return result
```

**Lines Added:** ~80 lines

---

## Testing

### Test Suite Structure

**File:** `backend/tests/test_supervisor_events.py`

**Sections:**
1. Mock Infrastructure (MockEventStream, MockEvent, MockMissionStats)
2. Fixtures (setup_supervisor_module, mock_get_stats)
3. Supervisor Tests (3-4 tests)
4. Charter Compliance Test (1 test)

**Total Tests:** 4-5 tests

### Mock Components

```python
import uuid
import time
from typing import List, Dict

class MockEvent:
    """Mock Event class for testing (Charter v1.0)."""
    def __init__(self, type: str, source: str, target, payload: dict):
        self.id = str(uuid.uuid4())
        self.type = type
        self.source = source
        self.target = target
        self.timestamp = time.time()
        self.payload = payload
        self.meta = {}


class MockEventStream:
    """Mock EventStream for capturing events."""
    def __init__(self):
        self.events: List[MockEvent] = []

    async def publish(self, event):
        self.events.append(event)

    def get_events_by_type(self, event_type: str) -> List[MockEvent]:
        return [e for e in self.events if e.type == event_type]


class MockMissionStats:
    """Mock mission statistics."""
    def __init__(self):
        self.total = 150
        self.by_status = {
            "pending": 3,
            "running": 5,
            "completed": 130,
            "failed": 10,
            "cancelled": 2,
        }
        self.last_updated = time.time()


class MockStatsResponse:
    """Mock stats response from missions module."""
    def __init__(self):
        self.stats = MockMissionStats()


async def mock_get_stats():
    """Mock missions.service.get_stats function."""
    return MockStatsResponse()
```

### Test Cases

```python
@pytest.mark.asyncio
async def test_supervisor_health_checked(setup_supervisor_module):
    """Test supervisor.health_checked event emission."""
    service_module, event_stream = setup_supervisor_module

    # Call health function
    result = await service_module.get_health()

    # Verify result
    assert result.status == "ok"

    # Verify event emitted
    events = event_stream.get_events_by_type("supervisor.health_checked")
    assert len(events) == 1

    event = events[0]
    assert event.type == "supervisor.health_checked"
    assert event.source == "supervisor_service"
    assert event.payload["status"] == "ok"
    assert "checked_at" in event.payload


@pytest.mark.asyncio
async def test_supervisor_status_queried(setup_supervisor_module, monkeypatch):
    """Test supervisor.status_queried event with mission statistics."""
    service_module, event_stream = setup_supervisor_module

    # Mock missions.get_stats
    monkeypatch.setattr(service_module, "get_stats", mock_get_stats)

    # Call status function
    result = await service_module.get_status()

    # Verify result has correct mission counts
    assert result.total_missions == 150
    assert result.running_missions == 5
    assert result.pending_missions == 3

    # Verify event emitted
    events = event_stream.get_events_by_type("supervisor.status_queried")
    assert len(events) == 1

    event = events[0]
    assert event.type == "supervisor.status_queried"
    assert event.source == "supervisor_service"
    assert event.payload["total_missions"] == 150
    assert event.payload["running_missions"] == 5
    assert event.payload["completed_missions"] == 130
    assert "queried_at" in event.payload


@pytest.mark.asyncio
async def test_supervisor_agents_listed(setup_supervisor_module):
    """Test supervisor.agents_listed event emission."""
    service_module, event_stream = setup_supervisor_module

    # Call list_agents function
    result = await service_module.list_agents()

    # Verify result (empty list stub)
    assert result == []

    # Verify event emitted
    events = event_stream.get_events_by_type("supervisor.agents_listed")
    assert len(events) == 1

    event = events[0]
    assert event.type == "supervisor.agents_listed"
    assert event.payload["agent_count"] == 0


@pytest.mark.asyncio
async def test_supervisor_charter_compliance(setup_supervisor_module, monkeypatch):
    """Test Supervisor events comply with Charter v1.0."""
    service_module, event_stream = setup_supervisor_module

    # Mock get_stats
    monkeypatch.setattr(service_module, "get_stats", mock_get_stats)

    # Generate all events
    await service_module.get_health()
    await service_module.get_status()
    await service_module.list_agents()

    # Verify all events comply with Charter v1.0
    for event in event_stream.events:
        # Required fields
        assert hasattr(event, 'id')
        assert hasattr(event, 'type')
        assert hasattr(event, 'source')
        assert hasattr(event, 'timestamp')
        assert hasattr(event, 'payload')

        # Field types
        assert isinstance(event.id, str)
        assert isinstance(event.type, str)
        assert isinstance(event.timestamp, float)
        assert isinstance(event.payload, dict)

        # Namespaced type
        assert event.type.startswith("supervisor.")

        # Consistent source
        assert event.source == "supervisor_service"
```

---

## Event Flow Diagrams

### Supervisor Status Query Flow

```
Client (Dashboard/Monitoring Tool)
    │
    │ GET /api/supervisor/status
    ↓
Supervisor Router (router.py)
    │
    │ await get_status()
    ↓
Supervisor Service (service.py)
    │
    │ 1. Call missions.get_stats() → Fetch statistics
    │ 2. Aggregate mission counts by status
    │ 3. Build SupervisorStatus object
    │ 4. Emit supervisor.status_queried event
    │ 5. Return result
    ↓
EventStream
    │
    │ Publish event to Redis
    ↓
Event Consumers
    │
    ├─→ Dashboard Analytics (track query frequency)
    ├─→ Load Monitor (detect high-frequency polling)
    └─→ Audit Logger (record who's monitoring)
```

---

## Migration Checklist

### Phase 1: Event Design ✅
- [x] Document all event types (3 events)
- [x] Define payload schemas
- [x] Specify Charter compliance
- [x] Create integration patterns
- [x] Design test strategy

### Phase 2: Implementation
- [ ] Add module-level EventStream to service.py
- [ ] Implement _emit_event_safe()
- [ ] Fix import paths (app.modules → relative imports)
- [ ] Add event to get_health() (optional)
- [ ] Add event to get_status() (recommended)
- [ ] Add event to list_agents() (optional)

### Phase 3: Consumer Setup (Skipped)
- N/A - No consumers yet

### Phase 4: Testing
- [ ] Create test file with mock infrastructure
- [ ] Mock missions.get_stats dependency
- [ ] Write supervisor module tests (3-4 tests)
- [ ] Write Charter compliance test
- [ ] Verify all tests passing

### Phase 5: Documentation
- [ ] Create migration summary
- [ ] Document code changes
- [ ] Capture lessons learned
- [ ] Git commit and push

---

## Appendix

### Event Type Quick Reference

| Event Type | Priority | Payload Keys |
|------------|----------|--------------|
| `supervisor.health_checked` | OPTIONAL | status, checked_at |
| `supervisor.status_queried` | **MEDIUM** | total_missions, running_missions, pending_missions, completed_missions, failed_missions, cancelled_missions, agent_count, queried_at |
| `supervisor.agents_listed` | OPTIONAL | agent_count, queried_at |

### Source Identifier

| Source | Module | Location |
|--------|--------|----------|
| `supervisor_service` | Supervisor | `service.py` |

### Target Pattern

| Pattern | Description | Example |
|---------|-------------|---------|
| `null` | Broadcast event | All supervisor events |

---

**Specification Version:** 1.0.0
**Status:** ✅ Ready for Implementation (Phase 2)
**Estimated Implementation Time:** 30 minutes
