# Phase 2: Database CRUD Operations + Basic Features

## Status: Ready for Implementation
## Prerequisites: ✅ Phase 1 Complete (Backend v2 with DB connectivity)

---

## Goals

1. **Add first database table** - Simple entity to test PostgreSQL CRUD
2. **Implement CRUD endpoints** - Create, Read, Update, Delete operations
3. **Add Alembic migrations** - Database schema versioning
4. **Redis caching** - Cache frequently accessed data
5. **Basic validation** - Pydantic models with validation

---

## Implementation Plan

### Step 1: Database Model - System Events Table

**Purpose:** Track system events/status changes (health checks, deployments, errors)

**Schema:**
```sql
CREATE TABLE system_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,  -- info, warning, error, critical
    message TEXT NOT NULL,
    details JSONB,
    source VARCHAR(100),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_system_events_type ON system_events(event_type);
CREATE INDEX idx_system_events_severity ON system_events(severity);
CREATE INDEX idx_system_events_timestamp ON system_events(timestamp);
```

**Why this table?**
- Simple, real-world use case
- Tests JSONB support
- Tests indexes
- Useful for monitoring
- Easy to expand later

---

### Step 2: Pydantic Models

**File:** `backend/models/system_event.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class EventSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class SystemEventCreate(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=50)
    severity: EventSeverity
    message: str = Field(..., min_length=1)
    details: Optional[Dict[str, Any]] = None
    source: Optional[str] = Field(None, max_length=100)

class SystemEventUpdate(BaseModel):
    event_type: Optional[str] = Field(None, min_length=1, max_length=50)
    severity: Optional[EventSeverity] = None
    message: Optional[str] = Field(None, min_length=1)
    details: Optional[Dict[str, Any]] = None
    source: Optional[str] = Field(None, max_length=100)

class SystemEventResponse(BaseModel):
    id: int
    event_type: str
    severity: EventSeverity
    message: str
    details: Optional[Dict[str, Any]]
    source: Optional[str]
    timestamp: datetime
    created_at: datetime

    class Config:
        from_attributes = True
```

---

### Step 3: CRUD Service

**File:** `backend/services/system_events.py`

Functions:
- `create_event()` - Insert new event
- `get_event(event_id)` - Get event by ID
- `list_events(filters)` - List events with filtering
- `update_event(event_id, data)` - Update event
- `delete_event(event_id)` - Delete event
- `get_events_by_type(event_type)` - Get events by type
- `get_events_by_severity(severity)` - Get events by severity

With Redis caching for frequently accessed events.

---

### Step 4: API Endpoints

**File:** `backend/api/routes/events.py`

```
POST   /api/events              - Create event
GET    /api/events              - List events (with filters)
GET    /api/events/{id}         - Get event by ID
PUT    /api/events/{id}         - Update event
DELETE /api/events/{id}         - Delete event
GET    /api/events/type/{type}  - Get events by type
GET    /api/events/stats        - Get event statistics
```

---

### Step 5: Alembic Migration

**File:** `backend/alembic/versions/001_create_system_events.py`

Create the migration to build the system_events table with indexes.

---

### Step 6: Redis Caching Strategy

**Cache Keys:**
```
events:id:{event_id}           - Single event (TTL: 300s)
events:type:{event_type}       - Events by type (TTL: 60s)
events:stats                   - Event statistics (TTL: 30s)
```

**Cache Invalidation:**
- On create: invalidate stats, type caches
- On update: invalidate event cache, stats, type caches
- On delete: invalidate all related caches

---

### Step 7: Integration with main_minimal_v2.py

Add event tracking to health checks:
- Log health check events
- Log database connection events
- Track startup/shutdown events

---

## Testing Plan

1. **Unit Tests:**
   - Test CRUD operations
   - Test validation
   - Test Redis caching

2. **Integration Tests:**
   - Test API endpoints
   - Test database transactions
   - Test cache invalidation

3. **Manual Testing:**
   ```bash
   # Create event
   curl -X POST https://dev.brain.falklabs.de/api/events \
     -H "Content-Type: application/json" \
     -d '{"event_type":"health_check","severity":"info","message":"System healthy"}'

   # List events
   curl https://dev.brain.falklabs.de/api/events

   # Get event by ID
   curl https://dev.brain.falklabs.de/api/events/1

   # Update event
   curl -X PUT https://dev.brain.falklabs.de/api/events/1 \
     -H "Content-Type: application/json" \
     -d '{"severity":"warning"}'

   # Delete event
   curl -X DELETE https://dev.brain.falklabs.de/api/events/1

   # Get statistics
   curl https://dev.brain.falklabs.de/api/events/stats
   ```

---

## File Structure After Phase 2

```
backend/
├── models/
│   ├── __init__.py
│   └── system_event.py          # NEW: Pydantic models
├── services/
│   ├── __init__.py
│   └── system_events.py          # NEW: CRUD service
├── api/routes/
│   └── events.py                 # NEW: API endpoints
├── alembic/
│   ├── versions/
│   │   └── 001_create_system_events.py  # NEW: Migration
│   ├── env.py
│   └── alembic.ini
├── main_minimal_v2.py            # UPDATED: Add event tracking
├── requirements-minimal.txt       # UPDATED: Add alembic
├── Dockerfile.minimal.v2          # Same (no changes needed)
└── DEPLOY_V2.sh                  # UPDATED: Run migrations on deploy
```

---

## Success Criteria

✅ System events table created via migration
✅ CRUD endpoints working
✅ Redis caching functional
✅ Event statistics endpoint working
✅ Integration with health checks
✅ All tests passing
✅ Documentation complete

---

## Next Steps After Phase 2

**Phase 3:** Add more complex features
- User authentication (if needed)
- Mission queue integration (from legacy system)
- WebSocket real-time events
- Qdrant vector search integration

**Phase 4:** Frontend integration
- Fix brain_control_ui build errors
- Connect to Phase 2 API endpoints
- Real-time event dashboard

---

## Estimated Complexity

- **Time:** 30-45 minutes implementation
- **Difficulty:** Medium (involves multiple files + migration)
- **Risk:** Low (isolated feature, doesn't affect existing functionality)

---

## Notes for Implementation

1. Start with Alembic setup first (if not already configured)
2. Create migration and test it manually
3. Build models → service → endpoints in that order
4. Test each layer before moving to next
5. Add caching last (so we can test without it first)
6. Update DEPLOY_V2.sh to run migrations automatically

---

**Ready to start when you return from break! 🚀**
