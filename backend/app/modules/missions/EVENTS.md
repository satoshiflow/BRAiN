# Missions Module - EventStream Event Specifications

**Version:** 1.0.0
**Last Updated:** December 29, 2025
**Module:** Missions
**Sprint:** Sprint 5 - Resource Management & Hardware (Module 4/4 - Final)
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

This document specifies EventStream events for the **Missions** module. The Missions module provides the core mission lifecycle management system with Redis-based CRUD operations, logging, and statistics tracking.

### Event Summary

| Event Type | Priority | Frequency | Use Case |
|------------|----------|-----------|----------|
| mission.created | **HIGH** | Per mission creation | **Critical lifecycle event, audit trail** |
| mission.status_changed | **HIGH** | Per status update | **Most important - workflow automation** |
| mission.log_appended | MEDIUM | Per log entry | Debugging, progress tracking |

**Primary Events:** All 3 events are important for mission lifecycle tracking and workflow automation.

### Event Naming Convention

All events follow the pattern: `mission.{action}_{object}`

---

## Event Types

### 1. mission.created (HIGH PRIORITY)

**Purpose:** Track mission creation for workflow triggering and audit trail
**Frequency:** Per POST /api/missions (mission creation)
**Priority:** HIGH (critical lifecycle event)

**When Emitted:**
- After successful mission creation in `create_mission()`
- After mission is saved to Redis
- After initial log entry is created

**Payload Schema:**
```typescript
{
  mission_id: string;          // Unique mission identifier
  name: string;                // Mission name
  description: string;         // Mission description (may be empty)
  status: string;              // Initial status (always "PENDING")
  created_at: number;          // Unix timestamp of creation
}
```

**Payload Example:**
```json
{
  "mission_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Deploy Application v2.0",
  "description": "Deploy new version to production",
  "status": "PENDING",
  "created_at": 1703001234.567
}
```

**Producer:** `missions_service` (from `service.py`)
**Target:** `null` (broadcast)

**Use Cases:**
- **Workflow Triggers** - Start automated workflows on mission creation
- **Notifications** - Alert teams when new missions are created
- **Audit Trail** - Complete record of mission creation events
- **Analytics** - Track mission creation patterns and volume
- **Integration** - Trigger external systems (ticketing, monitoring)

**Charter Envelope:**
```json
{
  "id": "e7a8b3c4-d1e2-4f5a-b6c7-8d9e0f1a2b3c",
  "type": "mission.created",
  "source": "missions_service",
  "target": null,
  "timestamp": 1703001234.567,
  "payload": {
    "mission_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Deploy Application v2.0",
    "description": "Deploy new version to production",
    "status": "PENDING",
    "created_at": 1703001234.567
  },
  "meta": {}
}
```

**Implementation Notes:**
- **Required event** - always emit
- Emit after Redis save and stats update
- Include full mission details for downstream processing
- Status is always "PENDING" at creation time

---

### 2. mission.status_changed (HIGH PRIORITY)

**Purpose:** Track mission status transitions for workflow automation and monitoring
**Frequency:** Per POST /api/missions/{id}/status (status update)
**Priority:** HIGH (most critical event - drives mission lifecycle)

**When Emitted:**
- After successful status update in `update_status()`
- After mission is saved to Redis with new status
- After statistics are updated
- After log entry is created

**Payload Schema:**
```typescript
{
  mission_id: string;          // Mission identifier
  old_status: string;          // Previous status
  new_status: string;          // New status
  changed_at: number;          // Unix timestamp of change
}
```

**Payload Example:**
```json
{
  "mission_id": "550e8400-e29b-41d4-a716-446655440000",
  "old_status": "PENDING",
  "new_status": "RUNNING",
  "changed_at": 1703001300.123
}
```

**Producer:** `missions_service` (from `service.py`)
**Target:** `mission_{mission_id}` (targeted to specific mission)

**Status Transitions:**

| From | To | Meaning | Trigger Actions |
|------|----|---------|-----------------
| PENDING | RUNNING | Mission started | Begin execution, allocate resources |
| RUNNING | COMPLETED | Mission succeeded | Cleanup, send success notification |
| RUNNING | FAILED | Mission failed | Cleanup, send alert, trigger retry? |
| ANY | CANCELLED | Mission cancelled | Cleanup, free resources |

