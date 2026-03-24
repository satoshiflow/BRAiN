# Dependency Health Policy

**Status**: Active  
**Scope**: Backend runtime dependencies (Postgres, Redis, Qdrant, EventStream)

## Policy Matrix

| Dependency | Local/Minimal | Remote/Full | Failure Behavior |
|------------|---------------|-------------|------------------|
| **PostgreSQL** | Required | Required | Fail-fast (startup blocked) |
| **Redis** | Optional (warn) | Required | Local: degraded, Remote: fail-fast |
| **Qdrant** | Optional (warn) | Optional (warn) | Degraded mode (log warning, continue) |
| **EventStream** | Optional (`degraded` mode) | Required | Mode-dependent |

## Health Endpoints

### Liveness: `/api/health`
**Purpose**: Is the service alive?  
**Checks**: Minimal (process is responding)  
**Failure**: Service should be restarted

**Response**:
```json
{"status": "healthy"}
```

### Readiness: `/api/system/health`
**Purpose**: Is the service ready to accept traffic?  
**Checks**: Dependencies + initialization state  
**Failure**: Service should not receive traffic until ready

**Response**:
```json
{
  "status": "healthy" | "degraded" | "unhealthy",
  "dependencies": {
    "postgres": {"status": "healthy", "latency_ms": 5},
    "redis": {"status": "healthy", "latency_ms": 2},
    "qdrant": {"status": "degraded", "latency_ms": null}
  }
}
```

## Failure Modes

### Postgres Unavailable
- **Local**: Startup blocked with clear error
- **Remote**: Startup blocked, Kubernetes restarts service
- **Mitigation**: None (critical dependency)

### Redis Unavailable
- **Local**: Warning logged, EventStream disabled, Mission Worker disabled
- **Remote**: Startup blocked (required for EventStream)
- **Mitigation**: Local fallback to in-memory state (limited)

### Qdrant Unavailable
- **Local**: Warning logged, vector search disabled
- **Remote**: Warning logged, vector search disabled
- **Mitigation**: Graceful degradation (RAG features unavailable)

### EventStream Unavailable
- **Local**: `BRAIN_EVENTSTREAM_MODE=degraded` → skip initialization
- **Remote**: `BRAIN_EVENTSTREAM_MODE=required` → startup blocked
- **Mitigation**: None in remote (critical for audit/observability)

## Docker Healthcheck Strategy

### Postgres
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U brain -d brain_dev"]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 15s
```

### Redis
```yaml
healthcheck:
  test: ["CMD", "redis-cli", "ping"]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 10s
```

### Qdrant
```yaml
healthcheck:
  test: ["CMD-SHELL", "wget -q --spider http://localhost:6333/ || exit 1"]
  interval: 15s
  timeout: 10s
  retries: 8
  start_period: 30s
```

**Note**: Qdrant uses root `/` endpoint instead of `/healthz` for more reliable checks.

## Runtime Mode Behavior

### Local (`BRAIN_RUNTIME_MODE=local`, `BRAIN_STARTUP_PROFILE=minimal`)
- Postgres: required
- Redis: optional (warn if unavailable)
- Qdrant: optional (warn if unavailable)
- EventStream: `degraded` by default
- Mission Worker: disabled by default

### Remote (`BRAIN_RUNTIME_MODE=remote`, `BRAIN_STARTUP_PROFILE=full`)
- Postgres: required
- Redis: required
- Qdrant: optional (warn if unavailable)
- EventStream: `required` by default
- Mission Worker: enabled by default

## Monitoring Recommendations

### Alerts (Production)
1. **Critical**: Postgres unavailable > 30s
2. **Critical**: Redis unavailable > 30s
3. **Warning**: Qdrant unavailable > 5min
4. **Warning**: Degraded health status > 10min

### Metrics
- Dependency latency (p50, p95, p99)
- Health check success rate
- Degraded mode duration
- Startup time per dependency

## References
- Runtime Contract: `docs/specs/runtime_deployment_contract.md`
- Health System: `docs/specs/canonical_health_model.md`
- Docker Compose: `docker-compose.dev.yml`
