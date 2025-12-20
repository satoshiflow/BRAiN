# Database Optimization Guide for BRAiN Core

**Version:** 1.0.0
**Phase:** 3 - Scalability
**Status:** ✅ Production Ready

---

## Overview

BRAiN Core provides comprehensive database optimization tools:

- **Slow query analysis** - Identify performance bottlenecks
- **Index recommendations** - Auto-suggest missing indexes
- **Connection pool tuning** - Optimize connection usage
- **Bloat detection** - Find tables needing VACUUM
- **Query execution plans** - EXPLAIN ANALYZE support

---

## Setup

### Enable pg_stat_statements

Required for slow query analysis:

```sql
-- Connect to PostgreSQL
psql -U brain -d brain

-- Enable extension
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Configure postgresql.conf
shared_preload_libraries = 'pg_stat_statements'
pg_stat_statements.max = 10000
pg_stat_statements.track = all

-- Restart PostgreSQL
docker compose restart postgres
```

### Enable Auto-Vacuum

Ensure auto-vacuum is enabled:

```sql
-- Check autovacuum settings
SHOW autovacuum;

-- Tune autovacuum (postgresql.conf)
autovacuum = on
autovacuum_max_workers = 3
autovacuum_naptime = 1min
autovacuum_vacuum_scale_factor = 0.2
autovacuum_analyze_scale_factor = 0.1
```

---

## Slow Query Analysis

### API Endpoint

```http
GET /api/db/slow-queries?limit=10&min_duration_ms=100

Response:
[
  {
    "query": "SELECT * FROM missions WHERE...",
    "calls": 1234,
    "total_seconds": 45.67,
    "mean_seconds": 0.037,
    "max_seconds": 2.5,
    "stddev_seconds": 0.15,
    "rows": 5678
  }
]
```

### Python Usage

```python
from app.core.db_optimization import QueryAnalyzer
from app.core.db import engine

analyzer = QueryAnalyzer(engine)

# Get slow queries
slow_queries = await analyzer.get_slow_queries(
    limit=10,
    min_duration_ms=100  # 100ms threshold
)

for query in slow_queries:
    print(f"Query: {query['query']}")
    print(f"Mean time: {query['mean_seconds']}s")
    print(f"Calls: {query['calls']}")
```

### Optimization Workflow

1. **Identify Slow Queries**
   ```bash
   curl http://localhost:8000/api/db/slow-queries?limit=20
   ```

2. **Analyze with EXPLAIN**
   ```bash
   curl -X POST http://localhost:8000/api/db/explain \
     -H "Content-Type: application/json" \
     -d '{"query": "SELECT * FROM missions WHERE status = '\''pending'\''", "analyze": true}'
   ```

3. **Add Index**
   ```sql
   CREATE INDEX idx_missions_status ON missions(status);
   ```

4. **Verify Improvement**
   ```bash
   # Check query plan again
   curl -X POST http://localhost:8000/api/db/explain \
     -d '{"query": "SELECT * FROM missions WHERE status = '\''pending'\''", "analyze": true}'
   ```

---

## Index Recommendations

### API Endpoint

```http
GET /api/db/index-recommendations

Response:
[
  {
    "type": "high_sequential_scans",
    "schema": "public",
    "table": "missions",
    "seq_scans": 15234,
    "seq_tuples_read": 1523400,
    "index_scans": 123,
    "avg_tuples_per_scan": 100.0,
    "recommendation": "Consider adding indexes to table public.missions",
    "priority": "high"
  }
]
```

### Common Index Patterns

#### Single-Column Index

```sql
-- Frequent WHERE clause
SELECT * FROM missions WHERE status = 'pending';

-- Add index
CREATE INDEX idx_missions_status ON missions(status);
```

#### Multi-Column Index

```sql
-- Frequent WHERE with multiple columns
SELECT * FROM missions WHERE status = 'pending' AND priority = 'high';

-- Add composite index (order matters!)
CREATE INDEX idx_missions_status_priority ON missions(status, priority);
```

#### Partial Index

```sql
-- Filter only specific rows
SELECT * FROM missions WHERE status = 'pending';

-- Partial index (smaller, faster)
CREATE INDEX idx_missions_pending ON missions(id) WHERE status = 'pending';
```

#### JSONB Index

```sql
-- Query JSONB column
SELECT * FROM missions WHERE payload->>'key' = 'value';

-- GIN index for JSONB
CREATE INDEX idx_missions_payload ON missions USING GIN (payload);
```

### Index Maintenance

```sql
-- Rebuild index (removes bloat)
REINDEX INDEX idx_missions_status;

-- Rebuild all indexes on table
REINDEX TABLE missions;

-- Drop unused index
DROP INDEX idx_missions_old;
```

---

## Query Optimization

### EXPLAIN ANALYZE

