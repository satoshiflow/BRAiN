# NeuroRail Integration Guide

## Overview

This document describes the integration of NeuroRail modules into the BRAiN backend.

**Version:** 1.0 (Phase 1: Observe-only)
**Status:** ✅ Integrated and tested

## Modules Integrated

### 1. Identity Module (`/api/neurorail/v1/identity`)

Manages trace chain entity creation and retrieval:
- `POST /mission` - Create mission identity
- `POST /plan` - Create plan identity
- `POST /job` - Create job identity
- `POST /attempt` - Create attempt identity
- `POST /resource` - Create resource identity
- `GET /trace/{entity_type}/{entity_id}` - Retrieve complete trace chain

**Trace Chain:** `mission_id → plan_id → job_id → attempt_id → resource_uuid`

### 2. Lifecycle Module (`/api/neurorail/v1/lifecycle`)

State machine management with explicit transitions:
- `POST /transition/{entity_type}` - Execute state transition
- `GET /state/{entity_type}/{entity_id}` - Get current state
- `GET /history/{entity_type}/{entity_id}` - Get transition history

**Allowed Transitions:**
- **Mission:** PENDING → PLANNING → PLANNED → EXECUTING → COMPLETED/FAILED/TIMEOUT/CANCELLED
- **Job:** PENDING → QUEUED → RUNNING → SUCCEEDED/FAILED/TIMEOUT/CANCELLED
- **Attempt:** PENDING → RUNNING → SUCCEEDED/FAILED/TIMEOUT/ORPHAN_KILLED

### 3. Audit Module (`/api/neurorail/v1/audit`)

Immutable audit logging with EventStream integration:
- `POST /log` - Log audit event (append-only)
- `GET /events` - Query audit events (by mission/plan/job/attempt)
- `GET /stats` - Get audit statistics

**Dual Write:**
- PostgreSQL (durable storage)
- EventStream (real-time pub/sub)

### 4. Telemetry Module (`/api/neurorail/v1/telemetry`)

Metrics collection and Prometheus integration:
- `POST /record` - Record execution metrics
- `GET /metrics/{entity_id}` - Get metrics for entity
- `GET /snapshot` - Get real-time system snapshot

**Prometheus Metrics:**
- `neurorail_attempts_total` - Total attempts (counter)
- `neurorail_attempts_failed_total` - Failed attempts (counter)
- `neurorail_attempt_duration_ms` - Execution duration (histogram)
- `neurorail_active_missions` - Active missions (gauge)
- `neurorail_tt_first_signal_ms` - Time to first signal (histogram)

### 5. Execution Module (`/api/neurorail/v1/execution`)

Observation wrapper for job execution:
- `GET /status/{attempt_id}` - Get execution status

**Phase 1 Behavior:**
- Complete trace chain generation
- State transitions (PENDING → RUNNING → SUCCEEDED/FAILED)
- Audit logging (start/success/failure)
- Telemetry collection
- **NO budget enforcement** (timeouts/retries are logged but not enforced)

### 6. Governor Module (`/api/governor/v1`)

Mode decision and governance:
- `POST /decide` - Decide execution mode (direct vs. rail)
- `GET /stats` - Get decision statistics

**Phase 1 Rules (Hard-coded):**
1. `job_type == "llm_call"` → RAIL (token tracking required)
2. `uses_personal_data == true` → RAIL (DSGVO Art. 25)
3. `environment == "production"` → RAIL (governance required)
4. Default → DIRECT (low-risk operations)

**Shadow Evaluation:** Supports A/B testing of new manifest versions (dry-run for 24h)

## Integration Points

### Router Registration

All NeuroRail routers are registered in `backend/main.py`:

```python
# NeuroRail routers (EGR v1.0 - Phase 1: Observe-only)
from app.modules.neurorail.identity.router import router as neurorail_identity_router
from app.modules.neurorail.lifecycle.router import router as neurorail_lifecycle_router
from app.modules.neurorail.audit.router import router as neurorail_audit_router
from app.modules.neurorail.telemetry.router import router as neurorail_telemetry_router
from app.modules.neurorail.execution.router import router as neurorail_execution_router
from app.modules.governor.router import router as governor_router

# In create_app():
app.include_router(neurorail_identity_router, tags=["neurorail-identity"])
app.include_router(neurorail_lifecycle_router, tags=["neurorail-lifecycle"])
app.include_router(neurorail_audit_router, tags=["neurorail-audit"])
app.include_router(neurorail_telemetry_router, tags=["neurorail-telemetry"])
app.include_router(neurorail_execution_router, tags=["neurorail-execution"])
app.include_router(governor_router, tags=["governor"])
```

### Database Schema

NeuroRail uses 5 PostgreSQL tables (created via Alembic migration `004_neurorail_schema.py`):

1. **`neurorail_audit`** - Immutable audit log
2. **`neurorail_state_transitions`** - State machine history
3. **`governor_decisions`** - Mode decisions and budget checks
4. **`neurorail_metrics_snapshots`** - Periodic metric snapshots
5. **`governor_manifests`** - Manifest versioning

