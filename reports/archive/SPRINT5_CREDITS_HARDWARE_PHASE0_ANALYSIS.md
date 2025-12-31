# Sprint 5 Phase 0: Credits & Hardware Modules Analysis

**Analysis Date:** December 29, 2025
**Modules:** Credits, Hardware
**Sprint:** Sprint 5 - Resource Management & Hardware (Modules 1+2)
**Strategy:** Combined implementation (efficiency optimization)

---

## Executive Summary

Pre-migration analysis for **Credits** and **Hardware** modules. Both modules are extremely small (39 lines combined) with minimal business logic, making them ideal candidates for combined implementation. Estimated migration time: **1.0 hour** (vs 2.0 hours separately).

### Module Overview

| Module | Purpose | Files | Lines | Complexity |
|--------|---------|-------|-------|------------|
| Credits | Resource credit management (stub) | 2 | 16 | MINIMAL |
| Hardware | Hardware abstraction layer | 1 | 23 | MINIMAL |
| **Combined** | | **3** | **39** | **MINIMAL** |

**Comparison:** Sprint 4's Metrics+Telemetry was 68 lines (1.5h). These modules are even smaller.

---

## Credits Module Analysis

### Location
`backend/app/modules/credits/`

### Files
```
credits/
├── __init__.py         # Module exports
├── schemas.py          # Pydantic models
├── service.py          # Business logic (16 lines)
└── router.py           # API endpoints (18 lines)
```

### Current Architecture

#### service.py (16 lines)
```python
from datetime import datetime, timezone
from .schemas import CreditsHealth, CreditsInfo

MODULE_NAME = "brain.credits"
MODULE_VERSION = "1.0.0"

async def get_health() -> CreditsHealth:
    return CreditsHealth(status="ok", timestamp=datetime.now(timezone.utc))

async def get_info() -> CreditsInfo:
    return CreditsInfo(
        name=MODULE_NAME,
        version=MODULE_VERSION,
        config={},
    )
```

**Analysis:**
- **Type:** Functional module (no classes)
- **Async:** Already async-ready
- **Storage:** No state (stub implementation)
- **Dependencies:** None
- **Pattern:** Simple health/info endpoints

#### router.py (18 lines)
```python
from fastapi import APIRouter, Depends
from app.core.security import Principal, get_current_principal
from .service import get_health, get_info
from .schemas import CreditsHealth, CreditsInfo

router = APIRouter(
    prefix="/api/credits",
    tags=["credits"],
)

@router.get("/health", response_model=CreditsHealth)
async def credits_health(principal: Principal = Depends(get_current_principal)):
    return await get_health()

@router.get("/info", response_model=CreditsInfo)
async def credits_info(principal: Principal = Depends(get_current_principal)):
    return await get_info()
```

**Analysis:**
- **Endpoints:** 2 (GET /health, GET /info)
- **Security:** Uses Principal authentication
- **Async:** Already async
- **No business logic** - just stub responses

### Event Opportunities

Despite minimal functionality, we can track:

1. **Module Health Checks** (Optional)
   - Track health endpoint calls
   - Monitor module availability

2. **Module Info Queries** (Optional)
   - Track info endpoint usage
   - Log configuration queries

**Recommendation:** Since this is a stub module with no real operations, events should be **OPTIONAL** or limited to basic telemetry.

---

## Hardware Module Analysis

### Location
`backend/app/modules/hardware/`

### Files
```
hardware/
├── __init__.py         # Module exports
├── schemas.py          # Pydantic models
└── router.py           # API endpoints (23 lines, no service)
```

### Current Architecture

