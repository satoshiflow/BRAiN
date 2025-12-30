# Sprint 3 - Threats Module: Phase 0 Analysis

**Module:** `backend.app.modules.threats/`
**Analysis Date:** 2024-12-28
**Estimated Migration Effort:** 3-4 hours

---

## 1. Module Structure

### File Inventory

| File | Lines | Purpose |
|------|-------|---------|
| `service.py` | 173 | Redis CRUD operations, stats tracking |
| `router.py` | 85 | FastAPI REST endpoints (6 routes) |
| `models.py` | 57 | Pydantic models (5 schemas) |

**Total Size:** ~315 lines
**Complexity:** MEDIUM (Redis CRUD, simpler than policy module)

---

## 2. Core Functionality Analysis

### 2.1 Data Models (models.py)

**Enums:**

```python
class ThreatSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ThreatStatus(str, Enum):
    OPEN = "OPEN"              # Initial state
    INVESTIGATING = "INVESTIGATING"  # Being analyzed
    MITIGATED = "MITIGATED"    # Resolved/fixed
    IGNORED = "IGNORED"        # Deemed non-threat
    ESCALATED = "ESCALATED"    # Severity increased
```

**Core Models:**

```python
class Threat(BaseModel):
    id: str                    # UUID
    type: str                  # Threat type (e.g., "sql_injection")
    source: str                # Origin (e.g., "api_gateway")
    severity: ThreatSeverity   # Severity level
    status: ThreatStatus       # Current status
    description: Optional[str] # Details
    metadata: Dict[str, Any]   # Additional context
    created_at: float          # Unix timestamp
    last_seen_at: float        # Last activity timestamp
```

**Lifecycle Flow:**
```
CREATE → OPEN → INVESTIGATING → MITIGATED/IGNORED
                          ↓
                      ESCALATED (if severity increases)
```

---

### 2.2 Service Functions (service.py)

**Redis Key Layout:**
```
brain:threats:threat:{id}   → JSON string (individual threat)
brain:threats:index         → SET (all threat IDs)
brain:threats:stats         → JSON string (aggregated stats)
```

**Key Functions:**

| Function | Lines | Purpose | Event Trigger Point |
|----------|-------|---------|-------------------|
| `create_threat()` | 28-46 | Create new threat | ✅ threat.detected |
| `get_threat()` | 49-56 | Fetch by ID | (read-only) |
| `list_threats()` | 58-76 | List with filters | (read-only) |
| `update_threat_status()` | 78-92 | Change status | ✅ threat.status_changed<br>✅ threat.escalated<br>✅ threat.mitigated |
| `get_stats()` | 94-125 | Get statistics | (read-only) |

**Helper Functions:**
- `_update_stats_on_create()` - Update aggregated stats after creation
- `_update_stats_on_status_change()` - Update stats after status change

---

### 2.3 API Routes (router.py)

**6 Endpoints:**

| Method | Path | Handler | Event Impact |
|--------|------|---------|-------------|
| GET | `/api/threats/health` | `threats_health()` | None |
| GET | `/api/threats` | `list_threats_endpoint()` | None (read-only) |
| POST | `/api/threats` | `create_threat_endpoint()` | ✅ Triggers threat.detected |
| GET | `/api/threats/{id}` | `get_threat_endpoint()` | None (read-only) |
| POST | `/api/threats/{id}/status` | `update_threat_status_endpoint()` | ✅ Triggers status events |
| GET | `/api/threats/stats/overview` | `get_stats_endpoint()` | None (read-only) |

**Key Observation:**
- Router delegates to service functions
- EventStream integration should happen in **service.py**, not router.py
- Router remains unchanged (events emitted from service layer)

---

## 3. Event Design Summary

### 3.1 Event Types (4 Total)

| Event Type | Source Function | Trigger Condition | Priority |
|------------|----------------|-------------------|----------|
| `threat.detected` | `create_threat()` | New threat created | CRITICAL |
| `threat.status_changed` | `update_threat_status()` | Any status change | HIGH |
| `threat.escalated` | `update_threat_status()` | status → ESCALATED | CRITICAL |
| `threat.mitigated` | `update_threat_status()` | status → MITIGATED | HIGH |