**Apply Migration:**
```bash
cd backend
alembic upgrade head
```

### Redis Keys

NeuroRail uses Redis for hot data (24h TTL):

- `neurorail:identity:mission:{mission_id}` - Mission identity
- `neurorail:identity:plan:{plan_id}` - Plan identity
- `neurorail:identity:job:{job_id}` - Job identity
- `neurorail:identity:attempt:{attempt_id}` - Attempt identity
- `neurorail:state:mission:{mission_id}` - Current mission state
- `neurorail:state:job:{job_id}` - Current job state
- `neurorail:state:attempt:{attempt_id}` - Current attempt state
- `neurorail:metrics:attempt:{attempt_id}` - Execution metrics

### EventStream Integration

Audit events are published to EventStream for real-time propagation:

```python
# Topic: neurorail.audit
# Message format:
{
  "audit_id": "aud_...",
  "mission_id": "m_...",
  "event_type": "execution_start",
  "timestamp": "2025-12-30T23:00:00Z",
  ...
}
```

## Testing

### 1. Pytest E2E Test

Comprehensive integration test covering all modules:

```bash
cd backend
pytest tests/test_neurorail_e2e.py -v -s
```

**Tests:**
- ✅ All endpoints registered
- ✅ Complete trace chain generation
- ✅ State machine transitions
- ✅ Audit logging
- ✅ Governor mode decisions
- ✅ Telemetry snapshot
- ✅ End-to-end execution flow

### 2. curl Smoke Test

Quick manual test with curl:

```bash
cd backend/tests
./test_neurorail_curl.sh
```

**Tests:**
- Health check
- Route discovery
- Trace chain creation (mission → plan → job → attempt)
- State transitions
- Audit logging
- Governor decisions
- Telemetry snapshot

### 3. Manual API Testing

Using the FastAPI auto-generated docs:

1. Start backend: `docker compose up -d backend`
2. Open: http://localhost:8000/docs
3. Navigate to NeuroRail sections:
   - `neurorail-identity`
   - `neurorail-lifecycle`
   - `neurorail-audit`
   - `neurorail-telemetry`
   - `neurorail-execution`
   - `governor`

## Configuration

### Environment Variables

NeuroRail uses existing infrastructure (no new env vars required):

- `REDIS_URL` - Redis connection (default: `redis://redis:6379/0`)
- `DATABASE_URL` - PostgreSQL connection
- `ENABLE_EVENTSTREAM` - EventStream integration (default: `true`)

### Feature Flags

Phase 1 enforcement is **disabled by default** (observation-only):

```python
# In execution/service.py:
# Phase 1: No timeout enforcement - just execute
# Phase 2: Add timeout wrapper here
result_data = await executor(**context.job_parameters)
```

Phase 2 enforcement will be enabled via feature flags in future commits.

## Monitoring

### Prometheus Metrics

NeuroRail exposes 9 Prometheus metrics at `/metrics`:

```prometheus
# Counters
neurorail_attempts_total{entity_type, status}
neurorail_attempts_failed_total{entity_type, error_category, error_code}
neurorail_budget_violations_total{violation_type}
neurorail_reflex_actions_total{action_type, entity_type}

# Gauges
neurorail_active_missions
neurorail_active_jobs
neurorail_active_attempts
neurorail_resources_by_state{resource_type, state}

# Histograms
neurorail_attempt_duration_ms{entity_type}  # [10, 50, 100, 500, 1000, 5000, 10000, 30000, 60000]
neurorail_job_duration_ms{entity_type}
neurorail_mission_duration_ms{entity_type}
neurorail_tt_first_signal_ms{entity_type}  # Time to first signal (SGLang-inspired)
```

### Health Checks

Global health: `GET /api/health`

Telemetry snapshot: `GET /api/neurorail/v1/telemetry/snapshot`

```json
{
  "timestamp": "2025-12-30T23:00:00Z",
  "entity_counts": {
    "missions": 42,
    "plans": 38,
    "jobs": 120,
    "attempts": 145
  },
  "active_executions": {
    "running_attempts": 3,
    "queued_jobs": 7
  },
  "error_rates": {
    "mechanical_errors": 0.02,
    "ethical_errors": 0.0
  }
}
```

## Error Handling

### Error Codes

NeuroRail uses structured error codes (NR-E001 to NR-E007):

| Code | Category | Retriable | Description |
|------|----------|-----------|-------------|
| NR-E001 | MECHANICAL | ✅ | Execution timeout |
| NR-E002 | MECHANICAL | ❌ | Budget exceeded |
| NR-E003 | MECHANICAL | ❌ | Retry exhausted |
| NR-E004 | MECHANICAL | ✅ | Upstream unavailable |
| NR-E005 | MECHANICAL | ✅ | Bad response format |
| NR-E006 | MECHANICAL | ❌ | Policy reflex cooldown |
| NR-E007 | SYSTEM | ❌ | Orphan killed |

### Error Propagation

Errors are:
1. Classified (mechanical vs. ethical)
2. Logged to audit trail
3. Recorded in state transitions
4. Emitted to Prometheus metrics
5. Published to EventStream