**Use Cases:**
- **Workflow Automation** - Trigger next steps on status change
- **Resource Management** - Allocate/deallocate resources
- **Alerting** - Send alerts on FAILED status
- **Analytics** - Track mission success rates, duration
- **Monitoring** - Real-time mission state tracking
- **Retry Logic** - Trigger retries on failure
- **Cleanup** - Free resources on completion/cancellation

**Why Most Important:**
- Drives entire mission lifecycle
- Enables reactive workflows
- Critical for success/failure tracking
- Supports automatic remediation

**Charter Envelope:**
```json
{
  "id": "a1b2c3d4-e5f6-4789-a0b1-2c3d4e5f6789",
  "type": "mission.status_changed",
  "source": "missions_service",
  "target": "mission_550e8400-e29b-41d4-a716-446655440000",
  "timestamp": 1703001300.123,
  "payload": {
    "mission_id": "550e8400-e29b-41d4-a716-446655440000",
    "old_status": "PENDING",
    "new_status": "RUNNING",
    "changed_at": 1703001300.123
  },
  "meta": {}
}
```

**Implementation Notes:**
- **Required event** - always emit
- Include both old and new status for complete context
- Target specific mission for efficient event routing
- Emit after all state changes are complete

---

### 3. mission.log_appended (MEDIUM PRIORITY)

**Purpose:** Track mission progress and debugging information
**Frequency:** Per POST /api/missions/{id}/log (log entry addition)
**Priority:** MEDIUM (useful for debugging and progress tracking)

**When Emitted:**
- After log entry is appended in `append_log_entry()`
- After entry is saved to Redis list

**Payload Schema:**
```typescript
{
  mission_id: string;          // Mission identifier
  log_level: string;           // Log level (info, warning, error, debug)
  message: string;             // Log message
  appended_at: number;         // Unix timestamp of log entry
}
```

**Payload Example:**
```json
{
  "mission_id": "550e8400-e29b-41d4-a716-446655440000",
  "log_level": "info",
  "message": "Deployment step 3/5 completed successfully",
  "appended_at": 1703001350.789
}
```

**Producer:** `missions_service` (from `service.py`)
**Target:** `mission_{mission_id}` (targeted to specific mission)

**Log Levels:**
- `info` - Normal progress information
- `warning` - Non-critical issues
- `error` - Errors occurred (but mission continues)
- `debug` - Detailed debugging information

**Use Cases:**
- **Progress Tracking** - Monitor mission execution progress
- **Debugging** - Troubleshoot mission failures
- **Audit Trail** - Complete log of mission activities
- **Real-time Updates** - Stream progress to dashboards
- **Alerting** - Trigger alerts on error log entries

**Charter Envelope:**
```json
{
  "id": "b2c3d4e5-f6a7-4890-b1c2-3d4e5f6a7890",
  "type": "mission.log_appended",
  "source": "missions_service",
  "target": "mission_550e8400-e29b-41d4-a716-446655440000",
  "timestamp": 1703001350.789,
  "payload": {
    "mission_id": "550e8400-e29b-41d4-a716-446655440000",
    "log_level": "info",
    "message": "Deployment step 3/5 completed successfully",
    "appended_at": 1703001350.789
  },
  "meta": {}
}
```

**Implementation Notes:**
- **Recommended event** - valuable for debugging
- Emit after Redis append operation
- Include full log details for downstream processing
- Target specific mission for log streaming

---

## Charter v1.0 Compliance

All events follow the Charter v1.0 specification:

```python
@dataclass
class Event:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str                    # "mission.*"
    source: str                  # "missions_service"
    target: Optional[str] = None # "mission_{id}" or null
    timestamp: float = field(default_factory=time.time)
    payload: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)
```

### Required Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | UUID string | Auto-generated unique ID | `"e7a8b3c4-d1e2-4f5a-b6c7-8d9e0f1a2b3c"` |
| `type` | string | Event type (namespaced) | `"mission.status_changed"` |
| `source` | string | Event producer | `"missions_service"` |
| `target` | string/null | Event destination | `"mission_{id}"` or `null` |
| `timestamp` | float | Unix timestamp | `1703001234.567` |
| `payload` | object | Event data | `{"mission_id": "...", ...}` |
| `meta` | object | Metadata (optional) | `{}` |

### Validation Rules

1. ✅ All events have UUID `id`
2. ✅ All events have namespaced `type` (mission.*)
3. ✅ All events have consistent `source` (missions_service)
4. ✅ All events have auto-generated `timestamp`
5. ✅ All payloads contain required fields
6. ✅ Timestamps are Unix epoch (seconds with decimal)

