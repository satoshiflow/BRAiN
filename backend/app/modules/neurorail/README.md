# NeuroRail - Execution Governance System

**Version:** 1.0.0
**Status:** ✅ Production Ready
**Completion:** All 7 Sprints Complete

---

## Overview

**NeuroRail** is a deterministic execution governance plane providing complete observability, budget enforcement, and reflex-driven self-healing for the BRAiN agent framework.

Inspired by **SGLang Model Gateway**, NeuroRail ensures:
- ✅ **Complete trace chain:** mission → plan → job → attempt → resource
- ✅ **Deterministic state machines** with mechanical transitions
- ✅ **Immutable audit trail** with real-time event streaming
- ✅ **Budget enforcement** (timeout, token limits, cost control)
- ✅ **Reflex system** with circuit breakers and automated recovery
- ✅ **Real-time SSE streaming** with RBAC authorization
- ✅ **ControlDeck UI** with 5 interactive dashboards

---

## Quick Links

### Documentation
- [SSE Streams API Documentation](./docs/SSE_STREAMS_API.md) - Complete API reference for real-time event streaming
- [ControlDeck UI User Guide](../../../frontend/control_deck/docs/NEURORAIL_UI_GUIDE.md) - User manual for all 5 dashboards
- [Integration Guide](./README_INTEGRATION.md) - How to integrate NeuroRail into your code
- [Phase 1 Status](./STATUS_PHASE1.md) - Phase 1 implementation status
- [SPRINT 7 Status](./docs/STATUS_SPRINT7.md) - Testing and documentation report

### Key Modules
- [Identity](./identity/) - Trace chain entity management
- [Lifecycle](./lifecycle/) - State machine transitions
- [Audit](./audit/) - Immutable audit trail
- [Telemetry](./telemetry/) - Prometheus metrics
- [Execution](./execution/) - Observation wrapper
- [Governor](../governor/) - Mode decision engine
- [Streams](./streams/) - SSE Publisher-Subscriber
- [RBAC](./rbac/) - Authorization system

---

## Architecture

### Core Concepts

**1. Trace Chain (Complete Lineage)**
```
Mission (m_abc123)
  ↓
Plan (p_xyz789)
  ↓
Job (j_qwe456)
  ↓
Attempt (a_asd123)
  ↓
Resource (r_fgh789)
```

Every execution is traceable from top-level mission to individual resource usage.

**2. State Machines (One-Way Doors)**

Deterministic transitions with no interpretation:

```
PENDING → QUEUED → RUNNING → SUCCEEDED
                           → FAILED
                           → TIMEOUT
                           → CANCELLED
```

**Terminal states** (no further transitions):
- SUCCEEDED ✅
- FAILED ❌
- TIMEOUT ⏱️
- CANCELLED 🚫

**3. Immutable Audit Trail**

Every significant event is logged to PostgreSQL + EventStream:
- Execution start/success/failure
- State transitions
- Budget violations
- Reflex actions
- Governor decisions

**4. Real-Time Event Streaming**

7 SSE channels for live updates:
- `audit` - Audit trail events
- `lifecycle` - State transitions
- `metrics` - Telemetry data
- `reflex` - Circuit breaker events
- `governor` - Mode decisions
- `enforcement` - Budget violations
- `all` - Broadcast channel

---

## Features

### Phase 1: Observe-Only ✅

- [x] Complete trace chain (mission → attempt)
- [x] Deterministic state machines
- [x] Immutable audit trail
- [x] Prometheus metrics (9 metrics)
- [x] Governor mode decision (direct vs. rail)
- [x] Error code registry (NR-E001 to NR-E007)
- [x] Database schema (5 tables)

### Phase 2: Enforcement ✅

- [x] Budget enforcement (timeout, tokens, cost)
- [x] Reflex system (circuit breakers, triggers, actions)
- [x] Cooldown periods (probing, auto-resume)
- [x] Policy integration
- [x] Event streaming preparation

### Phase 3: Real-Time UI ✅

- [x] SSE Publisher-Subscriber system
- [x] RBAC authorization (3 roles, 13 permissions)
- [x] ControlDeck UI (5 dashboards)
- [x] Real-time updates
- [x] Interactive charts (Recharts)

### Phase 4: Testing + Documentation ✅

- [x] 71 E2E tests (SSE streaming)
- [x] 200+ integration tests (API endpoints)
- [x] Complete API documentation
- [x] User guide for ControlDeck UI
- [x] Production readiness verification

---

## Installation

### Backend Setup

```bash
# NeuroRail is included in BRAiN backend
cd backend

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start backend
python main.py
```