#### router.py (23 lines)
```python
"""Hardware HAL REST API."""
from fastapi import APIRouter
from app.modules.hardware.schemas import RobotHardwareState, MovementCommand

router = APIRouter(prefix="/api/hardware", tags=["Hardware"])

@router.get("/info")
def get_hardware_info():
    return {
        "name": "Hardware Abstraction Layer",
        "version": "1.0.0",
        "supported_platforms": ["unitree_go1", "unitree_go2", "unitree_b2"],
        "features": ["Motor control", "IMU reading", "Battery monitoring"]
    }

@router.post("/robots/{robot_id}/command")
async def send_movement_command(robot_id: str, command: MovementCommand):
    return {"robot_id": robot_id, "status": "command_sent", "command": command}

@router.get("/robots/{robot_id}/state")
async def get_robot_state(robot_id: str):
    return {"robot_id": robot_id, "status": "mock_state"}
```

**Analysis:**
- **Type:** Functional module (no service layer yet)
- **Endpoints:** 3 (GET /info, POST /command, GET /state)
- **State:** Mock implementation (no real hardware)
- **Async:** Mixed (info is sync, others async)
- **Dependencies:** None

### Event Opportunities

Hardware module has more actionable events:

1. **hardware.command_sent**
   - When: POST /robots/{id}/command
   - Payload: robot_id, command type, parameters
   - Purpose: Track movement commands

2. **hardware.state_queried** (Optional)
   - When: GET /robots/{id}/state
   - Payload: robot_id
   - Purpose: Monitor state queries

3. **hardware.info_queried** (Optional)
   - When: GET /info
   - Purpose: Track module info requests

**Recommendation:** Focus on `hardware.command_sent` as primary event. State/info queries are optional.

---

## EventStream Integration Strategy

### Pattern Selection

Both modules are **functional** (no classes), so we'll use the **Module-Level EventStream Pattern**:

```python
# Module-level state
_event_stream: Optional["EventStream"] = None

def set_event_stream(stream: "EventStream") -> None:
    """Initialize EventStream for this module"""
    global _event_stream
    _event_stream = stream

async def _emit_event_safe(event_type: str, payload: dict) -> None:
    """Emit event with error handling (non-blocking)"""
    global _event_stream
    if _event_stream is None or Event is None:
        logger.debug("[ModuleName] EventStream not available, skipping event")
        return

    try:
        event = Event(type=event_type, source="module_service",
                     target=None, payload=payload)
        await _event_stream.publish(event)
    except Exception as e:
        logger.error("Event publishing failed: %s", e, exc_info=True)
```

This is the same pattern used in Sprint 4 for Metrics and Telemetry.

---

## Proposed Event Types

### Credits Module Events

Given the stub nature, we'll implement **minimal optional events**:

#### 1. `credits.health_checked` (Optional)
**Purpose:** Track module health checks
**Frequency:** Per health endpoint call
**Payload:**
```json
{
  "status": "ok",
  "checked_at": 1703001234.56
}
```

**Priority:** LOW (optional telemetry)

---

### Hardware Module Events

#### 1. `hardware.command_sent`
**Purpose:** Track robot movement commands
**Frequency:** Per POST /robots/{id}/command
**Payload:**
```json
{
  "robot_id": "robot_001",
  "command_type": "move",
  "command": {
    "linear": {"x": 1.0, "y": 0.0, "z": 0.0},
    "angular": {"x": 0.0, "y": 0.0, "z": 0.5}
  },
  "sent_at": 1703001234.56
}
```

**Priority:** HIGH (important operation tracking)

#### 2. `hardware.state_queried` (Optional)
**Purpose:** Monitor state queries
**Frequency:** Per GET /robots/{id}/state
**Payload:**
```json
{
  "robot_id": "robot_001",
  "queried_at": 1703001234.56
}
```

**Priority:** MEDIUM (useful telemetry)

#### 3. `hardware.info_queried` (Optional)
**Purpose:** Track module info requests
**Frequency:** Per GET /info
**Payload:**
```json
{
  "version": "1.0.0",
  "queried_at": 1703001234.56
}
```

**Priority:** LOW (optional telemetry)

---

## Event Count Summary

| Module | Total Events | High Priority | Optional |
|--------|--------------|---------------|----------|
| Credits | 1 | 0 | 1 |
| Hardware | 3 | 1 | 2 |
| **Total** | **4** | **1** | **3** |