**Note:** `threat.escalated` could also be triggered by severity increase (requires new function)

---

### 3.2 Event Trigger Points (Code Locations)

#### Event 1: `threat.detected`
**Location:** `service.py:46` (end of `create_threat()`)
**Trigger:** When new threat is created

```python
# Line 28-46
async def create_threat(payload: ThreatCreate) -> Threat:
    redis: Any = await get_redis()
    threat_id = str(uuid.uuid4())
    now = time.time()
    threat = Threat(
        id=threat_id,
        type=payload.type,
        source=payload.source,
        severity=payload.severity,
        status=ThreatStatus.OPEN,
        description=payload.description,
        metadata=payload.metadata,
        created_at=now,
        last_seen_at=now,
    )
    await redis.set(_threat_key(threat_id), threat.model_dump_json())
    await redis.sadd(THREAT_INDEX_KEY, threat_id)
    await _update_stats_on_create(redis, threat)

    # 🔥 EVENT TRIGGER POINT
    await _emit_event_safe(
        event_type="threat.detected",
        threat=threat,
    )

    return threat
```

**Payload Fields:**
- `threat_id`: UUID
- `type`: Threat type
- `source`: Origin system
- `severity`: LOW/MEDIUM/HIGH/CRITICAL
- `status`: OPEN (always for new threats)
- `description`: Optional details
- `metadata`: Additional context
- `detected_at`: timestamp

---

#### Event 2: `threat.status_changed`
**Location:** `service.py:92` (end of `update_threat_status()`)
**Trigger:** When threat status is updated

```python
# Line 78-92
async def update_threat_status(
    threat_id: str,
    status: ThreatStatus,
) -> Optional[Threat]:
    redis: Any = await get_redis()
    threat = await get_threat(threat_id)
    if not threat:
        return None
    old_status = threat.status
    threat.status = status
    threat.last_seen_at = time.time()
    await redis.set(_threat_key(threat_id), threat.model_dump_json())
    await _update_stats_on_status_change(redis, threat, old_status)

    # 🔥 EVENT TRIGGER POINT (always emit)
    await _emit_event_safe(
        event_type="threat.status_changed",
        threat=threat,
        old_status=old_status,
        new_status=status,
    )

    # 🔥 CONDITIONAL EVENTS (based on new status)
    if status == ThreatStatus.ESCALATED:
        await _emit_event_safe(
            event_type="threat.escalated",
            threat=threat,
            old_status=old_status,
        )
    elif status == ThreatStatus.MITIGATED:
        await _emit_event_safe(
            event_type="threat.mitigated",
            threat=threat,
            old_status=old_status,
        )

    return threat
```

**Payload Fields:**
- `threat_id`: UUID
- `type`: Threat type
- `severity`: Current severity
- `old_status`: Previous status
- `new_status`: New status
- `changed_at`: timestamp

---

#### Event 3: `threat.escalated`
**Location:** `service.py:92` (inside `update_threat_status()`)
**Trigger:** When status changes to ESCALATED

**Payload Fields:**
- `threat_id`: UUID
- `type`: Threat type
- `severity`: Current severity
- `old_status`: Previous status
- `escalated_at`: timestamp

---

#### Event 4: `threat.mitigated`
**Location:** `service.py:92` (inside `update_threat_status()`)
**Trigger:** When status changes to MITIGATED

**Payload Fields:**
- `threat_id`: UUID
- `type`: Threat type
- `severity`: Severity level (for context)
- `old_status`: Previous status
- `mitigated_at`: timestamp
- `duration_seconds`: Optional (created_at → mitigated_at)

---

## 4. EventStream Integration Strategy

### 4.1 Service-Level Integration

**Current Architecture:**
- Service functions are **standalone async functions** (not class methods)
- No singleton pattern (unlike Policy Engine)
- Pure functional approach