---

## Integration Pattern

### Module-Level EventStream Pattern

Missions module uses **module-level EventStream** (functional architecture):

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
    """Initialize EventStream for Missions module."""
    global _event_stream
    _event_stream = stream


async def _emit_event_safe(event_type: str, payload: dict, target: Optional[str] = None) -> None:
    """Emit mission event with error handling (non-blocking).

    Args:
        event_type: Event type (e.g., "mission.status_changed")
        payload: Event payload dictionary
        target: Optional target (e.g., "mission_{id}")

    Note:
        - Never raises exceptions
        - Logs failures at ERROR level
        - Gracefully handles missing EventStream
    """
    global _event_stream
    if _event_stream is None or Event is None:
        logger.debug("[MissionsService] EventStream not available, skipping event")
        return

    try:
        event = Event(
            type=event_type,
            source="missions_service",
            target=target,
            payload=payload
        )
        await _event_stream.publish(event)
    except Exception as e:
        logger.error(f"[MissionsService] Event publishing failed: {e}", exc_info=True)
```

### Implementation in service.py

**Modify create_mission():**
```python
async def create_mission(payload: MissionCreate) -> Mission:
    """Create new mission.

    Returns:
        Mission: Created mission object

    Events:
        - mission.created: Mission created successfully
    """
    redis: Any = await get_redis()
    mission_id = payload.id or str(uuid.uuid4())
    now = time.time()
    mission = Mission(
        id=mission_id,
        name=payload.name,
        description=payload.description,
        data=payload.data,
        status=MissionStatus.PENDING,
        created_at=now,
        updated_at=now,
    )
    await redis.set(_mission_key(mission_id), mission.model_dump_json())
    await redis.sadd(MISSION_INDEX_KEY, mission_id)
    await _update_stats_on_create(redis, mission.status)

    entry = MissionLogEntry(
        level="info",
        message="Mission created",
        data={"name": mission.name, "description": mission.description},
    )
    await append_log_entry(mission_id, entry)

    # EVENT: mission.created (HIGH PRIORITY)
    await _emit_event_safe("mission.created", {
        "mission_id": mission.id,
        "name": mission.name,
        "description": mission.description or "",
        "status": mission.status.value,
        "created_at": mission.created_at,
    })

    return mission
```

**Modify update_status():**
```python
async def update_status(mission_id: str, status: MissionStatus) -> Optional[Mission]:
    """Update mission status.

    Args:
        mission_id: Mission identifier
        status: New mission status

    Returns:
        Mission: Updated mission object (or None if not found)

    Events:
        - mission.status_changed: Status updated successfully
    """
    redis: Any = await get_redis()
    mission = await get_mission(mission_id)
    if not mission:
        return None

    old_status = mission.status
    mission.status = status
    mission.updated_at = time.time()

    await redis.set(_mission_key(mission_id), mission.model_dump_json())
    await _update_stats_on_status_change(redis, old_status, status)

    entry = MissionLogEntry(
        level="info",
        message="Mission status changed",
        data={"from": old_status, "to": status},
    )
    await append_log_entry(mission_id, entry)

    # EVENT: mission.status_changed (HIGH PRIORITY)
    await _emit_event_safe("mission.status_changed", {
        "mission_id": mission.id,
        "old_status": old_status.value,
        "new_status": mission.status.value,
        "changed_at": mission.updated_at,
    }, target=f"mission_{mission.id}")

    return mission
```

**Modify append_log_entry():**
```python
async def append_log_entry(mission_id: str, entry: MissionLogEntry) -> None:
    """Append log entry to mission.

    Args:
        mission_id: Mission identifier
        entry: Log entry to append

    Events:
        - mission.log_appended: Log entry added
    """
    redis: Any = await get_redis()
    await redis.rpush(_mission_log_key(mission_id), entry.model_dump_json())

    # EVENT: mission.log_appended (MEDIUM PRIORITY)
    await _emit_event_safe("mission.log_appended", {
        "mission_id": mission_id,
        "log_level": entry.level,
        "message": entry.message,
        "appended_at": entry.timestamp,
    }, target=f"mission_{mission_id}")
```

**Lines Added:** ~74 lines total

---

## Testing

### Test Suite Structure

**File:** `backend/tests/test_missions_events.py`

**Sections:**
1. Mock Infrastructure (MockRedis, MockEventStream, MockEvent)
2. Fixtures (setup_missions_module, mock_redis)
3. Mission Tests (5-6 tests)
4. Charter Compliance Test

**Total Tests:** 5-6 tests

### Mock Components

```python
import uuid
import time
import json
from typing import Dict, List, Set