```sql
EXPLAIN ANALYZE
SELECT m.id, m.name, a.name as agent_name
FROM missions m
JOIN agents a ON m.agent_id = a.id
WHERE m.status = 'running';

-- Output:
Hash Join  (cost=10.00..20.00 rows=100 width=64) (actual time=0.123..0.456 rows=95 loops=1)
  Hash Cond: (m.agent_id = a.id)
  ->  Seq Scan on missions m  (cost=0.00..8.00 rows=100 width=32) (actual time=0.010..0.050 rows=100 loops=1)
        Filter: (status = 'running')
  ->  Hash  (cost=5.00..5.00 rows=400 width=32) (actual time=0.100..0.100 rows=400 loops=1)
        ->  Seq Scan on agents a  (cost=0.00..5.00 rows=400 width=32)
Planning Time: 0.123 ms
Execution Time: 0.567 ms
```

**Key Metrics:**
- **cost**: Estimated cost (lower is better)
- **rows**: Estimated rows (accuracy matters)
- **actual time**: Real execution time
- **loops**: Number of iterations

**Red Flags:**
- `Seq Scan` on large tables
- High `actual time` vs `cost`
- Inaccurate row estimates
- Many `loops`

### Optimization Techniques

#### 1. Use Specific Columns

```sql
-- ❌ BAD
SELECT * FROM missions;

-- ✅ GOOD
SELECT id, name, status FROM missions;
```

#### 2. Add WHERE Clauses

```sql
-- ❌ BAD
SELECT * FROM missions;

-- ✅ GOOD
SELECT * FROM missions WHERE created_at > NOW() - INTERVAL '7 days';
```

#### 3. Use JOINs Instead of Subqueries

```sql
-- ❌ BAD
SELECT * FROM missions WHERE agent_id IN (
  SELECT id FROM agents WHERE status = 'active'
);

-- ✅ GOOD
SELECT m.* FROM missions m
JOIN agents a ON m.agent_id = a.id
WHERE a.status = 'active';
```

#### 4. Use LIMIT

```sql
-- ❌ BAD
SELECT * FROM missions ORDER BY created_at DESC;

-- ✅ GOOD
SELECT * FROM missions ORDER BY created_at DESC LIMIT 100;
```

#### 5. Avoid OR in WHERE

```sql
-- ❌ BAD
SELECT * FROM missions WHERE status = 'pending' OR status = 'running';

-- ✅ GOOD
SELECT * FROM missions WHERE status IN ('pending', 'running');
```

---

## Connection Pool Optimization

### Pool Statistics

```http
GET /api/db/pool-stats

Response:
{
  "pool_size": 20,
  "checked_out": 12,
  "overflow": 2,
  "checked_in": 8,
  "total_connections": 22
}
```

### Pool Recommendation

```http
GET /api/db/pool-recommendation

Response:
{
  "current_pool_size": 20,
  "recommended_pool_size": 30,
  "utilization_percentage": 80.5,
  "recommendation": "increase",
  "reason": "High utilization (80.5%), increase pool size",
  "overflow_used": true
}
```

### Tuning Pool Size

Update `backend/app/core/db.py`:

```python
engine = create_async_engine(
    settings.db_url,
    poolclass=QueuePool,
    pool_size=30,        # Recommended size
    max_overflow=15,     # Allow bursts
    pool_timeout=30,
    pool_recycle=3600,
    pool_pre_ping=True,
)
```

**Formula:**
```
optimal_pool_size = (avg_concurrent_requests * avg_query_time_seconds) + buffer

Example:
- 100 concurrent requests
- 0.05s average query time
- 10 buffer

pool_size = (100 * 0.05) + 10 = 15
```

---

## Table Bloat Detection

### Bloat Statistics

```http
GET /api/db/bloat-stats

Response:
[
  {
    "schema": "public",
    "table": "missions",
    "total_size": "125 MB",
    "dead_tuples": 12345,
    "live_tuples": 50000,
    "bloat_percentage": 24.69,
    "last_vacuum": "2025-12-19 10:30:00",
    "last_autovacuum": "2025-12-20 02:15:00",
    "needs_vacuum": true
  }
]
```

### Manual VACUUM

```sql
-- Vacuum specific table
VACUUM missions;

-- Vacuum and analyze
VACUUM ANALYZE missions;

-- Full vacuum (locks table)
VACUUM FULL missions;

-- Vacuum all tables
VACUUM;
```

### Auto-Vacuum Tuning

```sql
-- Per-table autovacuum settings
ALTER TABLE missions SET (
  autovacuum_vacuum_scale_factor = 0.1,  # Vacuum at 10% dead tuples
  autovacuum_analyze_scale_factor = 0.05 # Analyze at 5% dead tuples
);
```

---

## Read Replicas

### Setup (PostgreSQL)

**Master Configuration:**

```sql
-- postgresql.conf
wal_level = replica
max_wal_senders = 3
max_replication_slots = 3
synchronous_commit = on
```

**Replica Configuration:**

