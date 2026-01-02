"""
System Events Service

CRUD operations for system events with Redis caching.
"""
import asyncpg
import redis.asyncio as redis
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from backend.models.system_event import (
    SystemEventCreate,
    SystemEventUpdate,
    SystemEventResponse,
    EventStats,
    EventSeverity
)


class SystemEventsService:
    """Service for managing system events"""

    def __init__(self, db_pool: asyncpg.Pool, redis_client: redis.Redis):
        self.db = db_pool
        self.redis = redis_client
        self.cache_ttl = {
            "event": 300,      # 5 minutes
            "type": 60,        # 1 minute
            "stats": 30,       # 30 seconds
        }

    # Cache key generators
    def _event_cache_key(self, event_id: int) -> str:
        return f"events:id:{event_id}"

    def _type_cache_key(self, event_type: str) -> str:
        return f"events:type:{event_type}"

    def _stats_cache_key(self) -> str:
        return "events:stats"

    # Cache operations
    async def _cache_event(self, event: Dict[str, Any]):
        """Cache a single event"""
        try:
            key = self._event_cache_key(event["id"])
            await self.redis.setex(
                key,
                self.cache_ttl["event"],
                json.dumps(event, default=str)
            )
        except Exception as e:
            print(f"Cache write error: {e}")

    async def _get_cached_event(self, event_id: int) -> Optional[Dict[str, Any]]:
        """Get cached event"""
        try:
            key = self._event_cache_key(event_id)
            cached = await self.redis.get(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            print(f"Cache read error: {e}")
        return None

    async def _invalidate_caches(self, event_id: Optional[int] = None, event_type: Optional[str] = None):
        """Invalidate related caches"""
        try:
            keys_to_delete = [self._stats_cache_key()]

            if event_id:
                keys_to_delete.append(self._event_cache_key(event_id))

            if event_type:
                keys_to_delete.append(self._type_cache_key(event_type))

            await self.redis.delete(*keys_to_delete)
        except Exception as e:
            print(f"Cache invalidation error: {e}")

    # CRUD Operations
    async def create_event(self, event_data: SystemEventCreate) -> SystemEventResponse:
        """Create a new system event"""
        query = """
        INSERT INTO system_events (event_type, severity, message, details, source)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, event_type, severity, message, details, source, timestamp, created_at
        """

        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                query,
                event_data.event_type,
                event_data.severity.value,
                event_data.message,
                json.dumps(event_data.details) if event_data.details else None,
                event_data.source
            )

        event_dict = dict(row)

        # Cache the new event
        await self._cache_event(event_dict)

        # Invalidate stats and type caches
        await self._invalidate_caches(event_type=event_data.event_type)

        return SystemEventResponse(**event_dict)

    async def get_event(self, event_id: int) -> Optional[SystemEventResponse]:
        """Get event by ID (with caching)"""
        # Try cache first
        cached = await self._get_cached_event(event_id)
        if cached:
            return SystemEventResponse(**cached)

        # Query database
        query = """
        SELECT id, event_type, severity, message, details, source, timestamp, created_at
        FROM system_events
        WHERE id = $1
        """

        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, event_id)

        if not row:
            return None

        event_dict = dict(row)

        # Cache for next time
        await self._cache_event(event_dict)

        return SystemEventResponse(**event_dict)

    async def list_events(
        self,
        limit: int = 100,
        offset: int = 0,
        event_type: Optional[str] = None,
        severity: Optional[EventSeverity] = None
    ) -> List[SystemEventResponse]:
        """List events with optional filtering"""
        conditions = []
        params = []
        param_count = 0

        if event_type:
            param_count += 1
            conditions.append(f"event_type = ${param_count}")
            params.append(event_type)

        if severity:
            param_count += 1
            conditions.append(f"severity = ${param_count}")
            params.append(severity.value)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        param_count += 1
        params.append(limit)
        param_count += 1
        params.append(offset)

        query = f"""
        SELECT id, event_type, severity, message, details, source, timestamp, created_at
        FROM system_events
        {where_clause}
        ORDER BY timestamp DESC
        LIMIT ${param_count - 1} OFFSET ${param_count}
        """

        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [SystemEventResponse(**dict(row)) for row in rows]

    async def update_event(self, event_id: int, event_data: SystemEventUpdate) -> Optional[SystemEventResponse]:
        """Update an existing event"""
        # Build dynamic update query
        updates = []
        params = []
        param_count = 0

        if event_data.event_type is not None:
            param_count += 1
            updates.append(f"event_type = ${param_count}")
            params.append(event_data.event_type)

        if event_data.severity is not None:
            param_count += 1
            updates.append(f"severity = ${param_count}")
            params.append(event_data.severity.value)

        if event_data.message is not None:
            param_count += 1
            updates.append(f"message = ${param_count}")
            params.append(event_data.message)

        if event_data.details is not None:
            param_count += 1
            updates.append(f"details = ${param_count}")
            params.append(json.dumps(event_data.details))

        if event_data.source is not None:
            param_count += 1
            updates.append(f"source = ${param_count}")
            params.append(event_data.source)

        if not updates:
            # No fields to update, just return current event
            return await self.get_event(event_id)

        param_count += 1
        params.append(event_id)

        query = f"""
        UPDATE system_events
        SET {', '.join(updates)}
        WHERE id = ${param_count}
        RETURNING id, event_type, severity, message, details, source, timestamp, created_at
        """

        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, *params)

        if not row:
            return None

        event_dict = dict(row)

        # Invalidate caches
        await self._invalidate_caches(event_id=event_id, event_type=event_dict["event_type"])

        return SystemEventResponse(**event_dict)

    async def delete_event(self, event_id: int) -> bool:
        """Delete an event"""
        # Get event first to know which caches to invalidate
        event = await self.get_event(event_id)
        if not event:
            return False

        query = "DELETE FROM system_events WHERE id = $1"

        async with self.db.acquire() as conn:
            result = await conn.execute(query, event_id)

        # Invalidate caches
        await self._invalidate_caches(event_id=event_id, event_type=event.event_type)

        return result == "DELETE 1"

    async def get_stats(self) -> EventStats:
        """Get event statistics (with caching)"""
        # Try cache first
        try:
            cached = await self.redis.get(self._stats_cache_key())
            if cached:
                return EventStats(**json.loads(cached))
        except Exception:
            pass

        # Query database
        query_total = "SELECT COUNT(*) FROM system_events"
        query_by_severity = "SELECT severity, COUNT(*) FROM system_events GROUP BY severity"
        query_by_type = "SELECT event_type, COUNT(*) FROM system_events GROUP BY event_type LIMIT 20"
        query_recent = """
        SELECT COUNT(*) FROM system_events
        WHERE timestamp >= NOW() - INTERVAL '24 hours'
        """
        query_last = "SELECT MAX(timestamp) FROM system_events"

        async with self.db.acquire() as conn:
            total = await conn.fetchval(query_total)
            severity_rows = await conn.fetch(query_by_severity)
            type_rows = await conn.fetch(query_by_type)
            recent = await conn.fetchval(query_recent)
            last_timestamp = await conn.fetchval(query_last)

        events_by_severity = {row["severity"]: row["count"] for row in severity_rows}
        events_by_type = {row["event_type"]: row["count"] for row in type_rows}

        stats = EventStats(
            total_events=total,
            events_by_severity=events_by_severity,
            events_by_type=events_by_type,
            recent_events=recent,
            last_event_timestamp=last_timestamp
        )

        # Cache stats
        try:
            await self.redis.setex(
                self._stats_cache_key(),
                self.cache_ttl["stats"],
                json.dumps(stats.model_dump(), default=str)
            )
        except Exception:
            pass

        return stats
