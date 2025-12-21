# BRAiN Developer Tools

**Version:** 1.0.0
**Created:** 2025-12-20
**Phase:** 5 - Developer Experience & Advanced Features

## Overview

The BRAiN Developer Tools module provides comprehensive utilities for enhanced developer experience:

- **TypeScript API Client Generation** - Auto-generate type-safe API clients from OpenAPI schema
- **Test Data Generation** - Create realistic test data for development and testing
- **Performance Profiling** - Monitor and analyze API endpoint and database performance
- **API Documentation** - Enhanced OpenAPI schema with examples and metadata

## Table of Contents

1. [API Client Generator](#api-client-generator)
2. [Test Data Generator](#test-data-generator)
3. [Performance Profiler](#performance-profiler)
4. [API Endpoints](#api-endpoints)
5. [Usage Examples](#usage-examples)
6. [Best Practices](#best-practices)

---

## API Client Generator

### Overview

Automatically generates type-safe TypeScript API clients from your OpenAPI schema. The generator creates:

- **types.ts** - TypeScript interfaces from Pydantic models
- **api.ts** - API client class with typed methods
- **index.ts** - Barrel export file

### Features

- ✅ Full OpenAPI 3.0 support
- ✅ Pydantic model to TypeScript type conversion
- ✅ Request/response type mapping
- ✅ Automatic URL encoding and parameter handling
- ✅ Support for query parameters, path parameters, and request bodies
- ✅ Proper handling of optional vs required fields
- ✅ Array and nested object types

### Type Conversion

| OpenAPI Type | TypeScript Type |
|--------------|-----------------|
| `string` | `string` |
| `integer` | `number` |
| `number` | `number` |
| `boolean` | `boolean` |
| `array` | `Array<T>` |
| `object` | `{ [key: string]: any }` or interface |
| `$ref` | Interface reference |
| `enum` | Union type |

### Generated Client Structure

```typescript
// types.ts
export interface Mission {
  id: string;
  name: string;
  description: string;
  status: "pending" | "queued" | "running" | "completed" | "failed";
  priority: "LOW" | "NORMAL" | "HIGH" | "CRITICAL";
  payload: { [key: string]: any };
  created_at: number;
  updated_at: number;
}

export interface MissionEnqueuePayload {
  name: string;
  description: string;
  priority: "LOW" | "NORMAL" | "HIGH" | "CRITICAL";
  payload: { [key: string]: any };
  max_retries?: number;
}

// api.ts
export class BrainApiClient {
  constructor(private baseUrl: string = "http://localhost:8000") {}

  async enqueueMission(payload: MissionEnqueuePayload): Promise<Mission> {
    const response = await fetch(`${this.baseUrl}/api/missions/enqueue`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return response.json();
  }

  async getMissionQueue(): Promise<Array<Mission>> {
    const response = await fetch(`${this.baseUrl}/api/missions/queue`);
    return response.json();
  }
}

// index.ts
export * from "./types";
export * from "./api";
```

### Usage

**Python (Programmatic):**

```python
from pathlib import Path
from fastapi.openapi.utils import get_openapi
from backend.app.dev_tools import generate_typescript_client
from main import app

# Get OpenAPI schema
openapi_schema = get_openapi(
    title=app.title,
    version=app.version,
    description=app.description,
    routes=app.routes,
)

# Generate client
output_path = Path("frontend/generated")
generate_typescript_client(openapi_schema, output_path)

print(f"Generated TypeScript client in {output_path}")
```

**REST API:**

```bash
# Generate TypeScript client
curl -X POST http://localhost:8000/api/dev/generate-client \
  -H "Content-Type: application/json" \
  -d '{
    "format": "typescript",
    "output_path": "frontend/generated"
  }'

# Response
{
  "status": "generated",
  "format": "typescript",
  "output_path": "frontend/generated",
  "files": [
    "frontend/generated/types.ts",
    "frontend/generated/api.ts",
    "frontend/generated/index.ts"
  ]
}
```

**Frontend Integration:**

```typescript
import { BrainApiClient } from "@/generated";

const client = new BrainApiClient("http://localhost:8000");

// Type-safe API calls
const mission = await client.enqueueMission({
  name: "Deploy Application",
  description: "Deploy to production",
  priority: "HIGH",
  payload: { environment: "production" }
});

console.log(`Mission ${mission.id} enqueued with status ${mission.status}`);
```

---

## Test Data Generator

### Overview

Generate realistic test data for development, testing, and demos. Supports multiple entity types with proper relationships and realistic patterns.

### Supported Data Types

- **Missions** - Mission queue entries with varied statuses and priorities
- **Agents** - Agent instances with capabilities and states
- **Users** - User accounts with roles and metadata
- **Audit Logs** - Audit trail entries with actions and timestamps
- **Tasks** - Background tasks with execution history
- **Metrics** - Performance and system metrics

### Features

- ✅ Realistic data patterns (timestamps, IDs, names)
- ✅ Configurable quantity per entity type
- ✅ Proper relationships between entities
- ✅ Varied statuses and priorities
- ✅ Random but consistent data
- ✅ Support for overrides and customization

### Mission Data Structure

```python
{
    "id": "mission_f47ac10b",
    "name": "Test Mission 7482",
    "description": "Automated test mission for development",
    "status": "pending",  # pending, queued, running, completed, failed
    "priority": "NORMAL",  # LOW, NORMAL, HIGH, CRITICAL
    "mission_type": "deployment",  # general, code_review, deployment, etc.
    "payload": {"key": "value"},
    "created_at": "2025-12-20T10:30:00",
    "updated_at": "2025-12-20T10:30:00",
    "max_retries": 3,
    "retry_count": 0,
}
```

### Agent Data Structure

```python
{
    "id": "agent_abc123",
    "name": "Ops Specialist",
    "type": "ops_specialist",
    "status": "idle",  # idle, busy, offline, error
    "capabilities": ["deployment", "monitoring", "scaling"],
    "current_task": None,
    "last_heartbeat": "2025-12-20T10:30:00",
}
```

### Usage

**Python (Programmatic):**

```python
from backend.app.dev_tools import (
    generate_missions,
    generate_agents,
    generate_users,
    generate_test_dataset,
)

# Generate specific types
missions = generate_missions(count=50)
agents = generate_agents(count=10)
users = generate_users(count=20)

# Generate complete dataset
dataset = generate_test_dataset()
# Returns: {"missions": [...], "agents": [...], "users": [...], "audit_logs": [...]}

# Generate with custom status
completed_missions = generate_missions(count=10, status="completed")
failed_missions = generate_missions(count=5, status="failed", priority="HIGH")

# Generate single entity with overrides
mission = generate_mission(
    name="Custom Mission",
    description="Special test case",
    priority="CRITICAL",
    payload={"custom_field": "value"}
)
```

**REST API:**

```bash
# Generate test data
curl -X POST http://localhost:8000/api/dev/test-data \
  -H "Content-Type: application/json" \
  -d '{
    "missions": 50,
    "agents": 10,
    "users": 20,
    "audit_logs": 100,
    "tasks": 30
  }'

# Response
{
  "status": "generated",
  "counts": {
    "missions": 50,
    "agents": 10,
    "users": 20,
    "audit_logs": 100,
    "tasks": 30
  },
  "data": {
    "missions": [...],
    "agents": [...],
    "users": [...],
    "audit_logs": [...],
    "tasks": [...]
  }
}
```

**Seeding Database:**

```python
from backend.app.dev_tools import generate_test_dataset
from backend.app.modules.missions.service import MissionService

# Generate test data
dataset = generate_test_dataset()

# Seed database
mission_service = MissionService()

for mission_data in dataset["missions"]:
    await mission_service.create_mission(mission_data)

print(f"Seeded {len(dataset['missions'])} missions")
```

---

## Performance Profiler

### Overview

Comprehensive performance profiling and monitoring system for API endpoints and database queries. Tracks request timing, identifies slow operations, and provides statistical analysis.

### Features

- ✅ Endpoint request timing with percentiles
- ✅ Slow request detection and logging
- ✅ Database query profiling
- ✅ Memory usage tracking
- ✅ Statistical analysis (avg, p50, p95, p99)
- ✅ Non-invasive decorator-based profiling
- ✅ Configurable slow request thresholds

### Metrics Tracked

**Request Metrics:**
- Request count per endpoint
- Average response time
- Percentiles (p50, p95, p99)
- Slow request detection (>1000ms default)
- Request method and path
- Timestamp tracking

**Database Metrics:**
- Query execution time
- Query text and parameters
- Slow query detection
- Total queries executed
- Query frequency analysis

**System Metrics:**
- Memory usage (current, peak)
- CPU utilization
- Active connections
- Thread pool status

### Performance Report Structure

```python
{
    "endpoints": {
        "GET /api/missions/queue": {
            "count": 152,
            "avg_ms": 45.3,
            "p50_ms": 38.2,
            "p95_ms": 89.5,
            "p99_ms": 156.8,
            "min_ms": 12.3,
            "max_ms": 234.5
        },
        "POST /api/missions/enqueue": {
            "count": 48,
            "avg_ms": 123.7,
            "p50_ms": 105.2,
            "p95_ms": 245.8,
            "p99_ms": 389.2
        }
    },
    "slow_requests": [
        {
            "endpoint": "GET /api/missions/events/history",
            "method": "GET",
            "duration_ms": 1523.4,
            "timestamp": 1703001234.56
        }
    ],
    "database": {
        "total_queries": 456,
        "avg_query_time_ms": 23.5,
        "slow_queries_count": 3
    },
    "slow_queries": [
        {
            "query": "SELECT * FROM missions WHERE status = ? ORDER BY created_at DESC",
            "duration_ms": 1234.5,
            "timestamp": 1703001234.56
        }
    ],
    "timestamp": 1703001234.56
}
```

### Usage

**Python (Decorator):**

```python
from backend.app.dev_tools import profile_endpoint

@profile_endpoint
async def expensive_operation():
    """This endpoint will be automatically profiled."""
    # ... operation logic
    return result

# Profiling is automatic - metrics are collected in background
```

**Python (Manual):**

```python
from backend.app.dev_tools import get_metrics, get_db_profiler

# Get current metrics
metrics = get_metrics()
stats = metrics.get_stats("GET /api/missions/queue")

print(f"Average response time: {stats['avg_ms']}ms")
print(f"95th percentile: {stats['p95_ms']}ms")

# Get slow requests
slow_requests = metrics.get_slow_requests(limit=10)
for req in slow_requests:
    print(f"{req['endpoint']}: {req['duration_ms']}ms")

# Reset metrics
metrics.reset()

# Database profiling
db_profiler = get_db_profiler()
slow_queries = db_profiler.get_slow_queries(limit=5)
```

**REST API:**

```bash
# Get performance report
curl http://localhost:8000/api/dev/performance

# Get specific endpoint stats
curl http://localhost:8000/api/dev/performance/endpoints/GET%20%2Fapi%2Fmissions%2Fqueue

# Reset metrics
curl -X POST http://localhost:8000/api/dev/performance/reset
```

**Frontend Dashboard Integration:**

```typescript
import { useQuery } from "@tanstack/react-query";

export function PerformanceDashboard() {
  const { data: report } = useQuery({
    queryKey: ["performance", "report"],
    queryFn: () => fetch("/api/dev/performance").then(r => r.json()),
    refetchInterval: 10_000,  // Refresh every 10s
  });

  return (
    <div>
      <h2>Performance Overview</h2>
      {Object.entries(report?.endpoints || {}).map(([endpoint, stats]) => (
        <div key={endpoint}>
          <h3>{endpoint}</h3>
          <p>Requests: {stats.count}</p>
          <p>Average: {stats.avg_ms.toFixed(2)}ms</p>
          <p>95th percentile: {stats.p95_ms.toFixed(2)}ms</p>
        </div>
      ))}

      <h2>Slow Requests</h2>
      {report?.slow_requests.map(req => (
        <div key={req.timestamp}>
          {req.endpoint}: {req.duration_ms.toFixed(2)}ms
        </div>
      ))}
    </div>
  );
}
```

---

## API Endpoints

### Generate Client

**POST /api/dev/generate-client**

Generate TypeScript API client from OpenAPI schema.

**Permissions:** Admin only

**Request Body:**
```json
{
  "format": "typescript",
  "output_path": "frontend/generated"
}
```

**Response:**
```json
{
  "status": "generated",
  "format": "typescript",
  "output_path": "frontend/generated",
  "files": [
    "frontend/generated/types.ts",
    "frontend/generated/api.ts",
    "frontend/generated/index.ts"
  ]
}
```

### Generate Test Data

**POST /api/dev/test-data**

Generate test data for development and testing.

**Permissions:** Admin only

**Request Body:**
```json
{
  "missions": 50,
  "agents": 10,
  "users": 20,
  "audit_logs": 100,
  "tasks": 30
}
```

**Constraints:**
- `missions`: 1-1000
- `agents`: 1-100
- `users`: 1-100
- `audit_logs`: 1-10000
- `tasks`: 1-1000

**Response:**
```json
{
  "status": "generated",
  "counts": {
    "missions": 50,
    "agents": 10,
    "users": 20,
    "audit_logs": 100,
    "tasks": 30
  },
  "data": {
    "missions": [...],
    "agents": [...],
    "users": [...],
    "audit_logs": [...],
    "tasks": [...]
  }
}
```

### Performance Report

**GET /api/dev/performance**

Get comprehensive performance profiling report.

**Permissions:** Admin only

**Response:**
```json
{
  "endpoints": {
    "GET /api/missions/queue": {
      "count": 152,
      "avg_ms": 45.3,
      "p50_ms": 38.2,
      "p95_ms": 89.5,
      "p99_ms": 156.8
    }
  },
  "slow_requests": [...],
  "database": {
    "total_queries": 456,
    "avg_query_time_ms": 23.5
  },
  "slow_queries": [...],
  "timestamp": 1703001234.56
}
```

### Reset Performance Metrics

**POST /api/dev/performance/reset**

Reset all performance profiling metrics.

**Permissions:** Admin only

**Response:** 204 No Content

### Endpoint Performance

**GET /api/dev/performance/endpoints/{endpoint}**

Get performance statistics for specific endpoint.

**Permissions:** Admin only

**Parameters:**
- `endpoint` (path): Endpoint path (e.g., "GET /api/missions")

**Response:**
```json
{
  "count": 152,
  "avg_ms": 45.3,
  "p50_ms": 38.2,
  "p95_ms": 89.5,
  "p99_ms": 156.8,
  "min_ms": 12.3,
  "max_ms": 234.5
}
```

### Get OpenAPI Schema

**GET /api/dev/schema**

Get enhanced OpenAPI 3.0 schema.

**Permissions:** Public

**Response:**
```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "BRAiN API",
    "version": "0.5.0"
  },
  "paths": {...},
  "components": {...}
}
```

### Download OpenAPI Schema

**GET /api/dev/schema/download?format=json**

Download OpenAPI schema file.

**Permissions:** Public

**Parameters:**
- `format` (query): File format ("json" or "yaml")

**Response:** File download (application/json or application/x-yaml)

### Developer Tools Info

**GET /api/dev/info**

Get developer tools information and capabilities.

**Permissions:** Public

**Response:**
```json
{
  "name": "BRAiN Developer Tools",
  "version": "1.0.0",
  "tools": {
    "api_client_generator": {
      "description": "Generate TypeScript API client from OpenAPI schema",
      "formats": ["typescript"],
      "endpoint": "POST /api/dev/generate-client"
    },
    "test_data_generator": {
      "description": "Generate realistic test data for development",
      "types": ["missions", "agents", "users", "audit_logs", "tasks"],
      "endpoint": "POST /api/dev/test-data"
    },
    "performance_profiler": {
      "description": "Profile API endpoint and database performance",
      "features": ["endpoint_timing", "slow_requests", "db_queries"],
      "endpoint": "GET /api/dev/performance"
    },
    "openapi_schema": {
      "description": "Enhanced OpenAPI 3.0 schema",
      "formats": ["json", "yaml"],
      "endpoint": "GET /api/dev/schema"
    }
  }
}
```

---

## Usage Examples

### Example 1: Frontend Development Workflow

```bash
# 1. Generate TypeScript client from latest API schema
curl -X POST http://localhost:8000/api/dev/generate-client \
  -H "Content-Type: application/json" \
  -d '{"format": "typescript", "output_path": "frontend/generated"}'

# 2. Generate test data for UI development
curl -X POST http://localhost:8000/api/dev/test-data \
  -H "Content-Type: application/json" \
  -d '{"missions": 20, "agents": 5, "users": 10}'

# 3. Use generated client in frontend
# frontend/src/app/page.tsx
import { BrainApiClient } from "@/generated";

const client = new BrainApiClient();
const missions = await client.getMissionQueue();
```

### Example 2: Performance Monitoring

```python
from backend.app.dev_tools import profile_endpoint, get_metrics

# Profile endpoint
@profile_endpoint
async def get_mission_analytics():
    # Expensive operation
    return await calculate_analytics()

# Check performance after some requests
metrics = get_metrics()
stats = metrics.get_stats("GET /api/missions/analytics")

if stats["p95_ms"] > 1000:
    print(f"⚠️ Endpoint is slow! p95: {stats['p95_ms']}ms")

    # Get slow requests for debugging
    slow = metrics.get_slow_requests(endpoint="GET /api/missions/analytics")
    for req in slow:
        print(f"  {req['timestamp']}: {req['duration_ms']}ms")
```

### Example 3: Automated Testing Setup

```python
import pytest
from backend.app.dev_tools import generate_test_dataset
from backend.app.modules.missions.service import MissionService

@pytest.fixture
async def test_data():
    """Generate test data for test suite."""
    return generate_test_dataset()

@pytest.mark.asyncio
async def test_mission_processing(test_data):
    """Test mission processing with generated data."""
    service = MissionService()

    for mission_data in test_data["missions"][:10]:
        mission = await service.create_mission(mission_data)
        assert mission.id is not None
        assert mission.status == "pending"
```

### Example 4: Performance Dashboard

```typescript
// Performance monitoring dashboard component
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function PerformanceMonitor() {
  const { data: report, isLoading } = useQuery({
    queryKey: ["dev", "performance"],
    queryFn: () => fetch("/api/dev/performance").then(r => r.json()),
    refetchInterval: 15_000,
  });

  if (isLoading) return <div>Loading...</div>;

  const slowEndpoints = Object.entries(report.endpoints)
    .filter(([_, stats]) => stats.p95_ms > 500)
    .sort((a, b) => b[1].p95_ms - a[1].p95_ms);

  return (
    <div className="grid gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Slow Endpoints (p95 &gt; 500ms)</CardTitle>
        </CardHeader>
        <CardContent>
          {slowEndpoints.map(([endpoint, stats]) => (
            <div key={endpoint} className="flex justify-between mb-2">
              <span>{endpoint}</span>
              <span className="text-red-500">{stats.p95_ms.toFixed(0)}ms</span>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Recent Slow Requests</CardTitle>
        </CardHeader>
        <CardContent>
          {report.slow_requests.slice(0, 5).map(req => (
            <div key={req.timestamp} className="mb-2">
              <div className="font-mono text-sm">{req.endpoint}</div>
              <div className="text-xs text-muted-foreground">
                {req.duration_ms.toFixed(0)}ms at {new Date(req.timestamp * 1000).toLocaleTimeString()}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
```

### Example 5: CI/CD Integration

```yaml
# .github/workflows/api-client.yml
name: Generate API Client

on:
  push:
    branches: [main, develop]
    paths:
      - 'backend/app/api/**'
      - 'backend/app/modules/**'

jobs:
  generate-client:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Start Backend
        run: docker compose up -d backend

      - name: Generate TypeScript Client
        run: |
          curl -X POST http://localhost:8000/api/dev/generate-client \
            -H "Content-Type: application/json" \
            -d '{"format": "typescript", "output_path": "frontend/generated"}'

      - name: Commit Generated Client
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add frontend/generated/
          git commit -m "chore: regenerate API client" || exit 0
          git push
```

---

## Best Practices

### API Client Generation

1. **Regenerate on API Changes**
   - Regenerate client whenever API endpoints change
   - Include in CI/CD pipeline for automated updates
   - Version generated client alongside API version

2. **Type Safety**
   - Always use generated types in frontend code
   - Never bypass type checking with `any` types
   - Leverage TypeScript's strict mode

3. **Output Location**
   - Keep generated code in separate directory (`frontend/generated`)
   - Add to `.gitignore` if regenerating in CI
   - Document generation process in README

### Test Data Generation

1. **Realistic Patterns**
   - Use varied but realistic data patterns
   - Include edge cases (empty arrays, null values)
   - Maintain referential integrity

2. **Quantity Management**
   - Start with small datasets for unit tests
   - Use larger datasets for integration tests
   - Avoid overwhelming database with too much data

3. **Data Cleanup**
   - Clean up test data after tests complete
   - Use transactions for test isolation
   - Implement teardown procedures

### Performance Profiling

1. **Monitoring Strategy**
   - Enable profiling in development and staging
   - Monitor p95/p99 metrics, not just averages
   - Set alerts for performance degradation

2. **Threshold Configuration**
   - Adjust slow request threshold based on SLA
   - Different thresholds for different endpoints
   - Consider user experience expectations

3. **Performance Budget**
   - Set performance budgets for critical endpoints
   - Track trends over time
   - Investigate sudden performance changes

4. **Production Profiling**
   - Use sampling in production to reduce overhead
   - Profile representative traffic, not all requests
   - Balance observability with performance impact

### General Guidelines

1. **Admin-Only Features**
   - Developer tools expose sensitive information
   - Always require admin authentication
   - Disable in production if not needed

2. **Rate Limiting**
   - Consider rate limiting for expensive operations
   - Prevent abuse of data generation endpoints
   - Protect against DoS via profiling endpoints

3. **Documentation**
   - Keep API documentation up to date
   - Document generated client usage patterns
   - Provide examples for common use cases

4. **Integration**
   - Integrate with monitoring systems (Grafana, Datadog)
   - Export metrics in standard formats (Prometheus)
   - Connect with alerting systems

---

## Configuration

### Environment Variables

```bash
# Developer Tools
DEV_TOOLS_ENABLED=true
DEV_TOOLS_OUTPUT_PATH=frontend/generated

# Performance Profiling
PROFILER_ENABLED=true
PROFILER_SLOW_REQUEST_THRESHOLD_MS=1000
PROFILER_SAMPLE_RATE=1.0  # 1.0 = 100%, 0.1 = 10%

# Test Data
TEST_DATA_DEFAULT_COUNT=50
TEST_DATA_MAX_COUNT=10000
```

### Programmatic Configuration

```python
from backend.app.dev_tools import get_metrics

# Configure performance metrics
metrics = get_metrics()
metrics.slow_threshold_ms = 500.0  # Lower threshold

# Configure sampling (for production)
metrics.sample_rate = 0.1  # Profile 10% of requests
```

---

## Troubleshooting

### Issue: Generated Client Has Type Errors

**Solution:**
- Ensure OpenAPI schema is valid
- Check Pydantic models have proper type hints
- Regenerate client after fixing models
- Run TypeScript compiler to identify issues

### Issue: Test Data Generation Too Slow

**Solution:**
- Reduce quantity of generated items
- Use batch operations for database inserts
- Generate data in background tasks
- Cache commonly used test data

### Issue: Performance Metrics Show High Overhead

**Solution:**
- Reduce profiler sample rate in production
- Disable profiling for high-frequency endpoints
- Use async profiling to avoid blocking
- Monitor profiler's own performance impact

### Issue: TypeScript Client Missing Endpoints

**Solution:**
- Ensure FastAPI routes are properly registered
- Check route tags match expected values
- Verify OpenAPI schema includes all endpoints
- Regenerate client after adding routes

---

## Future Enhancements

- **Additional Client Languages** - Python, Go, Rust clients
- **Mock Server Generation** - Generate mock server from schema
- **Load Testing Tools** - Automated load testing with generated data
- **Performance Regression Detection** - Automatic detection of performance regressions
- **Schema Diffing** - Compare OpenAPI schemas across versions
- **Visual Performance Dashboard** - Real-time performance visualization
- **Database Query Optimization** - Automated query optimization suggestions

---

## Related Documentation

- [WebSocket System](WEBSOCKET.md) - Real-time communication
- [CLAUDE.md](../CLAUDE.md) - Comprehensive development guide
- [API Documentation](../README.md) - API reference
- [Frontend Development](../frontend/README.md) - Frontend integration

---

**Created:** 2025-12-20
**Last Updated:** 2025-12-20
**Version:** 1.0.0
**Phase:** 5 - Developer Experience & Advanced Features
