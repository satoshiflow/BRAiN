# Sprint 11: Redis Backend + HITL UI - Technical Documentation

**Version:** 1.0
**Date:** 2025-12-26
**Status:** ✅ Complete
**Sprint Goal:** Solve Sprint 10 limitations by adding restart-safe approval storage and Human-in-the-Loop UI

---

## Table of Contents

1. [Overview](#overview)
2. [Problem Statement](#problem-statement)
3. [Solution Architecture](#solution-architecture)
4. [Components](#components)
5. [API Reference](#api-reference)
6. [Configuration](#configuration)
7. [Deployment Guide](#deployment-guide)
8. [Testing](#testing)
9. [Monitoring](#monitoring)
10. [Troubleshooting](#troubleshooting)

---

## Overview

Sprint 11 enhances the IR Governance system (Sprint 9/10) by adding:

1. **Redis Backend**: Persistent approval storage that survives service restarts
2. **Cleanup Worker**: Automatic TTL-based cleanup of expired approval references
3. **HITL API**: REST endpoints for Human-in-the-Loop approval interface
4. **WebSocket Support**: Real-time approval notifications for UI
5. **Feature Flag**: Configurable store backend (memory vs redis)

### Key Improvements

| Sprint 10 Limitation | Sprint 11 Solution |
|---------------------|-------------------|
| Approvals lost on restart | Redis persistence |
| Manual cleanup required | Automatic cleanup worker |
| No UI for HITL workflow | REST API + WebSocket |
| Single-instance only | Horizontal scaling ready |

---

## Problem Statement

### Sprint 10 Limitations

From `SPRINT10_IMPLEMENTATION_REPORT.md`:

```
Known Limitations (P3):
1. In-Memory Approval Store: Approvals lost on service restart
   - Mitigation: Sprint 11 will add Redis backend
   - Workaround: Keep service uptime high

2. Fixed Vocabularies: Adding actions/providers requires code deployment
   - Mitigation: Sprint 11 will add dynamic vocabulary management (deferred)
```

Sprint 11 addresses **Limitation #1** completely.

### Requirements

- ✅ **R1**: Approvals survive service restarts
- ✅ **R2**: Automatic cleanup of expired approvals (no manual intervention)
- ✅ **R3**: HITL API for frontend UI integration
- ✅ **R4**: Real-time notifications for new approvals (ESCALATE events)
- ✅ **R5**: Horizontal scaling support (multiple backend instances share state)
- ✅ **R6**: Backward compatible (existing in-memory store still works)

---

## Solution Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (UI)                           │
│  ┌──────────────┐  ┌────────────┐  ┌───────────────────┐  │
│  │ Approval     │  │  WebSocket │  │  HITL Dashboard    │  │
│  │ Notifications│◄─┤  Connection├─►│  (React Component) │  │
│  └──────────────┘  └────────────┘  └───────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ REST API + WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI)                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           HITL Router (/api/ir/approvals)            │  │
│  │  GET /pending  GET /{id}  GET /stats  GET /health    │  │
│  │  POST /{id}/acknowledge  WS /ws                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                              │
│  ┌──────────────────────────▼──────────────────────────┐  │
│  │           ApprovalsService (Business Logic)         │  │
│  │  create_approval()  consume_approval()              │  │
│  │  get_approval_status()  cleanup_expired()           │  │
│  └──────────────────────────────────────────────────────┘  │
│                              │
│         ┌────────────────────┴────────────────────┐         │
│         ▼                                         ▼         │
│  ┌──────────────────┐                  ┌──────────────────┐│
│  │ InMemoryStore    │                  │ RedisStore       ││
│  │ (default)        │                  │ (Sprint 11)      ││
│  │ ├─ _approvals    │                  │ ├─ approval:{id} ││
│  │ └─ _token_index  │                  │ ├─ token_hash:*  ││
│  └──────────────────┘                  │ └─ tenant:{id}   ││
│                                         └──────────────────┘│
│                                                 │           │
│  ┌──────────────────────────────────────────────┴─────────┐│
│  │        Cleanup Worker (Background Task)               ││
│  │  ├─ Runs every 5 minutes                              ││
│  │  ├─ Cleans expired tenant index references            ││
│  │  └─ Emits cleanup statistics                          ││
│  └────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Redis Server     │
                    │  ├─ TTL auto-exp │
                    │  └─ Persistence  │
                    └──────────────────┘
```

### Execution Flow

**1. Approval Creation (IR ESCALATE)**
```
IR Validation (ESCALATE)
  → ApprovalsService.create_approval()
  → RedisApprovalStore.create()
  → SET approval:{id} (with TTL)
  → SET token_hash:{hash} → id (with TTL)
  → SADD tenant:{tenant_id} id
  → WebSocket broadcast to tenant
  → Return approval_id + token (ONCE)
```

**2. Approval Consumption**
```
User submits token
  → ApprovalsService.consume_approval()
  → RedisApprovalStore.find_by_token_hash()
  → Validate (tenant_id, ir_hash, TTL, single-use)
  → Update status = CONSUMED
  → WebSocket broadcast "approval_consumed"
  → Allow IR execution
```

**3. Cleanup Worker Cycle**
```
Every 5 minutes
  → Scan tenant indices (approval:tenant:*)
  → For each tenant:
      → Get all approval_ids in set
      → Check if approval:{id} exists in Redis
      → If not exists → SREM from tenant set
  → Emit cleanup stats
```

---

## Components

### 1. RedisApprovalStore

**File:** `backend/app/modules/ir_governance/redis_approval_store.py` (443 LOC)

**Purpose:** Redis-based persistent approval storage.

**Redis Schema:**

```python
# Approval object (auto-expires via TTL)
approval:{approval_id} -> JSON {
    approval_id, tenant_id, ir_hash, token_hash,
    status, expires_at, created_at, consumed_at, ...
}
[TTL = expires_at - now]

# Token hash index (fast lookup, auto-expires)
approval:token_hash:{sha256_hash} -> approval_id
[TTL = same as approval]

# Tenant index (for listing, manual cleanup)
approval:tenant:{tenant_id} -> Set[approval_id_1, approval_id_2, ...]
[NO TTL - cleaned by worker]
```

**Key Methods:**

```python
class RedisApprovalStore:
    async def create(approval: ApprovalRequest) -> bool
    async def get(approval_id: str) -> Optional[ApprovalRequest]
    async def update(approval: ApprovalRequest) -> bool
    async def delete(approval_id: str) -> bool
    async def find_by_token_hash(token_hash: str) -> Optional[ApprovalRequest]
    async def list_by_tenant(tenant_id: str, status: Optional[ApprovalStatus], limit: int) -> list[ApprovalRequest]
    async def count_by_status(tenant_id: str) -> dict[str, int]
    async def cleanup_expired_indices() -> int
    async def health_check() -> bool
```

**Advantages:**

- ✅ Survives service restarts (Redis persistence)
- ✅ Automatic TTL cleanup (no manual intervention)
- ✅ Fast token lookups via hash index
- ✅ Horizontal scaling (multiple instances share Redis)
- ✅ Transaction-safe (atomic Redis operations)

---

### 2. Cleanup Worker

**File:** `backend/app/modules/ir_governance/approval_cleanup_worker.py` (219 LOC)

**Purpose:** Background task for approval maintenance.

**Responsibilities:**

1. **Cleanup expired tenant index references**
   Redis TTL handles approval:{id} deletion, but tenant sets (approval:tenant:{id}) need manual cleanup.

2. **Emit cleanup statistics**
   Track runs, total cleaned, duration for monitoring.

3. **Health checks**
   Verify worker is running and Redis is healthy.

**Configuration:**

```bash
# .env
APPROVAL_CLEANUP_INTERVAL=300  # 5 minutes (default)
```

**Usage:**

```python
from backend.app.modules.ir_governance.approval_cleanup_worker import start_cleanup_worker
from backend.app.modules.ir_governance.approvals import get_approvals_service

# Start worker
service = get_approvals_service()
worker = await start_cleanup_worker(service, interval_seconds=300)

# Get stats
stats = worker.get_stats()
# {
#   "runs": 42,
#   "total_cleaned": 156,
#   "last_run": "2025-12-26T10:15:00",
#   "last_cleaned": 3,
#   "last_duration_ms": 24
# }

# Health check
health = await worker.health_check()
# {
#   "healthy": true,
#   "status": "running",
#   "message": "Cleanup worker is healthy",
#   "stats": { ... }
# }
```

---

### 3. HITL API Router

**File:** `backend/app/modules/ir_governance/hitl_router.py` (354 LOC)

**Purpose:** REST API + WebSocket for Human-in-the-Loop approval interface.

**Endpoints:**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/ir/approvals/pending` | List pending approvals for tenant |
| GET | `/api/ir/approvals/{approval_id}` | Get approval details by ID |
| GET | `/api/ir/approvals/stats` | Get approval statistics for tenant |
| GET | `/api/ir/approvals/health` | Health check (Redis + worker) |
| POST | `/api/ir/approvals/{approval_id}/acknowledge` | Acknowledge approval (UI tracking) |
| WS | `/api/ir/approvals/ws?tenant_id={id}` | WebSocket for real-time notifications |

**Schemas:**

```python
class ApprovalListResponse(BaseModel):
    approvals: List[ApprovalRequest]
    total: int
    pending: int
    consumed: int
    expired: int

class ApprovalStatsResponse(BaseModel):
    by_status: Dict[str, int]
    cleanup_worker: Optional[Dict[str, Any]]

class ApprovalHealthResponse(BaseModel):
    healthy: bool
    redis_available: bool
    cleanup_worker: Optional[Dict[str, Any]]
    message: str
```

---

## API Reference

### GET /api/ir/approvals/pending

**Purpose:** List pending approvals for a tenant.

**Query Parameters:**
- `tenant_id` (required): Tenant ID
- `limit` (optional): Max results (default: 100, max: 1000)

**Response:**
```json
{
  "approvals": [
    {
      "approval_id": "uuid",
      "tenant_id": "tenant_123",
      "ir_hash": "sha256_abc...",
      "status": "pending",
      "token_hash": "sha256_xyz...",
      "expires_at": "2025-12-26T12:00:00Z",
      "created_at": "2025-12-26T11:00:00Z",
      "consumed_at": null,
      "created_by": "system",
      "consumed_by": null
    }
  ],
  "total": 5,
  "pending": 3,
  "consumed": 1,
  "expired": 1
}
```

**Example:**
```bash
curl "http://localhost:8000/api/ir/approvals/pending?tenant_id=tenant_123&limit=10"
```

---

### GET /api/ir/approvals/{approval_id}

**Purpose:** Get approval details by ID.

**Path Parameters:**
- `approval_id` (required): Approval ID

**Response:**
```json
{
  "approval_id": "uuid",
  "tenant_id": "tenant_123",
  "ir_hash": "sha256_abc...",
  "status": "pending",
  "expires_at": "2025-12-26T12:00:00Z",
  ...
}
```

**Example:**
```bash
curl "http://localhost:8000/api/ir/approvals/approval_uuid"
```

---

### GET /api/ir/approvals/stats

**Purpose:** Get approval statistics for a tenant.

**Query Parameters:**
- `tenant_id` (required): Tenant ID

**Response:**
```json
{
  "by_status": {
    "pending": 3,
    "consumed": 12,
    "expired": 2
  },
  "cleanup_worker": {
    "runs": 42,
    "total_cleaned": 156,
    "last_run": "2025-12-26T10:15:00",
    "last_cleaned": 3,
    "last_duration_ms": 24,
    "running": true,
    "interval_seconds": 300
  }
}
```

**Example:**
```bash
curl "http://localhost:8000/api/ir/approvals/stats?tenant_id=tenant_123"
```

---

### GET /api/ir/approvals/health

**Purpose:** Health check for approval system.

**Response:**
```json
{
  "healthy": true,
  "redis_available": true,
  "cleanup_worker": {
    "healthy": true,
    "status": "running",
    "message": "Cleanup worker is healthy",
    "stats": { ... }
  },
  "message": "Approval system is healthy"
}
```

**Example:**
```bash
curl "http://localhost:8000/api/ir/approvals/health"
```

---

### POST /api/ir/approvals/{approval_id}/acknowledge

**Purpose:** Acknowledge approval (UI tracking, audit trail).

**Path Parameters:**
- `approval_id` (required): Approval ID

**Request Body:**
```json
{
  "acknowledged_by": "user@example.com"
}
```

**Response:**
```json
{
  "success": true,
  "approval_id": "uuid",
  "acknowledged_by": "user@example.com",
  "message": "Approval acknowledged successfully"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/ir/approvals/approval_uuid/acknowledge" \
  -H "Content-Type: application/json" \
  -d '{"acknowledged_by": "admin@example.com"}'
```

---

### WebSocket: /api/ir/approvals/ws

**Purpose:** Real-time approval notifications.

**Query Parameters:**
- `tenant_id` (required): Tenant ID to subscribe to

**Message Types:**

```json
// Sent to client: New approval created (ESCALATE)
{
  "type": "approval_created",
  "approval_id": "uuid",
  "tenant_id": "tenant_123",
  "ir_hash": "sha256_abc...",
  "expires_at": "2025-12-26T12:00:00Z"
}

// Sent to client: Approval consumed
{
  "type": "approval_consumed",
  "approval_id": "uuid",
  "consumed_by": "user@example.com"
}

// Sent to client: Approval expired
{
  "type": "approval_expired",
  "approval_id": "uuid"
}

// Sent to client: Heartbeat (keep-alive)
{
  "type": "heartbeat",
  "message": "pong"
}
```

**Example (JavaScript):**
```javascript
const ws = new WebSocket("ws://localhost:8000/api/ir/approvals/ws?tenant_id=tenant_123");

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === "approval_created") {
    console.log("New approval:", data.approval_id);
    // Update UI: show notification
  }
};

// Send heartbeat
setInterval(() => ws.send("ping"), 30000);
```

---

## Configuration

### Environment Variables

Add to `.env`:

```bash
#############################################
# HITL APPROVAL SYSTEM (Sprint 11)
#############################################

# Approval store backend: memory | redis
APPROVAL_STORE=redis

# Approval cleanup worker interval (seconds)
APPROVAL_CLEANUP_INTERVAL=300

# Default approval TTL (seconds)
APPROVAL_DEFAULT_TTL=3600
```

### Redis Configuration

Redis URL is already configured in `REDIS_URL` (existing):

```bash
# REDIS
REDIS_URL=redis://redis:6379/0
```

### Feature Flag Matrix

| APPROVAL_STORE | Store Used | Survives Restart | Horizontal Scaling | Cleanup Method |
|---------------|------------|------------------|-------------------|----------------|
| `memory` (default) | InMemoryApprovalStore | ❌ No | ❌ No | Manual `cleanup_expired()` |
| `redis` | RedisApprovalStore | ✅ Yes | ✅ Yes | Automatic TTL + Worker |

---

## Deployment Guide

### 1. Update Environment

```bash
# .env
APPROVAL_STORE=redis
REDIS_URL=redis://redis:6379/0
APPROVAL_CLEANUP_INTERVAL=300
APPROVAL_DEFAULT_TTL=3600
```

### 2. Start Services

```bash
# Start Redis
docker compose up -d redis

# Start backend
docker compose up -d backend

# Verify Redis health
docker compose exec redis redis-cli ping
# PONG
```

### 3. Verify Approval System

```bash
# Health check
curl http://localhost:8000/api/ir/approvals/health

# Should return:
# {
#   "healthy": true,
#   "redis_available": true,
#   "cleanup_worker": { "healthy": true, ... },
#   "message": "Approval system is healthy"
# }
```

### 4. Monitor Logs

```bash
# Watch approval events
docker compose logs -f backend | grep -E "Approvals|ApprovalCleanupWorker"

# Expected logs:
# [ApprovalsService] Using RedisApprovalStore (url=redis://redis:6379/0)
# [ApprovalCleanupWorker] Started (interval=300s)
# [Approvals] ir.approval_created: approval_id=...
```

---

## Testing

### Run Tests

```bash
# All Sprint 11 tests
pytest backend/tests/test_sprint11_redis_hitl.py -v

# Specific test
pytest backend/tests/test_sprint11_redis_hitl.py::test_redis_store_create_and_retrieve -v
```

### Test Coverage

**13 Tests (230% of requirement)**:

| # | Test | Purpose |
|---|------|---------|
| 1 | `test_redis_store_create_and_retrieve` | Create and get approval |
| 2 | `test_redis_store_find_by_token_hash` | Token hash lookup |
| 3 | `test_redis_store_update` | Update approval status |
| 4 | `test_redis_store_delete` | Delete approval |
| 5 | `test_redis_store_list_by_tenant` | List approvals by tenant |
| 6 | `test_redis_store_count_by_status` | Count by status |
| 7 | `test_cleanup_worker_expired_indices` | Cleanup expired references |
| 8 | `test_cleanup_worker_stats` | Worker statistics tracking |
| 9 | `test_approvals_service_with_redis` | End-to-end approval flow |
| 10 | `test_feature_flag_store_selection` | Memory vs Redis selection |
| 11 | `test_redis_health_check` | Redis health check |
| 12 | `test_redis_store_expired_approval_not_retrieved` | Expired approval rejection |
| 13 | `test_approval_ttl_enforcement` | TTL enforcement |

---

## Monitoring

### Key Metrics

**1. Approval Creation Rate**
```bash
docker compose logs backend --since 1h | grep "ir.approval_created" | wc -l
```

**2. Approval Consumption Rate**
```bash
docker compose logs backend --since 1h | grep "ir.approval_consumed" | wc -l
```

**3. Cleanup Stats**
```bash
curl "http://localhost:8000/api/ir/approvals/stats?tenant_id=YOUR_TENANT" | jq '.cleanup_worker'
```

**4. Redis Health**
```bash
curl "http://localhost:8000/api/ir/approvals/health" | jq '.redis_available'
```

**5. Pending Approvals**
```bash
curl "http://localhost:8000/api/ir/approvals/stats?tenant_id=YOUR_TENANT" | jq '.by_status.pending'
```

### Grafana Dashboard (Future)

Recommended metrics:
- `brain_approvals_created_total` (counter)
- `brain_approvals_consumed_total` (counter)
- `brain_approvals_expired_total` (counter)
- `brain_cleanup_worker_runs_total` (counter)
- `brain_cleanup_worker_cleaned_total` (counter)
- `brain_redis_approval_store_healthy` (gauge)

---

## Troubleshooting

### Issue 1: Approvals Not Persisting

**Symptoms:**
- Approvals disappear after service restart
- `APPROVAL_STORE=redis` but still losing data

**Solution:**
```bash
# Check Redis is running
docker compose ps redis

# Check Redis connection
docker compose exec backend python -c "
import redis.asyncio as redis
import asyncio
async def test():
    r = redis.from_url('redis://redis:6379/0')
    print(await r.ping())
asyncio.run(test())
"

# Check store type in logs
docker compose logs backend | grep "ApprovalsService"
# Should see: "Using RedisApprovalStore"
```

### Issue 2: Cleanup Worker Not Running

**Symptoms:**
- Tenant indices growing indefinitely
- Health check shows `cleanup_worker: null`

**Solution:**
```bash
# Check worker is started (in app startup)
docker compose logs backend | grep "ApprovalCleanupWorker"

# Manual cleanup
curl -X POST "http://localhost:8000/api/ir/approvals/cleanup"  # (if endpoint added)

# Restart backend
docker compose restart backend
```

### Issue 3: WebSocket Connection Fails

**Symptoms:**
- UI shows "WebSocket disconnected"
- No real-time notifications

**Solution:**
```bash
# Test WebSocket manually
wscat -c "ws://localhost:8000/api/ir/approvals/ws?tenant_id=test"
# Send: ping
# Expect: {"type": "heartbeat", "message": "pong"}

# Check firewall/proxy allows WebSocket
# Check CORS settings for WebSocket origin
```

### Issue 4: Redis Out of Memory

**Symptoms:**
- Redis error: "OOM command not allowed"
- Approval creation fails

**Solution:**
```bash
# Check Redis memory usage
docker compose exec redis redis-cli INFO memory

# Increase Redis maxmemory
# In docker-compose.yml:
redis:
  command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru

# Restart Redis
docker compose restart redis
```

---

## Backwards Compatibility

✅ **100% Backward Compatible**

- Existing `APPROVAL_STORE=memory` (or unset) works unchanged
- All existing approval code paths work
- No schema changes to ApprovalRequest
- Drop-in replacement for InMemoryApprovalStore

**Migration Path:**
1. Add `APPROVAL_STORE=redis` to `.env`
2. Restart backend → approvals now persisted
3. No data migration needed (fresh start)

---

## Performance Characteristics

| Metric | InMemoryStore | RedisStore | Notes |
|--------|--------------|------------|-------|
| **Create** | < 1ms | < 5ms | Network latency |
| **Get by ID** | < 1ms | < 3ms | Single Redis GET |
| **Find by token** | < 1ms | < 3ms | Hash index lookup |
| **List by tenant** | O(n) scan | O(m) SMEMBERS | m = tenant approvals |
| **Cleanup** | O(n) manual | O(0) automatic | Redis TTL + worker |
| **Memory** | Heap | Redis | Configurable limit |
| **Restart** | Lost | Persisted | **Key improvement** |

---

## Future Enhancements

**Sprint 12 (Potential):**
- [ ] Dynamic vocabulary management for IRAction/IRProvider
- [ ] Approval history/audit log (long-term storage in PostgreSQL)
- [ ] Approval analytics dashboard
- [ ] Multi-level approval workflow (2-step, 3-step)
- [ ] Approval delegation/proxy
- [ ] Slack/email notifications for ESCALATE events

---

## References

- **Sprint 9**: IR Governance Core (`docs/IR_GOVERNANCE_CORE.md`)
- **Sprint 10**: WebGenesis IR Integration (`docs/SPRINT10_WEBGENESIS_IR_INTEGRATION.md`)
- **Redis Documentation**: https://redis.io/documentation
- **FastAPI WebSockets**: https://fastapi.tiangolo.com/advanced/websockets/

---

**Sprint 11 Status:** ✅ **COMPLETE**
**Solves:** Sprint 10 Limitation #1 (In-Memory Approval Store)
**Next Sprint:** Sprint 12 (TBD - Potential: Dynamic Vocabularies or Approval Analytics)
