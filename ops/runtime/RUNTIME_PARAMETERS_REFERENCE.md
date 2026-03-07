# Runtime Parameters Reference (Local)

Purpose: central reference for runtime parameters used in local BRAiN verification.

## Network and service endpoints

- Backend API: `http://127.0.0.1:8001`
- PostgreSQL host/port: `localhost:5433`
- Redis URL: `redis://localhost:6380/0`
- Qdrant URL: `http://localhost:6334`
- Mock LLM URL: `http://localhost:8081`

## Core runtime environment variables

- `DATABASE_URL`
- `REDIS_URL`
- `QDRANT_URL`
- `ENVIRONMENT`
- `CORS_ORIGINS`
- `ENABLE_MISSION_WORKER`
- `ENABLE_METRICS_COLLECTOR`
- `ENABLE_AUTOSCALER`
- `ENABLE_BUILTIN_SKILL_SEED`
- `BRAIN_EVENTSTREAM_MODE`
- `BRAIN_AUDIT_BRIDGE_IMPLICIT_DB`
- `BRAIN_STARTUP_PROFILE` (`full` or `minimal`)
- `ENABLE_LEGACY_ROUTER_AUTODISCOVERY`
- `ENABLE_APP_ROUTER_AUTODISCOVERY`
- `ENABLE_LEGACY_SUPERVISOR_ROUTER`

## Runtime launch commands (local)

- Infra stack:
  - `docker compose --profile mock-llm -f docker-compose.dev.yml up -d`
- Backend (localhost bind):
  - `REDIS_URL=redis://localhost:6380/0 python3 -m uvicorn main:app --host 127.0.0.1 --port 8001`

## Verification commands (core)

- Health:
  - `curl http://127.0.0.1:8001/api/health`
- Postgres connectivity:
  - `python3` with `asyncpg.connect(... host='localhost', port=5433 ...)`
- Redis ping:
  - `redis-cli -h localhost -p 6380 ping`
- Qdrant:
  - `curl http://localhost:6334/healthz`
  - `curl http://localhost:6334/collections`