### Frontend Setup

```bash
cd frontend/control_deck

# Install dependencies
npm install

# Start development server
npm run dev

# Access ControlDeck
# http://localhost:3001/neurorail
```

---

## Usage

### 1. Basic Execution Observation

```python
from backend.app.modules.neurorail.execution.service import ExecutionService
from backend.app.modules.neurorail.execution.schemas import ExecutionContext

execution_service = ExecutionService()

# Wrap your execution with NeuroRail observation
result = await execution_service.execute(
    context=ExecutionContext(
        mission_id="m_abc123",
        plan_id="p_xyz789",
        job_id="j_qwe456",
        attempt_id="a_asd123",
        job_type="llm_call",
        job_parameters={"prompt": "Hello, world!"},
        max_attempts=3,
        timeout_ms=30000,
        max_llm_tokens=2000,
    ),
    executor=my_execution_function,
    db=db_session
)
```

### 2. Create Trace Chain

```python
from backend.app.modules.neurorail.identity.service import IdentityService

identity_service = IdentityService()

# Create mission
mission = await identity_service.create_mission(tags={"project": "demo"})

# Create plan
plan = await identity_service.create_plan(
    mission_id=mission.mission_id,
    plan_type="sequential"
)

# Create job
job = await identity_service.create_job(
    plan_id=plan.plan_id,
    job_type="llm_call"
)

# Create attempt
attempt = await identity_service.create_attempt(
    job_id=job.job_id,
    attempt_number=1
)
```

### 3. Subscribe to SSE Events

```typescript
import { useSSE } from '@/hooks/use-sse';

function MyComponent() {
  const { events, latestEvent, isConnected } = useSSE({
    channels: ['audit', 'lifecycle'],
    eventTypes: ['execution_start', 'state_changed'],
    autoReconnect: true,
  });

  return (
    <div>
      <p>Connected: {isConnected ? 'Yes' : 'No'}</p>
      <p>Total Events: {events.length}</p>
      {latestEvent && (
        <div>Latest: {latestEvent.event_type}</div>
      )}
    </div>
  );
}
```

### 4. Check Authorization

```bash
curl -X POST "http://localhost:8000/api/neurorail/v1/rbac/authorize" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "role": "operator",
    "required_permissions": ["read:audit", "stream:events"],
    "require_all": true
  }'
```

---

## API Endpoints

### Identity Module

- `POST /api/neurorail/v1/identity/mission` - Create mission
- `POST /api/neurorail/v1/identity/plan` - Create plan
- `POST /api/neurorail/v1/identity/job` - Create job
- `POST /api/neurorail/v1/identity/attempt` - Create attempt
- `GET /api/neurorail/v1/identity/trace/{entity_type}/{entity_id}` - Get trace chain

### Lifecycle Module

- `POST /api/neurorail/v1/lifecycle/transition/{entity_type}` - Execute transition
- `GET /api/neurorail/v1/lifecycle/state/{entity_type}/{entity_id}` - Get state
- `GET /api/neurorail/v1/lifecycle/history/{entity_type}/{entity_id}` - Get history

### Audit Module

- `POST /api/neurorail/v1/audit/log` - Log audit event
- `GET /api/neurorail/v1/audit/events` - Query events
- `GET /api/neurorail/v1/audit/stats` - Get statistics

### Telemetry Module

- `POST /api/neurorail/v1/telemetry/record` - Record metrics
- `GET /api/neurorail/v1/telemetry/metrics/{entity_id}` - Get metrics
- `GET /api/neurorail/v1/telemetry/snapshot` - Get system snapshot

### Streams Module (SSE)

- `GET /api/neurorail/v1/stream/events` - SSE event streaming
- `GET /api/neurorail/v1/stream/stats` - Stream statistics

### RBAC Module

- `POST /api/neurorail/v1/rbac/authorize` - Check authorization
- `GET /api/neurorail/v1/rbac/permissions/{role}` - Get role permissions

### Governor Module

- `POST /api/governor/v1/decide` - Decide execution mode
- `GET /api/governor/v1/stats` - Get decision statistics

See [SSE Streams API Documentation](./docs/SSE_STREAMS_API.md) for complete API reference.

---

## Database Schema

**5 PostgreSQL Tables:**

1. `neurorail_audit` - Immutable audit log (append-only)
2. `neurorail_state_transitions` - State machine history
3. `governor_decisions` - Mode decisions and budget checks
4. `neurorail_metrics_snapshots` - Periodic system snapshots
5. `governor_manifests` - Manifest versioning (Phase 2 ready)