**Integration Options:**

**Option A: Wrapper Function with EventStream Injection**
```python
# NEW: Wrapper function that accepts EventStream
async def create_threat_with_events(
    payload: ThreatCreate,
    event_stream: Optional["EventStream"] = None
) -> Threat:
    threat = await create_threat(payload)

    if event_stream:
        await _emit_event_safe(event_stream, "threat.detected", threat)

    return threat
```

**Option B: Module-Level EventStream Variable** (RECOMMENDED)
```python
# Module-level EventStream (injected at startup)
_event_stream: Optional["EventStream"] = None

def set_event_stream(event_stream: Optional["EventStream"]):
    """Set EventStream for threats module (called at startup)"""
    global _event_stream
    _event_stream = event_stream

# In service functions
async def create_threat(payload: ThreatCreate) -> Threat:
    # ... create logic ...

    await _emit_event_safe(
        event_type="threat.detected",
        threat=threat,
    )
    return threat
```

**Chosen Approach:** Option B (module-level variable)
**Rationale:**
- Minimal code changes (no new wrapper functions)
- Consistent with async function architecture
- EventStream injected once at startup (main.py)
- Clean separation of concerns

---

### 4.2 Non-Blocking Event Helper

**Add to service.py:**
```python
async def _emit_event_safe(
    event_type: str,
    threat: Threat,
    old_status: Optional[ThreatStatus] = None,
    new_status: Optional[ThreatStatus] = None,
) -> None:
    """
    Emit threat event with error handling (non-blocking).

    Charter v1.0 Compliance:
    - Event publishing MUST NOT block business logic
    - Failures are logged but NOT raised
    """
    global _event_stream

    if _event_stream is None or Event is None:
        logger.debug("[ThreatService] EventStream not available, skipping event")
        return

    try:
        # Build payload
        payload = {
            "threat_id": threat.id,
            "type": threat.type,
            "source": threat.source,
            "severity": threat.severity.value,
            "status": threat.status.value,
        }

        if threat.description:
            payload["description"] = threat.description

        if old_status:
            payload["old_status"] = old_status.value
        if new_status:
            payload["new_status"] = new_status.value

        # Add timestamp
        payload[f"{event_type.split('.')[1]}_at"] = time.time()

        # Create and publish event
        event = Event(
            type=event_type,
            source="threat_service",
            target=None,
            payload=payload,
        )

        await _event_stream.publish(event)

        logger.debug(
            "[ThreatService] Event published: %s (threat_id=%s)",
            event_type,
            threat.id,
        )

    except Exception as e:
        logger.error(
            "[ThreatService] Event publishing failed: %s (event_type=%s)",
            e,
            event_type,
            exc_info=True,
        )
        # DO NOT raise - business logic must continue
```

---

### 4.3 EventStream Import

**Add to top of service.py:**
```python
# EventStream integration (Sprint 3)
try:
    from backend.mission_control_core.core import EventStream, Event
except ImportError:
    EventStream = None
    Event = None
    import warnings
    warnings.warn(
        "[ThreatService] EventStream not available (mission_control_core not installed)",
        RuntimeWarning
    )

# Module-level EventStream (set at startup)
_event_stream: Optional["EventStream"] = None

def set_event_stream(event_stream: Optional["EventStream"]):
    """Set EventStream for threats module (called at startup)"""
    global _event_stream
    _event_stream = event_stream
```

---

## 5. Testing Strategy

### 5.1 Test Coverage Plan

**8 Tests Required:**

1. `test_threat_detected_event` - New threat creation triggers event
2. `test_threat_status_changed_event` - Status update triggers event
3. `test_threat_escalated_event` - ESCALATED status triggers specific event
4. `test_threat_mitigated_event` - MITIGATED status triggers specific event
5. `test_event_lifecycle_full` - Full lifecycle: detected → investigating → mitigated
6. `test_event_lifecycle_escalation` - Lifecycle: detected → escalated → mitigated
7. `test_threats_work_without_eventstream` - Graceful degradation
8. `test_event_envelope_charter_compliance` - Charter v1.0 structure