class MockRedis:
    """Comprehensive Redis mock for missions testing."""

    def __init__(self):
        self.data: Dict[str, str] = {}      # Key-value store
        self.sets: Dict[str, Set] = {}      # Set storage
        self.lists: Dict[str, List] = {}    # List storage

    async def get(self, key: str):
        """Get value by key."""
        return self.data.get(key)

    async def set(self, key: str, value: str):
        """Set key-value pair."""
        self.data[key] = value

    async def sadd(self, key: str, value: str):
        """Add to set."""
        if key not in self.sets:
            self.sets[key] = set()
        self.sets[key].add(value)

    async def smembers(self, key: str):
        """Get set members."""
        return self.sets.get(key, set())

    async def rpush(self, key: str, value: str):
        """Append to list."""
        if key not in self.lists:
            self.lists[key] = []
        self.lists[key].append(value)

    async def lrange(self, key: str, start: int, stop: int):
        """Get list range."""
        lst = self.lists.get(key, [])
        if stop == -1:
            return lst[start:]
        return lst[start:stop+1]


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

    def get_events_by_type(self, event_type: str):
        return [e for e in self.events if e.type == event_type]
```

### Test Cases

```python
@pytest.mark.asyncio
async def test_mission_created(setup_missions_module, sample_mission_create):
    """Test mission.created event emission."""
    service_module, event_stream = setup_missions_module

    # Create mission
    mission = await service_module.create_mission(sample_mission_create)

    # Verify mission created
    assert mission.id is not None
    assert mission.status == MissionStatus.PENDING

    # Verify event emitted
    created_events = event_stream.get_events_by_type("mission.created")
    assert len(created_events) == 1

    event = created_events[0]
    assert event.type == "mission.created"
    assert event.source == "missions_service"
    assert event.payload["mission_id"] == mission.id
    assert event.payload["name"] == sample_mission_create.name
    assert event.payload["status"] == "PENDING"


@pytest.mark.asyncio
async def test_mission_status_changed(setup_missions_module, sample_mission_create):
    """Test mission.status_changed event emission."""
    service_module, event_stream = setup_missions_module

    # Create mission
    mission = await service_module.create_mission(sample_mission_create)
    event_stream.events.clear()  # Clear creation event

    # Update status
    updated_mission = await service_module.update_status(
        mission.id, MissionStatus.RUNNING
    )

    # Verify event emitted
    status_events = event_stream.get_events_by_type("mission.status_changed")
    assert len(status_events) == 1

    event = status_events[0]
    assert event.payload["mission_id"] == mission.id
    assert event.payload["old_status"] == "PENDING"
    assert event.payload["new_status"] == "RUNNING"
    assert event.target == f"mission_{mission.id}"


@pytest.mark.asyncio
async def test_mission_log_appended(setup_missions_module, sample_mission_create):
    """Test mission.log_appended event emission."""
    service_module, event_stream = setup_missions_module

    # Create mission
    mission = await service_module.create_mission(sample_mission_create)
    event_stream.events.clear()  # Clear previous events

    # Append log entry
    log_entry = MissionLogEntry(
        level="info",
        message="Test log message"
    )
    await service_module.append_log_entry(mission.id, log_entry)

    # Verify event emitted
    log_events = event_stream.get_events_by_type("mission.log_appended")
    assert len(log_events) >= 1  # At least one (may have creation log too)

    # Find our test log event
    test_log_event = next(
        e for e in log_events if e.payload["message"] == "Test log message"
    )
    assert test_log_event.payload["mission_id"] == mission.id
    assert test_log_event.payload["log_level"] == "info"


