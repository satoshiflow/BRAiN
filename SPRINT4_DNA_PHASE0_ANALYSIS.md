# Sprint 4 - DNA Module: Phase 0 Analysis

**Module:** `backend.app.modules.dna`
**Analysis Date:** 2024-12-28
**Sprint:** Sprint 4 - Data & Analytics Modules (Module 1/3)
**Analyst:** Claude Code
**Estimated Effort:** 2.5 hours

---

## Module Overview

The DNA (Genetic Optimization) module manages versioned snapshots of agent configurations, enabling genetic algorithm-based evolution and optimization of agent behavior.

**Purpose:**
- Version control for agent DNA/configuration
- Genetic mutation tracking
- Performance score (KARMA) integration
- Evolution history management

**Key Concepts:**
- **DNA Snapshot** - Versioned capture of agent configuration
- **Mutation** - Genetic algorithm-based DNA modification
- **KARMA Score** - Performance metric for fitness evaluation
- **Evolution** - Progressive improvement through mutations

---

## File Structure

```
backend/app/modules/dna/
├── __init__.py
├── router.py                   # API endpoints (45 lines)
├── schemas.py                  # Data models (38 lines)
└── core/
    ├── service.py              # Business logic (89 lines)
    └── store.py                # Storage abstraction (if exists)
```

**Total Lines:** ~172 lines
**Complexity:** LOW-MEDIUM

---

## Data Models

### AgentDNASnapshot
```python
class AgentDNASnapshot(BaseModel):
    id: int                          # Unique snapshot ID
    agent_id: str                    # Agent identifier
    version: int                     # Snapshot version (incremental)
    dna: Dict[str, Any]             # Agent configuration/DNA
    traits: Dict[str, Any]          # Agent traits/characteristics
    karma_score: Optional[float]     # Performance score (from KARMA module)
    created_at: datetime             # Snapshot creation timestamp
    meta: DNAMetadata               # Metadata (reason, source, parent)
```

### DNAMetadata
```python
class DNAMetadata(BaseModel):
    reason: Optional[str]            # Why snapshot was created
    source: str                      # "manual" | "system" | "mutation"
    parent_snapshot_id: Optional[int] # Previous snapshot ID (for lineage)
```

---

## Service Architecture

**Pattern:** Class-based with in-memory storage

```python
class DNAService:
    def __init__(self) -> None:
        self._store: Dict[str, List[AgentDNASnapshot]] = {}
        self._id_counter: int = 1
```

**Storage:**
- In-memory dictionary: `agent_id -> List[AgentDNASnapshot]`
- Snapshots ordered by version
- Auto-incrementing ID counter

**Singleton:** Service instantiated once in router (line 14)

---

## Event Trigger Points

### 1. Snapshot Created (`create_snapshot`)

**Location:** `service.py:24-46`
**Trigger:** New DNA snapshot created

```python
def create_snapshot(self, payload: CreateDNASnapshotRequest) -> AgentDNASnapshot:
    snapshots = self._store.setdefault(payload.agent_id, [])
    version = len(snapshots) + 1

    meta = DNAMetadata(
        reason=payload.reason,
        source="manual",  # Or "system"
        parent_snapshot_id=snapshots[-1].id if snapshots else None,
    )

    snapshot = AgentDNASnapshot(...)
    snapshots.append(snapshot)

    # 🔔 EVENT: dna.snapshot_created
    return snapshot
```

**Frequency:** Medium
**Priority:** HIGH
**Payload:**
- snapshot_id
- agent_id
- version
- source (manual/system)
- parent_snapshot_id (if exists)
- dna_size (number of config keys)
- traits_count

---

### 2. Mutation Applied (`mutate`)

**Location:** `service.py:48-75`
**Trigger:** DNA mutation applied (genetic evolution)

```python
def mutate(self, agent_id: str, req: MutateDNARequest) -> AgentDNASnapshot:
    latest = snapshots[-1]
    new_dna = {**latest.dna, **req.mutation}
    new_traits = {**latest.traits, **req.traits_delta}

    meta = DNAMetadata(
        reason=req.reason,
        source="mutation",
        parent_snapshot_id=latest.id,
    )

    snapshot = AgentDNASnapshot(...)
    snapshots.append(snapshot)

    # 🔔 EVENT: dna.mutation_applied
    return snapshot
```

