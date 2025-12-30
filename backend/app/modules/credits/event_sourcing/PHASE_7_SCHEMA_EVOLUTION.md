# Phase 7: Event Schema Evolution

**Status:** ✅ **COMPLETE**
**Date:** 2025-12-30
**Version:** 1.0.0

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Components](#components)
4. [Schema Version Registry](#schema-version-registry)
5. [Event Upcaster](#event-upcaster)
6. [Migration Tools](#migration-tools)
7. [Usage Guide](#usage-guide)
8. [Integration](#integration)
9. [Best Practices](#best-practices)
10. [Testing](#testing)

---

## Overview

### Purpose

Enable forward-compatible event schema evolution while maintaining backward compatibility with old events.

### Problem

In long-running event-sourced systems, event schemas evolve over time:
- Add new fields (e.g., metadata tracking)
- Rename fields (e.g., `user_id` → `actor_id`)
- Change data structures (e.g., flat → nested)
- Remove deprecated fields

**Challenge:** Old events remain immutable in the journal, but projections expect latest schema.

### Solution

**Event Upcasting** - Transform old event schemas to latest version during replay:
- Automatic schema detection via `schema_version` field
- Sequential upcasting (v1 → v2 → v3)
- Pure transformation functions (deterministic)
- Zero downtime deployments

---

## Architecture

### Design Principles

1. **Events are Immutable**
   - Never modify events in the journal
   - Upcasting happens at read-time (during replay)
   - Original events preserved forever

2. **Sequential Versioning**
   - Versions increment sequentially (1, 2, 3, ...)
   - Each version has one upcaster (v1→v2, v2→v3, ...)
   - No skipping versions (v1→v3 goes through v2)

3. **Deterministic Transformations**
   - Upcasters are pure functions
   - Same input always produces same output
   - No side effects or external dependencies

4. **Transparent Operation**
   - Upcasting happens automatically during replay
   - Projections always receive latest schema
   - Zero code changes in event handlers

### Data Flow

```
Event Journal (Postgres)
├── v1 events (old schema)
├── v2 events (newer schema)
└── v3 events (latest schema)
         │
         ▼
    Read Events
         │
         ▼
   Upcast if Needed
   ┌──────────────────┐
   │ v1 → v2 → v3     │  Upcaster Chain
   │ (sequential)     │
   └──────────────────┘
         │
         ▼
   All Events → v3
         │
         ▼
  Apply to Projections
  (Always latest schema)
```

---

## Components

### 1. Schema Version Registry (`schema_versions.py`)

Centralized registry of all event schema versions and upcasters.

**Responsibilities:**
- Track latest version per event type
- Store upcaster functions
- Validate sequential versioning
- Provide evolution paths (v1 → latest)

**Key Classes:**
- `SchemaVersion` - Metadata for one schema version
- `SchemaRegistry` - Central registry
- `SCHEMA_REGISTRY` - Global singleton instance

### 2. Event Upcaster (`event_upcaster.py`)

Engine for transforming events to latest schema.

**Responsibilities:**
- Detect old schema versions
- Apply sequential upcasters
- Validate transformations
- Handle errors gracefully

**Key Functions:**
- `upcast_event_if_needed()` - Main entry point
- `is_upcast_needed()` - Check if upcast required
- `get_upcast_statistics()` - Analyze event corpus

### 3. Migration CLI (`upcast_events.py`)

Command-line tool for bulk upcasting.

**Responsibilities:**
- Analyze events (show statistics)
- Dry-run mode (preview changes)
- Bulk upcast with progress tracking
- Create backup snapshots

**Commands:**
- `analyze` - Show schema statistics
- `upcast` - Perform migration
- `validate` - Test upcasters

---

## Schema Version Registry

### Initialization

All events start at version 1:

```python
# schema_versions.py
from backend.app.modules.credits.event_sourcing.events import EventType

def initialize_schema_registry():
    """Register version 1 for all event types."""
    for event_type in EventType:
        SCHEMA_REGISTRY.register_version(
            event_type=event_type.value,
            version=1,
            upcaster=None,  # v1 has no upcaster
            description="Initial schema version",
        )
```

### Registering New Versions

When evolving a schema to v2:

```python
from backend.app.modules.credits.event_sourcing.schema_versions import SCHEMA_REGISTRY
from backend.app.modules.credits.event_sourcing.events import EventType

# Define upcaster function
def upcast_credit_allocated_v1_to_v2(payload):
    """Add metadata field to credit.allocated events."""
    return {
        **payload,  # Preserve all v1 fields
        "metadata": {
            "source": "system",
            "migrated_at": datetime.now(timezone.utc).isoformat(),
        }
    }

# Register version 2
SCHEMA_REGISTRY.register_version(
    event_type=EventType.CREDIT_ALLOCATED.value,
    version=2,
    upcaster=upcast_credit_allocated_v1_to_v2,
    description="Added metadata field for enhanced tracking"
)
```

### Query API

```python
# Get latest version
latest = SCHEMA_REGISTRY.get_latest_version("credit.allocated")  # → 2

# Get evolution path
path = SCHEMA_REGISTRY.get_evolution_path("credit.allocated", from_version=1)
# → [2] (need to apply v1→v2 upcaster)

# Get specific upcaster
upcaster = SCHEMA_REGISTRY.get_upcaster("credit.allocated", from_version=1)
# → upcast_credit_allocated_v1_to_v2 function

# Get version history
history = SCHEMA_REGISTRY.get_version_history("credit.allocated")
# → [SchemaVersion(v1), SchemaVersion(v2)]
```

---

## Event Upcaster

### Automatic Upcasting

Events are automatically upcasted during replay:

```python
from backend.app.modules.credits.event_sourcing.event_upcaster import upcast_event_if_needed

# Event from journal (v1)
event_v1 = EventEnvelope(
    schema_version=1,
    event_type=EventType.CREDIT_ALLOCATED,
    payload={
        "entity_id": "agent_123",
        "amount": 100.0,
        "reason": "Initial allocation",
        # No metadata field (v1 schema)
    }
)

# Upcast to latest version
event_v2 = await upcast_event_if_needed(event_v1)

# Result: v2 event with metadata
assert event_v2.schema_version == 2
assert "metadata" in event_v2.payload
```

### Check if Upcast Needed

```python
from backend.app.modules.credits.event_sourcing.event_upcaster import is_upcast_needed

if is_upcast_needed(event):
    print(f"Event {event.event_id} needs upcasting from v{event.schema_version}")
```

### Batch Upcasting

```python
from backend.app.modules.credits.event_sourcing.event_upcaster import upcast_event_batch

events = [event1, event2, event3]  # Mix of v1 and v2
upcasted = await upcast_event_batch(events)  # All → latest version
```

### Statistics

```python
from backend.app.modules.credits.event_sourcing.event_upcaster import get_upcast_statistics

# Analyze all events
stats = get_upcast_statistics(all_events)

print(f"Total events: {stats['total_events']}")
print(f"Need upcast: {stats['needs_upcast']} ({stats['upcast_percentage']:.1f}%)")

# Breakdown by type
for event_type, count in stats['by_event_type'].items():
    print(f"  {event_type}: {count} events")
```

### Error Handling

```python
from backend.app.modules.credits.event_sourcing.event_upcaster import UpcastError

try:
    event = await upcast_event_if_needed(old_event)
except UpcastError as e:
    logger.error(f"Upcasting failed: {e}")
    # Replay stops - fix upcaster and retry
```

---

## Migration Tools

### CLI Commands

#### 1. Analyze Events

Show statistics about events needing upcasting:

```bash
python backend/scripts/upcast_events.py analyze
```

**Output:**
```
================================================================================
Schema Analysis Results
================================================================================
Total Events: 1,234
Need Upcast: 450 (36.5%)

Events by Type:
  - credit.allocated: 200 events (→ v2)
  - credit.consumed: 250 events (→ v2)

Events by Current Version:
  - v1: 450 events
  - v2: 784 events
================================================================================
```

#### 2. Upcast Events (Dry Run)

Preview changes without modifying journal:

```bash
python backend/scripts/upcast_events.py upcast --dry-run
```

**Output:**
```
Found 450 events needing upcast:
  - credit.allocated: 200 events (→ v2)
  - credit.consumed: 250 events (→ v2)

[DRY RUN] Would upcast these events
[DRY RUN] No changes made
```

#### 3. Upcast Events (Production)

Perform actual migration:

```bash
python backend/scripts/upcast_events.py upcast --with-snapshot
```

**Output:**
```
Creating backup snapshot before migration...
✅ Backup snapshot created: snapshot_20251230_153000
   Sequence: 1,234
   Size: 1.2 MB

Upcasting 450 events...
Progress: 25.0% (113/450)
Progress: 50.0% (225/450)
Progress: 75.0% (338/450)
Progress: 100.0% (450/450)

================================================================================
Migration Complete
================================================================================
✅ Successfully upcasted: 450 events
📦 Backup snapshot: snapshot_20251230_153000
   To rollback, restore projections from this snapshot
================================================================================
```

#### 4. Filter by Event Type

Upcast only specific event types:

```bash
python backend/scripts/upcast_events.py upcast --event-type credit.allocated
```

#### 5. Validate Upcasters

Test all registered upcasters:

```bash
python backend/scripts/upcast_events.py validate
```

**Output:**
```
Validating credit.allocated v1 → v2...
  ✅ Valid
Validating credit.consumed v1 → v2...
  ✅ Valid

================================================================================
Validation Results
================================================================================
Total Upcasters: 2
Valid: 2
Invalid: 0
================================================================================
```

---

## Usage Guide

### Scenario 1: Add New Field to Event

**Step 1: Write Upcaster**

```python
# schema_versions.py
def upcast_credit_consumed_v1_to_v2(payload):
    """Add cost_breakdown field to credit.consumed events."""
    return {
        **payload,
        "cost_breakdown": {
            "base_cost": payload["amount"],
            "multiplier": 1.0,
            "total": payload["amount"],
        }
    }
```

**Step 2: Register Version**

```python
SCHEMA_REGISTRY.register_version(
    event_type=EventType.CREDIT_CONSUMED.value,
    version=2,
    upcaster=upcast_credit_consumed_v1_to_v2,
    description="Added cost_breakdown field for detailed cost tracking"
)
```

**Step 3: Update Event Creator**

```python
def create_credit_consumed_event(...):
    # ...
    payload = {
        "entity_id": entity_id,
        "amount": amount,
        "cost_breakdown": {  # NEW in v2
            "base_cost": amount,
            "multiplier": 1.0,
            "total": amount,
        }
    }

    return EventEnvelope(
        # ...
        payload=payload,
        schema_version=2,  # NEW version
    )
```

**Step 4: Deploy and Migrate**

```bash
# 1. Deploy code (with new upcaster registered)
docker compose build backend
docker compose restart backend

# 2. Test migration (dry run)
python backend/scripts/upcast_events.py upcast --dry-run

# 3. Perform migration
python backend/scripts/upcast_events.py upcast --with-snapshot
```

**Step 5: Verify**

```bash
# Check that all events are v2
python backend/scripts/upcast_events.py analyze
# Output: Need Upcast: 0 (0.0%)
```

### Scenario 2: Multiple Version Evolution

Events go from v1 → v2 → v3:

```python
# v1 → v2: Add metadata
def upcast_v1_to_v2(payload):
    return {**payload, "metadata": {}}

# v2 → v3: Add tags
def upcast_v2_to_v3(payload):
    return {**payload, "tags": []}

# Register sequentially
SCHEMA_REGISTRY.register_version("credit.allocated", 2, upcast_v1_to_v2)
SCHEMA_REGISTRY.register_version("credit.allocated", 3, upcast_v2_to_v3)

# Old v1 event will be upcasted through BOTH transformations:
# v1 → v2 (adds metadata) → v3 (adds tags)
```

---

## Integration

### Integrate with Replay Engine

Modify `replay.py` to upcast events during replay:

```python
# backend/app/modules/credits/event_sourcing/replay.py

from backend.app.modules.credits.event_sourcing.event_upcaster import upcast_event_if_needed

class ReplayEngine:
    async def replay_all(self):
        # ...

        async for event in self.journal.read_events():
            # Skip events before snapshot
            if snapshot and event_count <= start_sequence:
                continue

            try:
                # === UPCAST EVENT TO LATEST SCHEMA ===
                event = await upcast_event_if_needed(event)

                # Apply to projections (now guaranteed to be latest schema)
                await self.projection_manager.balance.handle_event(event)
                await self.projection_manager.ledger.handle_event(event)
                await self.projection_manager.approval.handle_event(event)
                await self.projection_manager.synergie.handle_event(event)

                # ...
```

### Update Event Handlers

Event handlers now always receive latest schema:

```python
# backend/app/modules/credits/event_sourcing/projections.py

class BalanceProjection:
    async def handle_event(self, event: EventEnvelope):
        """Handle event (guaranteed to be latest schema)."""

        if event.event_type == EventType.CREDIT_CONSUMED:
            # Can safely access v2 fields
            cost_breakdown = event.payload.get("cost_breakdown", {})
            base_cost = cost_breakdown.get("base_cost", event.payload["amount"])

            # Update balance
            # ...
```

---

## Best Practices

### 1. Always Preserve Required Fields

Upcasters must preserve all fields from previous version:

```python
# ✅ GOOD - Preserves all v1 fields
def upcast_v1_to_v2(payload):
    return {
        **payload,  # Spread operator preserves everything
        "new_field": "default_value"
    }

# ❌ BAD - Loses v1 fields
def upcast_v1_to_v2(payload):
    return {
        "entity_id": payload["entity_id"],
        "new_field": "default_value"
        # Lost: amount, reason, etc.
    }
```

### 2. Use Sensible Defaults

New fields should have safe default values:

```python
def upcast_v1_to_v2(payload):
    return {
        **payload,
        "metadata": {
            "source": "system",  # Safe default
            "migrated_at": datetime.now(timezone.utc).isoformat()
        }
    }
```

### 3. Keep Upcasters Pure

No side effects, external calls, or randomness:

```python
# ✅ GOOD - Pure function
def upcast_v1_to_v2(payload):
    return {**payload, "version": 2}

# ❌ BAD - Has side effects
def upcast_v1_to_v2(payload):
    db.insert(payload)  # Side effect!
    return {**payload, "id": random.uuid4()}  # Non-deterministic!
```

### 4. Test Upcasters Thoroughly

Write unit tests for every upcaster:

```python
import pytest

def test_upcast_credit_allocated_v1_to_v2():
    """Test credit.allocated v1 → v2 upcaster."""
    v1_payload = {
        "entity_id": "agent_123",
        "amount": 100.0,
        "reason": "Initial allocation"
    }

    v2_payload = upcast_credit_allocated_v1_to_v2(v1_payload)

    # Check v1 fields preserved
    assert v2_payload["entity_id"] == "agent_123"
    assert v2_payload["amount"] == 100.0
    assert v2_payload["reason"] == "Initial allocation"

    # Check v2 fields added
    assert "metadata" in v2_payload
    assert "source" in v2_payload["metadata"]
```

### 5. Document Schema Changes

Always include description when registering versions:

```python
SCHEMA_REGISTRY.register_version(
    event_type=EventType.CREDIT_ALLOCATED.value,
    version=2,
    upcaster=upcast_v1_to_v2,
    description="Added metadata field for enhanced tracking (2025-12-30)"
    #           ^ Clear description with date
)
```

### 6. Create Backup Before Migration

Always use `--with-snapshot` in production:

```bash
# ✅ GOOD - Creates backup
python upcast_events.py upcast --with-snapshot

# ❌ BAD - No rollback option
python upcast_events.py upcast
```

### 7. Test in Staging First

Migration workflow:
1. Deploy to staging
2. Run `analyze` - verify events detected
3. Run `upcast --dry-run` - preview changes
4. Run `upcast --with-snapshot` - perform migration
5. Run tests - verify projections still work
6. Deploy to production

---

## Testing

### Unit Tests

Test upcasters in isolation:

```python
# tests/test_schema_evolution.py
import pytest
from backend.app.modules.credits.event_sourcing.schema_versions import (
    SCHEMA_REGISTRY,
    upcast_credit_allocated_v1_to_v2,
)

def test_register_schema_version():
    """Test schema version registration."""
    # Should not raise
    SCHEMA_REGISTRY.register_version(
        event_type="test.event",
        version=1,
        upcaster=None,
        description="Test version"
    )

    assert SCHEMA_REGISTRY.get_latest_version("test.event") == 1

def test_upcaster_preserves_fields():
    """Test that upcaster preserves all v1 fields."""
    v1_payload = {
        "entity_id": "agent_123",
        "amount": 100.0,
        "reason": "Test"
    }

    v2_payload = upcast_credit_allocated_v1_to_v2(v1_payload)

    # All v1 fields must be preserved
    for key in v1_payload:
        assert key in v2_payload
        assert v2_payload[key] == v1_payload[key]
```

### Integration Tests

Test end-to-end upcasting:

```python
import pytest
from backend.app.modules.credits.event_sourcing.events import (
    EventEnvelope,
    EventType,
)
from backend.app.modules.credits.event_sourcing.event_upcaster import (
    upcast_event_if_needed,
)

@pytest.mark.asyncio
async def test_upcast_event_integration():
    """Test complete event upcasting flow."""
    # Create v1 event
    event_v1 = EventEnvelope(
        event_id="test_123",
        event_type=EventType.CREDIT_ALLOCATED,
        timestamp=datetime.now(timezone.utc),
        actor_id="system",
        correlation_id="agent_123",
        causation_id=None,
        payload={
            "entity_id": "agent_123",
            "amount": 100.0,
            "reason": "Test",
        },
        schema_version=1,  # Old version
        idempotency_key="test_123",
    )

    # Upcast to latest
    event_latest = await upcast_event_if_needed(event_v1)

    # Check version updated
    latest_version = SCHEMA_REGISTRY.get_latest_version("credit.allocated")
    assert event_latest.schema_version == latest_version

    # Check payload transformed
    if latest_version >= 2:
        assert "metadata" in event_latest.payload
```

### Live Tests

Test migration on copy of production data:

```bash
# 1. Export production events to test environment
pg_dump -t events production_db > events_backup.sql
psql test_db < events_backup.sql

# 2. Run migration on test data
DATABASE_URL="postgresql://test_db" python upcast_events.py upcast --dry-run

# 3. Verify results
DATABASE_URL="postgresql://test_db" python upcast_events.py analyze
```

---

## Performance

### Upcasting Overhead

- **Current version events:** O(1) - simple version check, no transformation
- **Old version events:** O(n) where n = number of versions to upcast through
  - Example: v1 → v4 requires 3 transformations (v1→v2, v2→v3, v3→v4)

### Optimization Strategies

1. **Keep schemas stable** - Minimize schema changes to reduce upcasting
2. **Periodic migration** - Upcast old events to latest version in journal
3. **Snapshot-based replay** - Load snapshot (already latest schema) + upcast delta only

### Benchmark

Typical performance (1000 events):
- **All v1 → v2:** ~50ms (0.05ms per event)
- **Mix of v1/v2:** ~25ms (50% need upcast)
- **All v2 (latest):** ~5ms (version check only)

---

## Troubleshooting

### Issue 1: Missing Upcaster

**Error:**
```
UpcastError: Missing upcaster for credit.allocated v1 → v2
```

**Solution:**
Register the missing upcaster:
```python
SCHEMA_REGISTRY.register_version(
    event_type="credit.allocated",
    version=2,
    upcaster=your_upcaster_function,
    description="..."
)
```

### Issue 2: Upcaster Loses Fields

**Error:**
```
KeyError: 'amount' not in event payload after upcasting
```

**Solution:**
Fix upcaster to preserve all fields:
```python
def upcast_v1_to_v2(payload):
    return {
        **payload,  # Use spread operator
        "new_field": "value"
    }
```

### Issue 3: Non-Sequential Versions

**Error:**
```
ValueError: Schema versions must be sequential. Expected version 3, got 4
```

**Solution:**
Register versions sequentially (no skipping):
```python
SCHEMA_REGISTRY.register_version(event_type, 2, upcast_v1_to_v2)
SCHEMA_REGISTRY.register_version(event_type, 3, upcast_v2_to_v3)
# Now can register v4
SCHEMA_REGISTRY.register_version(event_type, 4, upcast_v3_to_v4)
```

---

## Future Enhancements

### Phase 7b: Bulk Event Rewriting

Currently, upcasting happens at read-time (during replay). Future enhancement:
- **Write upcasted events back to journal** (update Postgres rows)
- **Benefit:** Reduce upcasting overhead on every replay
- **Trade-off:** More complex migration process

### Phase 7c: Schema Registry UI

Web UI for managing schemas:
- View all event types and versions
- Test upcasters with sample data
- Trigger migrations from UI
- Monitor migration progress

### Phase 7d: Automatic Schema Detection

Infer schema changes from code:
- Compare old vs new event creation functions
- Auto-generate upcaster skeletons
- Suggest sensible defaults for new fields

---

## Summary

Phase 7 enables **forward-compatible event schema evolution**:

✅ **Schema Version Registry** - Track all event versions
✅ **Event Upcaster** - Transform old events to latest schema
✅ **Migration CLI** - Analyze, dry-run, and migrate events
✅ **Integration** - Transparent upcasting during replay
✅ **Best Practices** - Pure functions, preserve fields, test thoroughly

**Result:** Events can evolve safely without breaking existing event streams. Old events remain immutable, projections always receive latest schema.

**Key Benefit:** Zero-downtime schema migrations for production event-sourced systems.

---

**End of Phase 7 Documentation**