## API Examples

### Example 1: Create Trace Chain

```bash
# 1. Create mission
curl -X POST http://localhost:8000/api/neurorail/v1/identity/mission \
  -H "Content-Type: application/json" \
  -d '{"tags": {"project": "test"}}'
# Response: {"mission_id": "m_abc123def456", ...}

# 2. Create plan
curl -X POST http://localhost:8000/api/neurorail/v1/identity/plan \
  -H "Content-Type: application/json" \
  -d '{"mission_id": "m_abc123def456", "plan_type": "sequential"}'
# Response: {"plan_id": "p_xyz789uvw012", ...}

# 3. Create job
curl -X POST http://localhost:8000/api/neurorail/v1/identity/job \
  -H "Content-Type: application/json" \
  -d '{"plan_id": "p_xyz789uvw012", "job_type": "llm_call"}'
# Response: {"job_id": "j_qwe456rty789", ...}

# 4. Create attempt
curl -X POST http://localhost:8000/api/neurorail/v1/identity/attempt \
  -H "Content-Type: application/json" \
  -d '{"job_id": "j_qwe456rty789", "attempt_number": 1}'
# Response: {"attempt_id": "a_asd123fgh456", ...}
```

### Example 2: Execute with Observation

```bash
# 1. Get governor decision
curl -X POST http://localhost:8000/api/governor/v1/decide \
  -H "Content-Type: application/json" \
  -d '{"job_type": "llm_call", "context": {}}'
# Response: {"mode": "rail", "reason": "LLM calls require governance", ...}

# 2. Transition to RUNNING
curl -X POST http://localhost:8000/api/neurorail/v1/lifecycle/transition/attempt \
  -H "Content-Type: application/json" \
  -d '{"entity_id": "a_asd123fgh456", "transition": "start", "metadata": {}}'

# 3. Log audit event
curl -X POST http://localhost:8000/api/neurorail/v1/audit/log \
  -H "Content-Type: application/json" \
  -d '{
    "attempt_id": "a_asd123fgh456",
    "event_type": "execution_start",
    "event_category": "execution",
    "severity": "info",
    "message": "Starting execution"
  }'

# 4. Transition to SUCCEEDED
curl -X POST http://localhost:8000/api/neurorail/v1/lifecycle/transition/attempt \
  -H "Content-Type: application/json" \
  -d '{"entity_id": "a_asd123fgh456", "transition": "complete", "metadata": {"duration_ms": 150}}'
```

### Example 3: Query Audit Trail

```bash
# Get all events for a mission
curl "http://localhost:8000/api/neurorail/v1/audit/events?mission_id=m_abc123def456&limit=100"

# Get events for specific attempt
curl "http://localhost:8000/api/neurorail/v1/audit/events?attempt_id=a_asd123fgh456&limit=10"

# Get events by severity
curl "http://localhost:8000/api/neurorail/v1/audit/events?severity=error&limit=50"
```

## Phase 2 Roadmap

Future enhancements (not in this commit):

1. **Budget Enforcement:**
   - Timeout wrapper in execution
   - Token limit checks
   - Resource quota enforcement

2. **Reflex System:**
   - Cooldown periods
   - Probing strategies
   - Automatic suspension

3. **Manifest-Driven Governance:**
   - Replace hard-coded rules with manifest
   - Dynamic rule updates
   - Manifest versioning with A/B testing

4. **Advanced Telemetry:**
   - Per-job budget tracking
   - Cost attribution
   - Predictive resource allocation

5. **ControlDeck UI:**
   - Trace Explorer
   - Health Matrix
   - Budget Dashboard
   - Reflex Control Panel

## Troubleshooting

### Issue: Routes not registered

**Check:**
```bash
curl http://localhost:8000/debug/routes | grep neurorail
```

**Fix:** Ensure routers are imported and included in `backend/main.py`

### Issue: Database tables missing

**Check:**
```bash
cd backend
alembic current
```

**Fix:**
```bash
alembic upgrade head
```

### Issue: Redis connection errors

**Check:**
```bash
docker compose ps redis
docker compose logs redis
```

**Fix:**
```bash
docker compose restart redis
```

### Issue: EventStream not available

**Check logs:**
```bash
docker compose logs backend | grep EventStream
```

**Workaround (Dev only):**
```bash
export BRAIN_EVENTSTREAM_MODE=degraded
docker compose restart backend
```

## Support

For issues or questions:
- Check module-specific README files in `app/modules/neurorail/*/`
- Review error codes in `app/modules/neurorail/errors.py`
- Check Prometheus metrics at `/metrics`
- Review audit trail via `/api/neurorail/v1/audit/events`

## Version History

- **v1.0 (2025-12-30):** Initial integration (Phase 1: Observe-only)
  - Identity, Lifecycle, Audit, Telemetry, Execution modules
  - Governor stub with hard-coded rules
  - PostgreSQL + Redis dual storage
  - EventStream integration
  - Prometheus metrics
  - E2E tests