**Frequency:** Medium (during optimization runs)
**Priority:** HIGH
**Payload:**
- snapshot_id
- agent_id
- version
- parent_snapshot_id
- mutation_keys (which DNA keys changed)
- traits_delta (trait changes)
- reason

---

### 3. KARMA Updated (`update_karma`)

**Location:** `service.py:81-89`
**Trigger:** KARMA score updated for latest snapshot

```python
def update_karma(self, agent_id: str, score: float) -> None:
    """Called by KARMA service."""
    latest = snapshots[-1]
    latest.karma_score = score

    # 🔔 EVENT: dna.karma_updated
```

**Frequency:** Medium (after each KARMA evaluation)
**Priority:** MEDIUM
**Payload:**
- snapshot_id
- agent_id
- version
- karma_score
- previous_score (if available)
- score_delta

---

## Proposed Event Types

### Event 1: `dna.snapshot_created`
**When:** New DNA snapshot created (manual or system)
**Priority:** HIGH
**Consumers:**
- Evolution Dashboard - Track snapshot creation timeline
- Analytics - Snapshot frequency metrics
- Audit Log - Configuration change tracking

**Payload Schema:**
```json
{
  "snapshot_id": 123,
  "agent_id": "coder_agent",
  "version": 5,
  "source": "manual",
  "parent_snapshot_id": 122,
  "dna_size": 42,
  "traits_count": 8,
  "created_at": 1703001234.567
}
```

---

### Event 2: `dna.mutation_applied`
**When:** DNA mutation applied (genetic algorithm evolution)
**Priority:** HIGH
**Consumers:**
- Evolution Dashboard - Mutation tracking
- Analytics - Mutation success rate
- KARMA Module - Trigger fitness evaluation

**Payload Schema:**
```json
{
  "snapshot_id": 124,
  "agent_id": "coder_agent",
  "version": 6,
  "parent_snapshot_id": 123,
  "mutation_keys": ["temperature", "max_tokens"],
  "traits_delta": {"creativity": 0.1},
  "reason": "Exploration phase - temperature increase",
  "created_at": 1703002345.678
}
```

---

### Event 3: `dna.karma_updated`
**When:** KARMA score updated for a snapshot
**Priority:** MEDIUM
**Consumers:**
- Evolution Dashboard - Fitness score visualization
- Analytics - Performance trend analysis
- Genetic Algorithm - Selection criteria

**Payload Schema:**
```json
{
  "snapshot_id": 124,
  "agent_id": "coder_agent",
  "version": 6,
  "karma_score": 0.87,
  "previous_score": 0.82,
  "score_delta": 0.05,
  "updated_at": 1703003456.789
}
```

---

## EventStream Integration Strategy

### Pattern: Constructor Injection

**Rationale:**
- DNA module uses class-based architecture
- Consistent with Policy and Immune modules (Sprint 3)
- Clean dependency injection
- Testable (can pass mock EventStream)

**Implementation:**
```python
class DNAService:
    def __init__(self, event_stream: Optional["EventStream"] = None) -> None:
        self._store: Dict[str, List[AgentDNASnapshot]] = {}
        self._id_counter: int = 1
        self.event_stream = event_stream  # EventStream integration
```

**Router Update:**
```python
# In startup event or module initialization
from backend.mission_control_core.core import get_event_stream

event_stream = get_event_stream()
dna_service = DNAService(event_stream=event_stream)
```

---

## Async Conversion Requirements

**Current State:** All methods are synchronous
**Target State:** Event-emitting methods must be async

**Methods to Convert:**
1. `create_snapshot()` → `async def create_snapshot()`
2. `mutate()` → `async def mutate()`
3. `update_karma()` → `async def update_karma()`

**Router Endpoints:**
- All 3 endpoints must be converted to `async def`

**Backward Compatibility:**
- No breaking changes (API signature remains same)
- Async is transparent to HTTP clients

---

## Dependencies

**Current:**
- pydantic - Data validation
- fastapi - API framework