@pytest.mark.asyncio
async def test_mission_status_transitions(setup_missions_module, sample_mission_create):
    """Test multiple status transitions emit events correctly."""
    service_module, event_stream = setup_missions_module

    # Create mission
    mission = await service_module.create_mission(sample_mission_create)
    event_stream.events.clear()

    # Transition: PENDING → RUNNING → COMPLETED
    await service_module.update_status(mission.id, MissionStatus.RUNNING)
    await service_module.update_status(mission.id, MissionStatus.COMPLETED)

    # Verify 2 status change events
    status_events = event_stream.get_events_by_type("mission.status_changed")
    assert len(status_events) == 2

    # Verify first transition
    assert status_events[0].payload["old_status"] == "PENDING"
    assert status_events[0].payload["new_status"] == "RUNNING"

    # Verify second transition
    assert status_events[1].payload["old_status"] == "RUNNING"
    assert status_events[1].payload["new_status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_mission_charter_compliance(setup_missions_module, sample_mission_create):
    """Test Mission events comply with Charter v1.0."""
    service_module, event_stream = setup_missions_module

    # Generate all events
    mission = await service_module.create_mission(sample_mission_create)
    await service_module.update_status(mission.id, MissionStatus.RUNNING)
    await service_module.append_log_entry(
        mission.id,
        MissionLogEntry(level="info", message="Test")
    )

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
        assert event.type.startswith("mission.")

        # Consistent source
        assert event.source == "missions_service"
```

---

## Event Flow Diagrams

### Mission Creation Flow

```
Client
    │
    │ POST /api/missions
    ↓
Missions Router (router.py)
    │
    │ await create_mission(payload)
    ↓
Missions Service (service.py)
    │
    │ 1. Generate mission ID
    │ 2. Create Mission object (status=PENDING)
    │ 3. Save to Redis (SET + SADD to index)
    │ 4. Update statistics
    │ 5. Append "Mission created" log entry
    │ 6. Emit mission.created event
    │ 7. Return mission
    ↓
EventStream
    │
    │ Publish event to Redis
    ↓
Event Consumers
    │
    ├─→ Workflow Engine (trigger automated workflows)
    ├─→ Notification Service (alert teams)
    └─→ Analytics Collector (track creation patterns)
```

### Mission Status Change Flow

```
Client
    │
    │ POST /api/missions/{id}/status
    ↓
Missions Router (router.py)
    │
    │ await update_status(mission_id, new_status)
    ↓
Missions Service (service.py)
    │
    │ 1. Get current mission
    │ 2. Store old_status
    │ 3. Update to new_status
    │ 4. Save to Redis
    │ 5. Update statistics
    │ 6. Append status change log entry
    │ 7. Emit mission.status_changed event (with target)
    │ 8. Return updated mission
    ↓
EventStream
    │
    │ Publish event to Redis (targeted to mission)
    ↓
Event Consumers (targeted)
    │
    ├─→ Workflow Engine (trigger next steps)
    ├─→ Resource Manager (allocate/free resources)
    └─→ Alert Service (notify on failures)
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
- [ ] Fix import path in router.py (app.core → ...core)
- [ ] Add event to create_mission()
- [ ] Add event to update_status()
- [ ] Add event to append_log_entry()

### Phase 3: Consumer Setup (Skipped)
- N/A - No consumers yet

### Phase 4: Testing
- [ ] Create test file with mock infrastructure
- [ ] Create comprehensive MockRedis
- [ ] Write mission module tests (5-6 tests)
- [ ] Write Charter compliance test
- [ ] Verify all tests passing

### Phase 5: Documentation
- [ ] Create migration summary
- [ ] Document code changes
- [ ] Capture lessons learned
- [ ] Git commit and push
- [ ] Create Sprint 5 completion summary

---

## Appendix

### Event Type Quick Reference

| Event Type | Priority | Payload Keys | Target |
|------------|----------|--------------|--------|
| `mission.created` | **HIGH** | mission_id, name, description, status, created_at | null |
| `mission.status_changed` | **HIGH** | mission_id, old_status, new_status, changed_at | mission_{id} |
| `mission.log_appended` | MEDIUM | mission_id, log_level, message, appended_at | mission_{id} |

### Source Identifier

| Source | Module | Location |
|--------|--------|----------|
| `missions_service` | Missions | `service.py` |

### Target Patterns

| Pattern | Description | Example |
|---------|-------------|---------|
| `null` | Broadcast event | mission.created |
| `mission_{id}` | Mission-specific | mission.status_changed |

### MissionStatus Enum Values

| Status | Value | Meaning |
|--------|-------|---------|
| PENDING | "PENDING" | Mission created, not started |
| RUNNING | "RUNNING" | Mission currently executing |
| COMPLETED | "COMPLETED" | Mission finished successfully |
| FAILED | "FAILED" | Mission failed |
| CANCELLED | "CANCELLED" | Mission cancelled by user |

---

**Specification Version:** 1.0.0
**Status:** ✅ Ready for Implementation (Phase 2)
**Estimated Implementation Time:** 40 minutes