```sql
-- Create replication user on master
CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD 'password';

-- Configure replica
# postgresql.conf
primary_conninfo = 'host=postgres-master port=5432 user=replicator password=password'
hot_standby = on

# recovery.conf (or recovery.signal in PG 12+)
standby_mode = on
primary_conninfo = 'host=postgres-master port=5432 user=replicator password=password'
```

**Verify Replication:**

```sql
-- On master
SELECT * FROM pg_stat_replication;

-- On replica
SELECT pg_is_in_recovery();  -- Should return true
```

### Application Usage

```python
# backend/app/core/db.py
from sqlalchemy import create_engine

# Master (read-write)
engine_master = create_async_engine(
    "postgresql+asyncpg://brain:password@postgres-master:5432/brain"
)

# Replica (read-only)
engine_replica = create_async_engine(
    "postgresql+asyncpg://brain:password@postgres-replica:5432/brain"
)

# Route reads to replica
async def get_mission(mission_id: str):
    async with AsyncSession(engine_replica) as session:
        return await session.get(Mission, mission_id)

# Route writes to master
async def create_mission(mission: Mission):
    async with AsyncSession(engine_master) as session:
        session.add(mission)
        await session.commit()
```

---

## Performance Monitoring

### Table Statistics

```http
GET /api/db/table-stats

Response:
[
  {
    "schema": "public",
    "table": "missions",
    "total_size": "125 MB",
    "table_size": "100 MB",
    "indexes_size": "25 MB",
    "seq_scans": 1234,
    "seq_tuples_read": 123400,
    "index_scans": 5678,
    "index_tuples_fetched": 567800,
    "inserts": 10000,
    "updates": 5000,
    "deletes": 500
  }
]
```

### Index Usage

```http
GET /api/db/index-usage

Response:
[
  {
    "schema": "public",
    "table": "missions",
    "index": "idx_missions_status",
    "scans": 5678,
    "tuples_read": 567800,
    "tuples_fetched": 567800,
    "size": "2048 kB",
    "unused": false
  },
  {
    "schema": "public",
    "table": "missions",
    "index": "idx_missions_old",
    "scans": 0,
    "tuples_read": 0,
    "tuples_fetched": 0,
    "size": "1024 kB",
    "unused": true
  }
]
```

**Action:** Drop unused indexes

```sql
DROP INDEX idx_missions_old;
```

---

## Best Practices

1. **Index Wisely**
   - Don't over-index (slows writes)
   - Monitor index usage regularly
   - Drop unused indexes

2. **Use Connection Pooling**
   - Configure pool size appropriately
   - Monitor pool utilization
   - Adjust based on load

3. **Regular VACUUM**
   - Enable autovacuum
   - Monitor bloat
   - Manual VACUUM for heavy updates

4. **Analyze Slow Queries**
   - Enable pg_stat_statements
   - Review monthly
   - Optimize top 10 slowest

5. **Use Read Replicas**
   - Offload read traffic
   - Scale horizontally
   - Reduce master load

6. **Query Optimization**
   - Use EXPLAIN ANALYZE
   - Avoid SELECT *
   - Add WHERE clauses
   - Use LIMIT

7. **Monitor Metrics**
   - Track query latency
   - Monitor connection count
   - Watch bloat percentage

---

## Troubleshooting

### Issue: High CPU Usage

**Check:**
```sql
SELECT pid, query, state, query_start
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY query_start;
```

**Kill Long-Running Query:**
```sql
SELECT pg_terminate_backend(12345);  -- Replace with PID
```

### Issue: Table Locks

**Check Locks:**
```sql
SELECT
  t.relname,
  l.locktype,
  l.mode,
  l.granted,
  a.query
FROM pg_locks l
JOIN pg_stat_activity a ON l.pid = a.pid
JOIN pg_class t ON l.relation = t.oid
WHERE NOT l.granted;
```

### Issue: Slow Queries

**Temporary Fix:**
```sql
-- Increase work_mem for session
SET work_mem = '256MB';

-- Run slow query
SELECT ...;
```

**Permanent Fix:**
```sql
-- Add index
CREATE INDEX idx_missions_status ON missions(status);
```

---

## Production Checklist

- [ ] pg_stat_statements enabled
- [ ] Auto-vacuum configured
- [ ] Connection pool sized appropriately
- [ ] Slow query monitoring active
- [ ] Indexes optimized
- [ ] Bloat monitored
- [ ] Read replicas configured (if needed)
- [ ] Backup strategy in place
- [ ] Monitoring alerts configured

---

## References

- [PostgreSQL Performance Tuning](https://www.postgresql.org/docs/current/performance-tips.html)
- [pg_stat_statements](https://www.postgresql.org/docs/current/pgstatstatements.html)
- [EXPLAIN Documentation](https://www.postgresql.org/docs/current/using-explain.html)
- [CLAUDE.md](../CLAUDE.md#phase-3-scalability) - BRAiN development guide

---

**Last Updated:** 2025-12-20
**Author:** BRAiN Development Team
**Version:** 1.0.0