**Recommendation:** Implement **2 core events** (hardware.command_sent + 1 optional), skip low-priority telemetry for stub modules.

---

## Migration Complexity Assessment

### Credits Module

| Aspect | Complexity | Notes |
|--------|------------|-------|
| Code Size | MINIMAL | 16 lines |
| Async Conversion | NONE | Already async |
| Event Integration | LOW | Module-level pattern |
| Event Types | MINIMAL | 0-1 events |
| Testing | LOW | Simple mock tests |
| **Overall** | **MINIMAL** | **~20 min** |

### Hardware Module

| Aspect | Complexity | Notes |
|--------|------------|-------|
| Code Size | MINIMAL | 23 lines |
| Async Conversion | MINIMAL | 1 endpoint to convert |
| Event Integration | LOW | Module-level pattern |
| Event Types | MEDIUM | 1-3 events |
| Testing | MEDIUM | Mock command/state |
| **Overall** | **LOW** | **~40 min** |

### Combined Estimate

| Phase | Credits | Hardware | Combined |
|-------|---------|----------|----------|
| 0 - Analysis | - | - | ✅ Done |
| 1 - Event Design | 5 min | 10 min | 15 min |
| 2 - Implementation | 10 min | 20 min | 30 min |
| 3 - Consumers | - | - | Skipped |
| 4 - Testing | 5 min | 10 min | 15 min |
| 5 - Documentation | 5 min | 5 min | 10 min |
| **Total** | **25 min** | **45 min** | **1.0 hour** |

**Efficiency Gain:** 0.2 hours saved vs separate implementation (1.2h → 1.0h)

---

## Implementation Approach

### Combined Strategy

**Phase 1:** Create single EVENTS.md for both modules
**Phase 2:** Implement both modules in parallel
- Credits: Add module-level EventStream + 0-1 events
- Hardware: Add module-level EventStream + 1-3 events
**Phase 4:** Single test file with sections for each module
**Phase 5:** Single migration summary document

### Integration Points

#### Credits Module
**File:** `service.py`
```python
# Add at top
from typing import Optional
import time

# Module-level EventStream
_event_stream: Optional["EventStream"] = None

def set_event_stream(stream: "EventStream") -> None:
    global _event_stream
    _event_stream = stream

async def _emit_event_safe(event_type: str, payload: dict) -> None:
    # ... safe emit pattern

# Optional: Add to get_health()
async def get_health() -> CreditsHealth:
    result = CreditsHealth(status="ok", timestamp=datetime.now(timezone.utc))

    # EVENT: credits.health_checked (optional)
    await _emit_event_safe("credits.health_checked", {
        "status": result.status,
        "checked_at": result.timestamp.timestamp(),
    })

    return result
```

**Changes:** +30 lines estimated

#### Hardware Module
**File:** `router.py`
```python
# Add at top
from typing import Optional
import time

# Module-level EventStream
_event_stream: Optional["EventStream"] = None

def set_event_stream(stream: "EventStream") -> None:
    global _event_stream
    _event_stream = stream

async def _emit_event_safe(event_type: str, payload: dict) -> None:
    # ... safe emit pattern

# Convert to async
async def get_hardware_info():
    # ... existing code

# Add event to send_movement_command
@router.post("/robots/{robot_id}/command")
async def send_movement_command(robot_id: str, command: MovementCommand):
    result = {"robot_id": robot_id, "status": "command_sent", "command": command}

    # EVENT: hardware.command_sent
    await _emit_event_safe("hardware.command_sent", {
        "robot_id": robot_id,
        "command_type": command.type if hasattr(command, 'type') else "movement",
        "command": command.model_dump(),
        "sent_at": time.time(),
    })

    return result

# Optional: Add event to get_robot_state
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

**Changes:** +40 lines estimated

---

## Testing Strategy

### Test Structure

Single test file: `backend/tests/test_credits_hardware_events.py`

**Sections:**
1. Fixtures (MockEventStream, setup functions)
2. Credits Module Tests (1-2 tests)
3. Hardware Module Tests (2-3 tests)
4. Charter Compliance Tests (2 tests)

**Total Tests:** ~6-8 tests

### Mock Components

```python
class MockEventStream:
    def __init__(self):
        self.events = []

    async def publish(self, event):
        self.events.append(event)

    def get_events_by_type(self, event_type):
        return [e for e in self.events if e.type == event_type]