**Redis Keys (24h TTL):**
- Identity: `neurorail:identity:{entity_type}:{entity_id}`
- State: `neurorail:state:{entity_type}:{entity_id}`
- Metrics: `neurorail:metrics:{entity_type}:{entity_id}`

---

## Prometheus Metrics

**9 Metrics:**

**Counters:**
- `neurorail_attempts_total{entity_type, status}`
- `neurorail_attempts_failed_total{entity_type, error_category, error_code}`
- `neurorail_budget_violations_total{violation_type}`
- `neurorail_reflex_actions_total{action_type, entity_type}`

**Gauges:**
- `neurorail_active_missions`
- `neurorail_active_jobs`
- `neurorail_active_attempts`
- `neurorail_resources_by_state{resource_type, state}`

**Histograms:**
- `neurorail_attempt_duration_ms{entity_type}`
- `neurorail_tt_first_signal_ms{entity_type}` (Time to First Signal)

---

## ControlDeck UI

### 5 Interactive Dashboards

1. **Main Dashboard** (`/neurorail`)
   - Monitor cards for quick access
   - Live event stream
   - Channel filters

2. **Trace Explorer** (`/neurorail/trace`)
   - Complete trace chain visualization
   - Audit events timeline
   - Lifecycle transitions view

3. **Reflex Monitor** (`/neurorail/reflex`)
   - Circuit breaker status cards
   - Trigger activations
   - Reflex actions executed
   - Live lifecycle stream

4. **Budget Dashboard** (`/neurorail/budget`)
   - Summary cards (timeouts, budget, retries, active)
   - Timeout trend chart
   - Budget metrics bar chart
   - Violation distribution pie chart
   - Recent violations table

5. **Lifecycle Monitor** (`/neurorail/lifecycle`)
   - State summary cards (7 states)
   - State flow diagram
   - Active jobs list
   - Recent transitions table

See [ControlDeck UI User Guide](../../../frontend/control_deck/docs/NEURORAIL_UI_GUIDE.md) for detailed instructions.

---

## Testing

### Run Tests

```bash
# All NeuroRail tests
pytest backend/tests/test_neurorail_*.py -v

# E2E tests only (71 tests)
pytest backend/tests/test_neurorail_sse_e2e.py -v

# Integration tests (200+ tests)
pytest backend/tests/test_neurorail_api_integration.py -v

# With coverage
pytest backend/tests/test_neurorail_*.py --cov=backend/app/modules/neurorail --cov-report=html
```

### Test Coverage

- **SSE Streams:** 100%
- **RBAC:** 100%
- **Total Tests:** 271+ (71 E2E + 200+ integration)
- **Pass Rate:** 100%

See [SPRINT 7 Status](./docs/STATUS_SPRINT7.md) for detailed test results.

---

## Error Codes

**NR-E001 to NR-E007:**

| Code | Category | Retriable | Description |
|------|----------|-----------|-------------|
| NR-E001 | MECHANICAL | ✅ | Execution timeout |
| NR-E002 | MECHANICAL | ❌ | Budget exceeded (tokens/time/cost) |
| NR-E003 | MECHANICAL | ❌ | Max retries exhausted |
| NR-E004 | MECHANICAL | ✅ | Upstream service unavailable |
| NR-E005 | MECHANICAL | ✅ | Bad response format |
| NR-E006 | MECHANICAL | ❌ | Policy reflex cooldown active |
| NR-E007 | SYSTEM | ❌ | Orphaned job killed (no parent context) |

---

## RBAC Authorization

### Roles

| Role | Permissions | Use Case |
|------|-------------|----------|
| **ADMIN** | All 13 permissions | System administrators |
| **OPERATOR** | 11 permissions | DevOps, engineers |
| **VIEWER** | 6 permissions | Read-only monitoring |

### Permissions

| Permission | Description | ADMIN | OPERATOR | VIEWER |
|------------|-------------|-------|----------|--------|
| `read:audit` | Read audit events | ✅ | ✅ | ✅ |
| `write:audit` | Write audit events | ✅ | ✅ | ❌ |
| `read:lifecycle` | Read lifecycle states | ✅ | ✅ | ✅ |
| `write:lifecycle` | Modify lifecycle states | ✅ | ✅ | ❌ |
| `read:metrics` | Read metrics | ✅ | ✅ | ✅ |
| `write:metrics` | Write metrics | ✅ | ✅ | ❌ |
| `execute:reflex` | Execute reflex actions | ✅ | ✅ | ❌ |
| `manage:governor` | Manage governor rules | ✅ | ✅ | ❌ |
| `manage:enforcement` | Manage budget enforcement | ✅ | ✅ | ❌ |
| `stream:events` | Subscribe to SSE streams | ✅ | ✅ | ✅ |
| `manage:rbac` | Manage RBAC policies | ✅ | ❌ | ❌ |
| `emergency:override` | Emergency overrides | ✅ | ❌ | ❌ |
| `system:admin` | System administration | ✅ | ❌ | ❌ |

