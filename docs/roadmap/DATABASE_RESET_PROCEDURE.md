# Database Reset Procedure

## Overview

This document describes the procedure for resetting the BRAiN database and fixing common migration issues. This was developed during ControlDeck v3 setup.

## Problem Statement

The alembic migration system had multiple issues:
- Multiple heads due to parallel migration branches
- Broken merge files causing KeyError
- Enum case mismatch (database: lowercase, Python: uppercase)
- UUID serialization issues in SSE streams

## Prerequisites

- Docker and Docker Compose installed
- Access to PostgreSQL container
- Backend container available

## Step-by-Step Procedure

### Step 1: Stop All Services

```bash
docker compose -f docker-compose.local.yml --env-file .env.local down
```

### Step 2: Reset Database Schema

Connect to PostgreSQL and drop the public schema:

```bash
docker exec brain-postgres psql -U brain -d brain -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
```

Recreate the alembic_version table:

```bash
docker exec brain-postgres psql -U brain -d brain -c "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL);"
```

### Step 3: Create Health Monitor Tables

**Important**: Use uppercase enum values to match Python model.

Create the enum type:

```bash
docker exec brain-postgres psql -U brain -d brain -c "
DO
\$\$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'healthstatus') THEN
        CREATE TYPE healthstatus AS ENUM ('HEALTHY', 'DEGRADED', 'UNHEALTHY', 'UNKNOWN');
    END IF;
END
\$\$;
"
```

Create health_checks table:

```bash
docker exec brain-postgres psql -U brain -d brain -c "
CREATE TABLE health_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_name VARCHAR(100) NOT NULL UNIQUE,
    service_type VARCHAR(50) NOT NULL DEFAULT 'internal',
    status healthstatus NOT NULL DEFAULT 'UNKNOWN',
    previous_status healthstatus,
    status_changed_at TIMESTAMP,
    last_check_at TIMESTAMP,
    next_check_at TIMESTAMP,
    response_time_ms FLOAT,
    check_interval_seconds INTEGER NOT NULL DEFAULT 60,
    error_message TEXT,
    check_output TEXT,
    extra_data JSONB NOT NULL DEFAULT '{}',
    total_checks INTEGER NOT NULL DEFAULT 0,
    failed_checks INTEGER NOT NULL DEFAULT 0,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    consecutive_successes INTEGER NOT NULL DEFAULT 0,
    uptime_percentage FLOAT,
    last_healthy_at TIMESTAMP,
    last_failure_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
"
```

Create health_check_history table:

```bash
docker exec brain-postgres psql -U brain -d brain -c "
CREATE TABLE health_check_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_name VARCHAR(100) NOT NULL,
    status healthstatus NOT NULL,
    response_time_ms FLOAT,
    error_message TEXT,
    checked_at TIMESTAMP NOT NULL DEFAULT NOW()
);
"
```

Create indexes:

```bash
docker exec brain-postgres psql -U brain -d brain -c "
CREATE INDEX idx_health_checks_service ON health_checks (service_name);
CREATE INDEX idx_health_checks_status ON health_checks (status);
CREATE INDEX idx_health_history_service ON health_check_history (service_name);
CREATE INDEX idx_health_history_checked ON health_check_history (checked_at);
"
```

### Step 4: Create Provider Bindings Table

```bash
docker exec brain-postgres psql -U brain -d brain -c "
CREATE TABLE IF NOT EXISTS provider_bindings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(64) NULL,
    owner_scope VARCHAR(16) NOT NULL DEFAULT 'system',
    capability_id UUID NULL,
    capability_key VARCHAR(120) NOT NULL,
    capability_version INTEGER NOT NULL,
    provider_key VARCHAR(120) NOT NULL,
    provider_type VARCHAR(32) NOT NULL DEFAULT 'service',
    adapter_key VARCHAR(120) NOT NULL,
    endpoint_ref JSONB NOT NULL DEFAULT '{}',
    model_or_tool_ref VARCHAR(255) NULL,
    region VARCHAR(64) NULL,
    priority INTEGER NOT NULL DEFAULT 100,
    weight FLOAT NULL,
    cost_profile JSONB NOT NULL DEFAULT '{}',
    sla_profile JSONB NOT NULL DEFAULT '{}',
    policy_constraints JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    valid_from TIMESTAMP WITH TIME ZONE NULL,
    valid_to TIMESTAMP WITH TIME ZONE NULL,
    config JSONB NOT NULL DEFAULT '{}',
    definition_artifact_refs JSONB NOT NULL DEFAULT '[]',
    evidence_artifact_refs JSONB NOT NULL DEFAULT '[]',
    created_by VARCHAR(120) NOT NULL,
    updated_by VARCHAR(120) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
"

docker exec brain-postgres psql -U brain -d brain -c "
CREATE INDEX IF NOT EXISTS ix_provider_bindings_capability_status_priority ON provider_bindings (capability_key, capability_version, status, priority);
"
```

