# Credits & Hardware Modules - EventStream Event Specifications

**Version:** 1.0.0
**Last Updated:** December 29, 2025
**Modules:** Credits, Hardware
**Sprint:** Sprint 5 - Resource Management & Hardware (Modules 1+2)
**Status:** Specification

---

## Table of Contents

1. [Overview](#overview)
2. [Credits Module Events](#credits-module-events)
3. [Hardware Module Events](#hardware-module-events)
4. [Charter v1.0 Compliance](#charter-v10-compliance)
5. [Integration Patterns](#integration-patterns)
6. [Testing](#testing)

---

## Overview

This document specifies EventStream events for the **Credits** and **Hardware** modules. These are combined due to their minimal size (39 lines total) and similar implementation patterns.

### Event Summary

| Module | Event Types | Priority | Total Events |
|--------|-------------|----------|--------------|
| Credits | 1 | Optional | 1 |
| Hardware | 3 | 1 High, 2 Optional | 3 |
| **Total** | **4** | | **4** |

### Event Naming Convention

All events follow the pattern: `{module}.{action}_{object}`

- **Credits:** `credits.*`
- **Hardware:** `hardware.*`

---

## Credits Module Events

### Module Context

The Credits module is a **stub implementation** for resource credit management. It currently provides only health and info endpoints with no real business logic. Events are **OPTIONAL** for telemetry purposes.

### Event Types

#### 1. `credits.health_checked` (OPTIONAL)

**Purpose:** Track module health check requests
**Frequency:** Per GET /api/credits/health
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

**Producer:** `credits_service` (from `service.py`)
**Target:** `null` (broadcast)

**Use Cases:**
- Monitor health check frequency
- Track module availability
- Aggregate uptime metrics

**Charter Envelope:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "credits.health_checked",
  "source": "credits_service",
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
- This event is **OPTIONAL** - can be skipped for minimal stub modules
- If implemented, emit at end of `get_health()` function
- Non-blocking: failures logged, never raised

---

## Hardware Module Events

### Module Context

The Hardware module provides a **Hardware Abstraction Layer (HAL)** for robot control. It supports Unitree robots (Go1, Go2, B2) with motor control, IMU reading, and battery monitoring. Currently returns mock data but events establish patterns for real hardware integration.

### Event Types

#### 1. `hardware.command_sent` (HIGH PRIORITY)

**Purpose:** Track robot movement commands for monitoring and debugging
**Frequency:** Per POST /api/hardware/robots/{robot_id}/command
**Priority:** HIGH (critical operation tracking)

**When Emitted:**
- After successful movement command in `send_movement_command()`

**Payload Schema:**
```typescript
{
  robot_id: string;         // Robot identifier
  command_type: string;     // Command type ("move", "stop", "rotate", etc.)
  command: object;          // Full command payload
  sent_at: number;          // Unix timestamp of command
}
```

**Payload Example:**
```json
{
  "robot_id": "robot_001",
  "command_type": "move",
  "command": {
    "linear": {"x": 1.0, "y": 0.0, "z": 0.0},
    "angular": {"x": 0.0, "y": 0.0, "z": 0.5}
  },
  "sent_at": 1703001234.567
}
```

**Producer:** `hardware_router` (from `router.py`)
**Target:** `robot_{robot_id}` (specific robot)

**Use Cases:**
- Monitor robot command history
- Debug movement issues
- Analyze command patterns
- Safety auditing
- Fleet coordination

**Charter Envelope:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "type": "hardware.command_sent",
  "source": "hardware_router",
  "target": "robot_robot_001",
  "timestamp": 1703001234.567,
  "payload": {
    "robot_id": "robot_001",
    "command_type": "move",
    "command": {
      "linear": {"x": 1.0, "y": 0.0, "z": 0.0},
      "angular": {"x": 0.0, "y": 0.0, "z": 0.5}
    },
    "sent_at": 1703001234.567
  },
  "meta": {}
}
```

**Implementation Notes:**
- **Required event** - always emit
- Extract command_type from MovementCommand schema
- Include full command object for debugging
- Target specific robot for event routing

---

#### 2. `hardware.state_queried` (OPTIONAL)

**Purpose:** Monitor robot state queries for diagnostics
**Frequency:** Per GET /api/hardware/robots/{robot_id}/state
**Priority:** MEDIUM (useful telemetry)

**When Emitted:**
- After returning robot state in `get_robot_state()`

**Payload Schema:**
```typescript
{
  robot_id: string;         // Robot identifier
  queried_at: number;       // Unix timestamp of query
}
```

**Payload Example:**
```json
{
  "robot_id": "robot_001",
  "queried_at": 1703001234.567
}
```

**Producer:** `hardware_router` (from `router.py`)
**Target:** `robot_{robot_id}` (specific robot)

**Use Cases:**
- Track state query frequency
- Monitor polling patterns
- Identify overactive clients

**Charter Envelope:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "type": "hardware.state_queried",
  "source": "hardware_router",
  "target": "robot_robot_001",
  "timestamp": 1703001234.567,
  "payload": {
    "robot_id": "robot_001",
    "queried_at": 1703001234.567
  },
  "meta": {}
}
```

**Implementation Notes:**
- **Optional event** - can be skipped to reduce noise
- Useful for monitoring query patterns
- Consider rate limiting if implemented

---

#### 3. `hardware.info_queried` (OPTIONAL)

**Purpose:** Track module information queries
**Frequency:** Per GET /api/hardware/info
**Priority:** LOW (optional telemetry)

**When Emitted:**
- After returning module info in `get_hardware_info()`

**Payload Schema:**
```typescript
{
  version: string;          // Module version
  queried_at: number;       // Unix timestamp of query
}
```

**Payload Example:**
```json
{
  "version": "1.0.0",
  "queried_at": 1703001234.567
}
```

**Producer:** `hardware_router` (from `router.py`)
**Target:** `null` (broadcast)

**Use Cases:**
- Track module discovery
- Monitor info endpoint usage
- Audit client requests

**Charter Envelope:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440003",
  "type": "hardware.info_queried",
  "source": "hardware_router",
  "target": null,
  "timestamp": 1703001234.567,
  "payload": {
    "version": "1.0.0",
    "queried_at": 1703001234.567
  },
  "meta": {}
}
```

**Implementation Notes:**
- **Optional event** - can be skipped for minimal telemetry
- Low priority due to infrequent usage
- Useful for tracking module discovery

---

## Charter v1.0 Compliance

All events follow the Charter v1.0 specification:

```python
@dataclass
class Event:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str                    # "credits.*" or "hardware.*"
    source: str                  # "credits_service" or "hardware_router"
    target: Optional[str] = None # Robot ID or null
    timestamp: float = field(default_factory=time.time)
    payload: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)
```

### Required Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | UUID string | Auto-generated unique ID | `"550e8400-e29b-41d4-a716-446655440000"` |
| `type` | string | Event type (namespaced) | `"hardware.command_sent"` |
| `source` | string | Event producer | `"hardware_router"` |
| `target` | string/null | Event destination | `"robot_robot_001"` or `null` |
| `timestamp` | float | Unix timestamp | `1703001234.567` |
| `payload` | object | Event data | `{"robot_id": "robot_001", ...}` |
| `meta` | object | Metadata (optional) | `{}` |

### Validation Rules

1. ✅ All events have UUID `id`
2. ✅ All events have namespaced `type` (module.action)
3. ✅ All events have consistent `source`
4. ✅ All events have auto-generated `timestamp`
5. ✅ All payloads contain required fields
6. ✅ Timestamps are Unix epoch (seconds with decimal)

---

## Integration Patterns

### Module-Level EventStream Pattern

Both Credits and Hardware modules use **module-level EventStream** (functional architecture):

```python
from typing import Optional
import time
import logging

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
    """Initialize EventStream for this module."""
    global _event_stream
    _event_stream = stream

async def _emit_event_safe(event_type: str, payload: dict) -> None:
    """Emit event with error handling (non-blocking).

    Args:
        event_type: Event type (e.g., "hardware.command_sent")
        payload: Event payload dictionary

    Note:
        - Never raises exceptions
        - Logs failures at ERROR level
        - Gracefully handles missing EventStream
    """
    global _event_stream
    if _event_stream is None or Event is None:
        logger.debug("[ModuleName] EventStream not available, skipping event")
        return

    try:
        event = Event(
            type=event_type,
            source="module_name",
            target=None,  # Override per event
            payload=payload
        )
        await _event_stream.publish(event)
    except Exception as e:
        logger.error(f"Event publishing failed: {e}", exc_info=True)
        # Never raise - graceful degradation
```

### Credits Module Integration

**File:** `backend/app/modules/credits/service.py`

```python
# Add at module level (after imports)
_event_stream: Optional["EventStream"] = None

def set_event_stream(stream: "EventStream") -> None:
    global _event_stream
    _event_stream = stream

async def _emit_event_safe(event_type: str, payload: dict) -> None:
    # ... implementation above

# Modify get_health() function
async def get_health() -> CreditsHealth:
    result = CreditsHealth(status="ok", timestamp=datetime.now(timezone.utc))

    # EVENT: credits.health_checked (optional)
    await _emit_event_safe("credits.health_checked", {
        "status": result.status,
        "checked_at": result.timestamp.timestamp(),
    })

    return result
```

**Lines Added:** ~30 lines

### Hardware Module Integration

**File:** `backend/app/modules/hardware/router.py`

```python
# Add at module level (after imports)
_event_stream: Optional["EventStream"] = None

def set_event_stream(stream: "EventStream") -> None:
    global _event_stream
    _event_stream = stream

async def _emit_event_safe(event_type: str, payload: dict) -> None:
    # ... implementation above

# Convert get_hardware_info to async
@router.get("/info")
async def get_hardware_info():
    result = {
        "name": "Hardware Abstraction Layer",
        "version": "1.0.0",
        "supported_platforms": ["unitree_go1", "unitree_go2", "unitree_b2"],
        "features": ["Motor control", "IMU reading", "Battery monitoring"]
    }

    # EVENT: hardware.info_queried (optional)
    await _emit_event_safe("hardware.info_queried", {
        "version": result["version"],
        "queried_at": time.time(),
    })

    return result

# Modify send_movement_command()
@router.post("/robots/{robot_id}/command")
async def send_movement_command(robot_id: str, command: MovementCommand):
    result = {"robot_id": robot_id, "status": "command_sent", "command": command}

    # EVENT: hardware.command_sent (required)
    await _emit_event_safe("hardware.command_sent", {
        "robot_id": robot_id,
        "command_type": getattr(command, 'type', 'movement'),
        "command": command.model_dump(),
        "sent_at": time.time(),
    })

    return result

# Modify get_robot_state()
@router.get("/robots/{robot_id}/state")
async def get_robot_state(robot_id: str):
    result = {"robot_id": robot_id, "status": "mock_state"}

    # EVENT: hardware.state_queried (optional)
    await _emit_event_safe("hardware.state_queried", {
        "robot_id": robot_id,
        "queried_at": time.time(),
    })

    return result
```

**Lines Added:** ~40 lines

---

## Testing

### Test Suite Structure

**File:** `backend/tests/test_credits_hardware_events.py`

**Sections:**
1. Mock Infrastructure (MockEventStream, MockEvent)
2. Fixtures (setup_credits_module, setup_hardware_module)
3. Credits Tests (1-2 tests)
4. Hardware Tests (3 tests)
5. Charter Compliance Tests (2 tests)

**Total Tests:** 6-8 tests

### Mock Components

```python
import uuid
import time
from typing import List

class MockEvent:
    """Mock Event class for testing."""
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
        """Capture published event."""
        self.events.append(event)

    def get_events_by_type(self, event_type: str) -> List[MockEvent]:
        """Get all events of specific type."""
        return [e for e in self.events if e.type == event_type]

    def clear(self):
        """Clear all captured events."""
        self.events = []
```

### Test Cases

#### Credits Module Tests

```python
@pytest.mark.asyncio
async def test_credits_health_checked(setup_credits_module):
    """Test credits.health_checked event emission."""
    service_module, event_stream = setup_credits_module

    # Call health function
    result = await service_module.get_health()

    # Verify event emitted
    events = event_stream.get_events_by_type("credits.health_checked")
    assert len(events) == 1

    event = events[0]
    assert event.type == "credits.health_checked"
    assert event.source == "credits_service"
    assert event.payload["status"] == "ok"
    assert "checked_at" in event.payload

@pytest.mark.asyncio
async def test_credits_charter_compliance(setup_credits_module):
    """Test Credits events comply with Charter v1.0."""
    service_module, event_stream = setup_credits_module

    await service_module.get_health()

    for event in event_stream.events:
        # Verify required fields
        assert hasattr(event, 'id')
        assert hasattr(event, 'type')
        assert hasattr(event, 'source')
        assert hasattr(event, 'timestamp')
        assert hasattr(event, 'payload')
        assert hasattr(event, 'meta')

        # Verify types
        assert isinstance(event.id, str)
        assert isinstance(event.type, str)
        assert isinstance(event.timestamp, float)
        assert isinstance(event.payload, dict)
```

#### Hardware Module Tests

```python
@pytest.mark.asyncio
async def test_hardware_command_sent(setup_hardware_module):
    """Test hardware.command_sent event emission."""
    router_module, event_stream, mock_command = setup_hardware_module

    # Send command
    result = await router_module.send_movement_command("robot_001", mock_command)

    # Verify event emitted
    events = event_stream.get_events_by_type("hardware.command_sent")
    assert len(events) == 1

    event = events[0]
    assert event.type == "hardware.command_sent"
    assert event.source == "hardware_router"
    assert event.payload["robot_id"] == "robot_001"
    assert "command" in event.payload
    assert "sent_at" in event.payload

@pytest.mark.asyncio
async def test_hardware_state_queried(setup_hardware_module):
    """Test hardware.state_queried event emission (if implemented)."""
    router_module, event_stream, _ = setup_hardware_module

    # Query state
    result = await router_module.get_robot_state("robot_001")

    # Verify event emitted
    events = event_stream.get_events_by_type("hardware.state_queried")
    assert len(events) == 1

    event = events[0]
    assert event.payload["robot_id"] == "robot_001"
    assert "queried_at" in event.payload

@pytest.mark.asyncio
async def test_hardware_charter_compliance(setup_hardware_module):
    """Test Hardware events comply with Charter v1.0."""
    router_module, event_stream, mock_command = setup_hardware_module

    await router_module.send_movement_command("robot_001", mock_command)

    for event in event_stream.events:
        assert hasattr(event, 'id')
        assert hasattr(event, 'type')
        assert event.type.startswith("hardware.")
        assert event.source == "hardware_router"
        assert isinstance(event.timestamp, float)
```

### Test Fixtures

```python
@pytest.fixture
def mock_event_stream():
    """Provide MockEventStream instance."""
    return MockEventStream()

@pytest.fixture
def setup_credits_module(mock_event_stream):
    """Setup Credits module with mocked EventStream."""
    import backend.app.modules.credits.service as service_module

    # Store original Event class
    original_event = service_module.Event if hasattr(service_module, 'Event') else None

    # Mock Event class
    service_module.Event = MockEvent

    # Set event stream
    service_module.set_event_stream(mock_event_stream)

    yield service_module, mock_event_stream

    # Cleanup
    if original_event:
        service_module.Event = original_event
    service_module.set_event_stream(None)
    mock_event_stream.clear()

@pytest.fixture
def setup_hardware_module(mock_event_stream):
    """Setup Hardware module with mocked EventStream."""
    import backend.app.modules.hardware.router as router_module
    from backend.app.modules.hardware.schemas import MovementCommand

    # Store original Event class
    original_event = router_module.Event if hasattr(router_module, 'Event') else None

    # Mock Event class
    router_module.Event = MockEvent

    # Set event stream
    router_module.set_event_stream(mock_event_stream)

    # Create mock command
    mock_command = MovementCommand(
        linear={"x": 1.0, "y": 0.0, "z": 0.0},
        angular={"x": 0.0, "y": 0.0, "z": 0.5}
    )

    yield router_module, mock_event_stream, mock_command

    # Cleanup
    if original_event:
        router_module.Event = original_event
    router_module.set_event_stream(None)
    mock_event_stream.clear()
```

---

## Event Flow Diagrams

### Credits Health Check Flow

```
User/Client
    │
    │ GET /api/credits/health
    ↓
Credits Router (router.py)
    │
    │ await get_health()
    ↓
Credits Service (service.py)
    │
    │ 1. Create CreditsHealth object
    │ 2. Emit credits.health_checked (optional)
    │ 3. Return result
    ↓
EventStream (if available)
    │
    │ Publish event to Redis
    ↓
Event Consumers (future)
```

### Hardware Command Flow

```
User/Client
    │
    │ POST /api/hardware/robots/robot_001/command
    ↓
Hardware Router (router.py)
    │
    │ await send_movement_command(robot_id, command)
    ↓
send_movement_command()
    │
    │ 1. Process command
    │ 2. Emit hardware.command_sent (required)
    │ 3. Return result {"status": "command_sent"}
    ↓
EventStream
    │
    │ Publish event to Redis
    │ Target: robot_robot_001
    ↓
Event Consumers
    │
    ├─→ Fleet Manager (track commands)
    ├─→ Safety Monitor (validate commands)
    └─→ Telemetry Logger (record history)
```

---

## Migration Checklist

### Phase 1: Event Design ✅
- [x] Document all event types
- [x] Define payload schemas
- [x] Specify Charter compliance
- [x] Create integration patterns
- [x] Design test strategy

### Phase 2: Implementation
- [ ] Credits: Add module-level EventStream
- [ ] Credits: Implement _emit_event_safe()
- [ ] Credits: Add event to get_health() (optional)
- [ ] Hardware: Add module-level EventStream
- [ ] Hardware: Implement _emit_event_safe()
- [ ] Hardware: Convert get_hardware_info() to async
- [ ] Hardware: Add event to send_movement_command() (required)
- [ ] Hardware: Add event to get_robot_state() (optional)
- [ ] Hardware: Add event to get_hardware_info() (optional)

### Phase 3: Consumer Setup (Skipped)
- N/A - No consumers yet

### Phase 4: Testing
- [ ] Create test file with mock infrastructure
- [ ] Write Credits module tests (1-2 tests)
- [ ] Write Hardware module tests (3 tests)
- [ ] Write Charter compliance tests (2 tests)
- [ ] Verify all tests passing

### Phase 5: Documentation
- [ ] Create migration summary
- [ ] Document code changes
- [ ] Capture lessons learned
- [ ] Git commit and push

---

## Appendix

### Event Type Quick Reference

| Event Type | Module | Priority | Payload Keys |
|------------|--------|----------|--------------|
| `credits.health_checked` | Credits | OPTIONAL | status, checked_at |
| `hardware.command_sent` | Hardware | HIGH | robot_id, command_type, command, sent_at |
| `hardware.state_queried` | Hardware | OPTIONAL | robot_id, queried_at |
| `hardware.info_queried` | Hardware | OPTIONAL | version, queried_at |

### Source Identifiers

| Source | Module | Location |
|--------|--------|----------|
| `credits_service` | Credits | `service.py` |
| `hardware_router` | Hardware | `router.py` |

### Target Patterns

| Pattern | Description | Example |
|---------|-------------|---------|
| `null` | Broadcast event | General telemetry |
| `robot_{robot_id}` | Robot-specific | `robot_robot_001` |

---

**Specification Version:** 1.0.0
**Status:** ✅ Ready for Implementation (Phase 2)
**Estimated Implementation Time:** 30 minutes