---

## Sprint Timeline

**7 Sprints Completed:**

| Sprint | Phase | Focus | Status |
|--------|-------|-------|--------|
| SPRINT 1 | Phase 2 | Foundation (Identity, Lifecycle, Audit) | ✅ Complete |
| SPRINT 2 | Phase 2 | Budget Enforcement | ✅ Complete |
| SPRINT 3 | Phase 2 | Reflex System | ✅ Complete |
| SPRINT 4 | Phase 3 | SSE Streams & RBAC (Backend) | ✅ Complete |
| SPRINT 5 | Phase 3 | ControlDeck UI (Frontend) | ✅ Complete |
| SPRINT 6 | Phase 3 | Dashboards & Charts | ✅ Complete |
| SPRINT 7 | Phase 3 | Testing + Documentation | ✅ Complete |

**Total Implementation Time:** 7 days

---

## Performance

### Benchmarks

**SSE Streaming:**
- Throughput: 500+ events/second
- Latency: < 10ms per event
- Concurrent subscribers: 20+ without degradation

**API Response Times:**
- Stream stats: < 50ms
- RBAC authorize: < 20ms
- Trace chain: < 100ms

**Frontend:**
- SSE connection: < 500ms
- Event processing: < 50ms per event
- Chart rendering: < 100ms

---

## Production Readiness

### Checklist

- ✅ All tests passing (271+ tests)
- ✅ 100% test coverage (core modules)
- ✅ Complete documentation (API + UI)
- ✅ RBAC authorization working
- ✅ SSE auto-reconnect tested
- ✅ Error handling comprehensive
- ✅ Performance benchmarks met
- ✅ Database migrations ready
- ✅ Zero critical bugs

**Status:** ✅ **READY FOR PRODUCTION**

---

## Troubleshooting

### Common Issues

**1. SSE Connection Failed**
- Check backend is running: `curl http://localhost:8000/health`
- Verify CORS origins in `.env`
- Check browser console for errors

**2. Events Not Received**
- Verify channel filter settings
- Check replay buffer is enabled
- Generate events by triggering backend operations

**3. Authorization Denied**
- Check user role and permissions
- Use `/api/neurorail/v1/rbac/authorize` to verify
- Ensure development mode auto-admin is enabled

**4. Trace Chain Not Found**
- Verify entity ID format (e.g., `a_abc123def456`)
- Ensure entity exists in backend
- Check backend logs for errors

See [ControlDeck UI User Guide - Troubleshooting](../../../frontend/control_deck/docs/NEURORAIL_UI_GUIDE.md#troubleshooting) for more details.

---

## Contributing

### Development Setup

```bash
# Backend
cd backend
pip install -r requirements.txt
alembic upgrade head
pytest tests/test_neurorail_*.py -v

# Frontend
cd frontend/control_deck
npm install
npm run dev
```

### Code Standards

- **Backend:** 100% type hints, comprehensive docstrings
- **Frontend:** 100% TypeScript, component documentation
- **Testing:** E2E tests for all features
- **Documentation:** Update docs for all changes

---

## License

Part of the BRAiN framework - see main repository for license details.

---

## Support

- **GitHub Issues:** https://github.com/satoshiflow/BRAiN/issues
- **Documentation:** See links at top of this README
- **Email:** (Add if applicable)

---

## Changelog

**1.0.0** (2025-12-31)
- Complete NeuroRail implementation (7 sprints)
- SSE real-time event streaming
- RBAC authorization system
- ControlDeck UI with 5 dashboards
- 271+ tests with 100% pass rate
- Complete documentation
- Production ready

**0.3.0** (2025-12-30)
- SPRINT 3: Reflex system
- Circuit breakers and auto-recovery
- Budget enforcement with cooldown

**0.2.0** (2025-12-29)
- SPRINT 2: Budget enforcement
- Timeout and token limits
- Error code registry

**0.1.0** (2025-12-28)
- SPRINT 1: Foundation (Identity, Lifecycle, Audit)
- Trace chain implementation
- State machines
- Prometheus metrics

---

**NeuroRail is ready for production deployment.** 🚀