### Step 5: Register Initial Health Check Services

```bash
docker exec brain-postgres psql -U brain -d brain -c "
INSERT INTO health_checks (service_name, service_type, status, extra_data, check_interval_seconds)
VALUES 
('backend-api', 'internal', 'HEALTHY', '{\"version\": \"0.3.0\"}', 30),
('postgres-database', 'database', 'HEALTHY', '{\"host\": \"postgres\", \"port\": 5432}', 60),
('redis-cache', 'cache', 'HEALTHY', '{\"host\": \"redis\", \"port\": 6379}', 30),
('qdrant-vector', 'internal', 'HEALTHY', '{\"host\": \"qdrant\", \"port\": 6333}', 45),
('mock-llm', 'external', 'HEALTHY', '{\"probe_url\": \"http://host.docker.internal:8099/health\"}', 60)
ON CONFLICT (service_name) DO UPDATE SET
    status = EXCLUDED.status,
    extra_data = EXCLUDED.extra_data,
    check_interval_seconds = EXCLUDED.check_interval_seconds,
    updated_at = NOW();
"
```

### Step 6: Fix UUID Serialization in SSE Stream

The health monitor router uses `model_dump()` which doesn't serialize UUIDs properly. Change to `model_dump(mode='json')`:

**File**: `backend/app/modules/health_monitor/router.py`

```python
# Before:
yield f"data: {json.dumps(status_data.model_dump())}\n\n"

# After:
yield f"data: {json.dumps(status_data.model_dump(mode='json'))}\n\n"
```

Similarly for immune orchestrator:

**File**: `backend/app/modules/immune_orchestrator/router.py`

```python
# Before:
payload = {
    "audit": [item.model_dump() for item in audit.items[:10]],
    "decisions": [item.model_dump() for item in decisions.items[:10]],
}

# After:
payload = {
    "audit": [item.model_dump(mode='json') for item in audit.items[:10]],
    "decisions": [item.model_dump(mode='json') for item in decisions.items[:10]],
}
```

### Step 7: Start All Services

```bash
docker compose -f docker-compose.local.yml --env-file .env.local up -d
```

### Step 8: Verify Services

Test backend:

```bash
curl -s http://127.0.0.1:8000/
# Expected: {"name":"BRAiN Core Backend","version":"0.3.0",...}
```

Test health stream:

```bash
curl -sN http://127.0.0.1:8000/api/health/stream
# Expected: SSE data with JSON containing health status
```

Test ControlDeck v3:

```bash
curl -s http://127.0.0.1:3003/dashboard
# Expected: HTML page loads
```

## Troubleshooting

### Port Already in Use

If port 3003 is already in use:

```bash
# Find and kill the process
lsof -i :3003
kill <PID>
docker start controldeck-v3
```

### Enum Case Mismatch

If you see errors like `LookupError: 'healthy' is not among the defined enum values`:

1. Check the enum values in the database:
```bash
docker exec brain-postgres psql -U brain -d brain -c "SELECT pg_enum.enumlabel FROM pg_type JOIN pg_enum ON pg_type.oid = pg_enum.enumtypid WHERE pg_type.typname = 'healthstatus';"
```

2. If values are lowercase ('healthy'), drop and recreate with uppercase:
```bash
docker exec brain-postgres psql -U brain -d brain -c "DROP TYPE IF EXISTS healthstatus;"
# Then recreate with uppercase values (Step 3)
```

### SSE Stream Not Returning Data

1. Verify health_checks table has data:
```bash
docker exec brain-postgres psql -U brain -d brain -c "SELECT * FROM health_checks;"
```

2. Check backend logs for errors:
```bash
docker logs brain-backend
```

## Quick Reference

| Service | URL |
|---------|-----|
| Backend API | http://127.0.0.1:8000 |
| Health Stream | http://127.0.0.1:8000/api/health/stream |
| Immune Stream | http://127.0.0.1:8000/api/immune-orchestrator/stream |
| AXE UI | http://127.0.0.1:3002 |
| ControlDeck v3 | http://127.0.0.1:3003 |

## Notes

- The health monitor uses 30-second intervals for SSE streaming
- Authentication is required for `/api/health/status` but not for `/stream`
- The enum must match exactly between Python (HEALTHY) and PostgreSQL (HEALTHY)
- `model_dump(mode='json')` is required for Pydantic v2 to serialize UUIDs and datetimes correctly