class MockEvent:
    def __init__(self, type: str, source: str, target, payload: dict):
        self.id = str(uuid.uuid4())
        self.type = type
        self.source = source
        self.target = target
        self.timestamp = time.time()
        self.payload = payload
        self.meta = {}
```

### Test Cases

#### Credits Tests (1-2)
1. `test_credits_health_checked` (if implemented)
   - Call get_health()
   - Verify credits.health_checked event

2. `test_credits_charter_compliance`
   - Verify Charter v1.0 compliance

#### Hardware Tests (2-3)
1. `test_hardware_command_sent`
   - Call send_movement_command()
   - Verify hardware.command_sent event with command data

2. `test_hardware_state_queried` (if implemented)
   - Call get_robot_state()
   - Verify hardware.state_queried event

3. `test_hardware_charter_compliance`
   - Verify Charter v1.0 compliance

---

## Dependencies & Imports

### Required Imports (Both Modules)

```python
from typing import Optional
import time
import logging

# EventStream (optional)
try:
    from backend.app.core.event_stream import EventStream, Event
except ImportError:
    EventStream = None
    Event = None
```

### No Additional Packages

Both modules use standard libraries and existing dependencies.

---

## Risks & Mitigations

### Risk 1: Stub Modules
**Risk:** Credits is a stub with no real logic - events may be unnecessary
**Mitigation:** Make Credits events OPTIONAL, focus on Hardware

### Risk 2: No Service Layer in Hardware
**Risk:** Hardware has no service.py, logic is in router.py
**Mitigation:** Add EventStream directly to router.py (valid pattern)

### Risk 3: Mock Data
**Risk:** Both modules return mock data, events may not reflect real operations
**Mitigation:** Document as "future-ready" events, implement patterns for when real logic is added

---

## Success Criteria

### Phase 0 (Analysis)
- ✅ Module structure documented
- ✅ Event opportunities identified
- ✅ Integration strategy defined
- ✅ Time estimate calculated

### Phase 1 (Event Design)
- [ ] EVENTS.md created with 2-4 event types
- [ ] Event schemas documented
- [ ] Charter v1.0 compliance verified

### Phase 2 (Implementation)
- [ ] Credits: Module-level EventStream added (~30 lines)
- [ ] Hardware: Module-level EventStream added (~40 lines)
- [ ] Non-blocking event publishing implemented
- [ ] Graceful degradation verified

### Phase 4 (Testing)
- [ ] 6-8 tests written and passing
- [ ] Mock infrastructure validated
- [ ] Charter compliance automated

### Phase 5 (Documentation)
- [ ] Migration summary created
- [ ] Code changes documented
- [ ] Lessons learned captured
- [ ] Git commit and push

---

## Next Steps

1. **Phase 1:** Create combined EVENTS.md
2. **Phase 2:** Implement EventStream integration in both modules
3. **Phase 4:** Write comprehensive test suite
4. **Phase 5:** Document and commit

**Estimated Total Time:** 1.0 hour

---

## Notes

- **Efficiency Strategy:** Combining two minimal modules saves ~0.2 hours overhead
- **Pattern Consistency:** Using module-level EventStream pattern from Sprint 4
- **Event Philosophy:** Minimal events for stub modules, focus on actionable events
- **Future-Ready:** Events establish patterns for when real business logic is added

---

**Analysis Completed:** December 29, 2025
**Status:** ✅ Ready for Phase 1 (Event Design)