**Test File:** `backend/tests/test_threats_events.py`

---

### 5.2 Mock Strategy

**Fixtures:**
```python
@pytest.fixture
def mock_event_stream():
    """Mock EventStream that captures published events"""
    class MockEventStream:
        def __init__(self):
            self.events = []

        async def publish(self, event):
            self.events.append(event)

    return MockEventStream()

@pytest.fixture
async def setup_event_stream(mock_event_stream):
    """Set module-level EventStream"""
    from backend.app.modules.threats import service
    service.set_event_stream(mock_event_stream)
    yield
    service.set_event_stream(None)  # Cleanup

@pytest.fixture
def sample_threat_payload():
    """Sample threat creation payload"""
    return ThreatCreate(
        type="sql_injection",
        source="api_gateway",
        severity=ThreatSeverity.HIGH,
        description="Detected SQL injection attempt",
        metadata={"ip": "192.168.1.100"},
    )
```

---

## 6. Implementation Checklist

### Phase 2: Producer Implementation
- [ ] Add EventStream import with graceful fallback
- [ ] Add module-level `_event_stream` variable
- [ ] Implement `set_event_stream()` function
- [ ] Implement `_emit_event_safe()` helper
- [ ] Add event publishing to `create_threat()` (threat.detected)
- [ ] Add event publishing to `update_threat_status()` (threat.status_changed)
- [ ] Add conditional event for ESCALATED status
- [ ] Add conditional event for MITIGATED status

### Phase 4: Testing
- [ ] Create `test_threats_events.py`
- [ ] Implement all 8 tests
- [ ] Verify all tests pass
- [ ] Verify payload structure matches Charter v1.0

### Phase 5: Documentation
- [ ] Create `backend/app/modules/threats/EVENTS.md`
- [ ] Update `backend/app/modules/threats/README.md` (if exists)
- [ ] Create Sprint 3 threats migration summary
- [ ] Document any breaking changes (none expected)

---

## 7. Risk Assessment

### Low Risk
- **Simple CRUD logic** - No complex rule evaluation
- **Functional architecture** - No class state to manage
- **Proven pattern** - Module-level variable used in other modules

### Medium Risk
- **Module-level variable** - Need to ensure thread safety (but Python async is single-threaded)
- **Redis operations** - Event publishing must not block Redis I/O

### Mitigation
- Use non-blocking `_emit_event_safe()` pattern
- Comprehensive testing of all code paths
- Test graceful degradation

---

## 8. Estimated Effort Breakdown

| Phase | Task | Estimated Time |
|-------|------|---------------|
| Phase 0 | Analysis | ✅ 30 min (DONE) |
| Phase 1 | Event design + EVENTS.md | 30 min |
| Phase 2 | Producer implementation | 1.5 hours |
| Phase 4 | Testing (8 tests) | 1 hour |
| Phase 5 | Documentation | 30 min |
| Phase 6 | Commit & push | 15 min |

**Total:** 4 hours

---

## 9. Comparison with Policy Module

| Aspect | Policy Module | Threats Module |
|--------|--------------|----------------|
| **Size** | 561 lines (service only) | 173 lines (service only) |
| **Complexity** | HIGH (rule evaluation) | MEDIUM (CRUD only) |
| **Event Count** | 7 events | 4 events |
| **Architecture** | Class-based (singleton) | Functional |
| **Test Count** | 11 tests | 8 tests |
| **Effort** | 5.5 hours | 4 hours (estimated) |

**Simpler than policy module:** ✅
**Faster implementation expected:** ✅

---

## 10. Next Steps

1. **Phase 1:** Create detailed event specifications in EVENTS.md
2. **Phase 2:** Implement EventStream integration in service.py
3. **Phase 4:** Create comprehensive test suite
4. **Phase 5:** Document changes

**Ready to proceed to Phase 1: Event Design** ✅