**New (EventStream):**
- mission_control_core - EventStream (optional import)

**No external storage dependencies:**
- In-memory storage only
- No Redis, PostgreSQL, etc.

---

## Testing Strategy

### Test Coverage Plan

**Total Tests:** 7 tests

1. **test_dna_snapshot_created**
   - Create snapshot → verify event published
   - Check payload structure

2. **test_dna_mutation_applied**
   - Apply mutation → verify event published
   - Check mutation_keys and traits_delta

3. **test_dna_karma_updated**
   - Update karma → verify event published
   - Check score_delta calculation

4. **test_dna_snapshot_lifecycle**
   - Full lifecycle: create → mutate → update karma
   - Verify all 3 events emitted in order

5. **test_dna_multiple_mutations**
   - Create snapshot → mutate 3 times
   - Verify version incrementing and parent tracking

6. **test_dna_works_without_eventstream**
   - Service works normally without EventStream
   - Graceful degradation

7. **test_event_envelope_charter_compliance**
   - All events comply with Charter v1.0
   - Event envelope structure validation

**Mock Infrastructure:**
- MockEventStream (reuse from Sprint 3)
- MockEvent (Charter v1.0 compliant)
- Fixtures for service setup/cleanup

---

## Migration Complexity Assessment

### Complexity: LOW-MEDIUM

**Easy Aspects:**
- ✅ Small codebase (89 lines service)
- ✅ In-memory storage (no external dependencies)
- ✅ Clear event trigger points
- ✅ Class-based architecture (constructor injection)
- ✅ Simple data model

**Moderate Aspects:**
- ⚠️ Async conversion required (3 methods + 3 endpoints)
- ⚠️ KARMA score tracking (need previous_score)
- ⚠️ Mutation tracking (need to extract mutation_keys)

**No Complex Aspects** ✅

---

## Risk Assessment

### LOW RISK ✅

**Risks:**
1. **Async Conversion** - LOW
   - Straightforward conversion
   - No complex async operations

2. **Performance** - LOW
   - In-memory operations (fast)
   - Event publishing <1ms overhead

3. **Breaking Changes** - NONE
   - Async transparent to HTTP clients
   - EventStream optional dependency

**Mitigation:**
- Comprehensive testing (7 tests)
- Graceful degradation without EventStream
- Charter v1.0 compliance

---

## Effort Estimation

### Total: 2.5 hours

| Phase | Time | Tasks |
|-------|------|-------|
| Phase 0: Analysis | 0.5h | ✅ This document |
| Phase 1: Event Design | 0.5h | Create EVENTS.md |
| Phase 2: Implementation | 1.0h | Add EventStream + async conversion |
| Phase 4: Testing | 0.5h | Create test suite (7 tests) |
| Phase 5: Documentation | 0.25h | Migration summary + commit |

**Comparison to Sprint 3:**
- Policy: 5.5h (HIGH complexity)
- Threats: 4.0h (MEDIUM complexity)
- Immune: 2.0h (LOW complexity)
- **DNA: 2.5h (LOW-MEDIUM complexity)**

---

## Success Criteria

✅ **Implementation:**
- 3 event types implemented
- Async conversion complete
- Constructor injection pattern
- EventStream import with graceful fallback

✅ **Testing:**
- 7 comprehensive tests
- 100% event type coverage
- Charter v1.0 compliance
- All tests passing

✅ **Documentation:**
- EVENTS.md (500+ lines)
- Migration summary
- Git commit with detailed message

✅ **Quality:**
- Zero breaking changes
- Non-blocking event publishing
- Graceful degradation
- Performance overhead <1%

---

## Next Steps

1. ✅ **Phase 0 Complete** - This analysis document
2. ⏳ **Phase 1** - Create EVENTS.md with full event specifications
3. ⏳ **Phase 2** - Implement EventStream integration + async conversion
4. ⏳ **Phase 4** - Create comprehensive test suite
5. ⏳ **Phase 5** - Documentation and git commit

---

**Analysis Complete**
**Ready to proceed to Phase 1: Event Design**

---

**Document Version:** 1.0
**Last Updated:** 2024-12-28
**Status:** ✅ ANALYSIS COMPLETE
