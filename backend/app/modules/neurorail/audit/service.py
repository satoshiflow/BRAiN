"""
NeuroRail Audit Service.

Provides immutable audit logging with:
- Append-only PostgreSQL storage
- EventStream integration for real-time observability
- Query API for audit trail analysis
"""

from __future__ import annotations
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.neurorail.audit.schemas import (
    AuditEvent,
    AuditQuery,
    AuditQueryResponse,
    AuditStats,
)
from app.modules.neurorail.errors import (
    NeuroRailError,
    NeuroRailErrorCode,
)


class AuditService:
    """
    Service for managing NeuroRail audit trail.

    Responsibilities:
    - Append events to PostgreSQL audit log
    - Publish events to EventStream for real-time monitoring
    - Provide query API for audit analysis
    - Never allow updates or deletes (append-only)
    """

    def __init__(self):
        # EventStream integration (optional dependency)
        self.event_stream = None
        try:
            from backend.mission_control_core.core.event_stream import EventStream, EventType, Event
            # Initialize EventStream connection (will be created on first use)
            self._event_stream_class = EventStream
            self._event_type_class = EventType
            self._event_class = Event
        except ImportError:
            logger.warning("EventStream not available - audit events will not be published to stream")

    async def _get_event_stream(self):
        """Get or create EventStream instance."""
        if self.event_stream is None and self._event_stream_class:
            from app.core.config import get_settings
            settings = get_settings()
            self.event_stream = self._event_stream_class(redis_url=settings.redis_url)
            await self.event_stream.initialize()
        return self.event_stream

    # ========================================================================
    # Audit Logging
    # ========================================================================

    async def log(
        self,
        event: AuditEvent,
        db: AsyncSession
    ) -> AuditEvent:
        """
        Log an audit event.

        Args:
            event: Audit event to log
            db: Database session

        Returns:
            Logged audit event with audit_id

        Raises:
            NeuroRailError: If audit logging fails (critical error)
        """
        try:
            # 1. Persist to PostgreSQL (durable storage)
            await self._persist_to_postgres(event, db)

            # 2. Publish to EventStream (real-time observability)
            await self._publish_to_stream(event)

            logger.debug(
                f"Audit event logged: {event.audit_id} "
                f"[{event.event_category}/{event.event_type}] "
                f"{event.message}"
            )

            return event

        except Exception as e:
            # Audit log failure is CRITICAL - system cannot operate without it
            logger.error(f"CRITICAL: Audit log failure: {e}")
            raise NeuroRailError(
                code=NeuroRailErrorCode.AUDIT_LOG_FAILURE,
                message=f"Failed to write audit log: {str(e)}",
                details={
                    "event_type": event.event_type,
                    "event_category": event.event_category,
                    "mission_id": event.mission_id,
                }
            )

    async def _persist_to_postgres(
        self,
        event: AuditEvent,
        db: AsyncSession
    ) -> None:
        """Persist audit event to PostgreSQL."""
        query = text("""
            INSERT INTO neurorail_audit
                (audit_id, timestamp, mission_id, plan_id, job_id, attempt_id, resource_uuid,
                 event_type, event_category, severity, message, details,
                 caused_by_agent, caused_by_event, created_at)
            VALUES
                (:audit_id, :timestamp, :mission_id, :plan_id, :job_id, :attempt_id, :resource_uuid,
                 :event_type, :event_category, :severity, :message, :details,
                 :caused_by_agent, :caused_by_event, NOW())
        """)

        await db.execute(query, {
            "audit_id": event.audit_id,
            "timestamp": event.timestamp,
            "mission_id": event.mission_id,
            "plan_id": event.plan_id,
            "job_id": event.job_id,
            "attempt_id": event.attempt_id,
            "resource_uuid": event.resource_uuid,
            "event_type": event.event_type,
            "event_category": event.event_category,
            "severity": event.severity,
            "message": event.message,
            "details": json.dumps(event.details),
            "caused_by_agent": event.caused_by_agent,
            "caused_by_event": event.caused_by_event,
        })
        await db.commit()

    async def _publish_to_stream(self, event: AuditEvent) -> None:
        """Publish audit event to EventStream."""
        event_stream = await self._get_event_stream()
        if not event_stream:
            return  # EventStream not available, skip publishing

        # Map NeuroRail event to EventStream format
        stream_event = self._event_class(
            id=event.audit_id,
            type=self._map_to_event_type(event.event_type),
            source="neurorail",
            target=None,  # Broadcast
            payload={
                "event_category": event.event_category,
                "severity": event.severity,
                "message": event.message,
                "details": event.details,
                "trace_context": {
                    "mission_id": event.mission_id,
                    "plan_id": event.plan_id,
                    "job_id": event.job_id,
                    "attempt_id": event.attempt_id,
                    "resource_uuid": event.resource_uuid,
                }
            },
            timestamp=event.timestamp,
            mission_id=event.mission_id,
            severity=event.severity.upper(),
            meta={
                "schema_version": 1,
                "producer": "neurorail",
                "source_module": "neurorail.audit"
            }
        )

        try:
            await event_stream.publish(stream_event)
        except Exception as e:
            # Non-critical: EventStream publishing failure should not break audit logging
            logger.warning(f"Failed to publish audit event to EventStream: {e}")

    def _map_to_event_type(self, neurorail_event_type: str):
        """Map NeuroRail event type to EventStream EventType."""
        # For now, use SYSTEM_ALERT for all NeuroRail events
        # TODO: Add NeuroRail-specific event types to EventType enum
        return self._event_type_class.SYSTEM_ALERT

    # ========================================================================
    # Audit Queries
    # ========================================================================

    async def query(
        self,
        query: AuditQuery,
        db: AsyncSession
    ) -> AuditQueryResponse:
        """
        Query audit log.

        Args:
            query: Query parameters
            db: Database session

        Returns:
            Query results with events and pagination info
        """
        # Build WHERE clause dynamically
        where_clauses = []
        params: Dict[str, Any] = {}

        if query.mission_id:
            where_clauses.append("mission_id = :mission_id")
            params["mission_id"] = query.mission_id

        if query.job_id:
            where_clauses.append("job_id = :job_id")
            params["job_id"] = query.job_id

        if query.event_type:
            where_clauses.append("event_type = :event_type")
            params["event_type"] = query.event_type

        if query.event_category:
            where_clauses.append("event_category = :event_category")
            params["event_category"] = query.event_category

        if query.severity:
            where_clauses.append("severity = :severity")
            params["severity"] = query.severity

        if query.start_time:
            where_clauses.append("timestamp >= :start_time")
            params["start_time"] = query.start_time

        if query.end_time:
            where_clauses.append("timestamp <= :end_time")
            params["end_time"] = query.end_time

        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        # Count total matching events
        count_query = text(f"""
            SELECT COUNT(*) FROM neurorail_audit {where_clause}
        """)
        count_result = await db.execute(count_query, params)
        total = count_result.scalar()

        # Fetch events with pagination
        params["limit"] = query.limit
        params["offset"] = query.offset

        select_query = text(f"""
            SELECT
                audit_id, timestamp, mission_id, plan_id, job_id, attempt_id, resource_uuid,
                event_type, event_category, severity, message, details,
                caused_by_agent, caused_by_event
            FROM neurorail_audit
            {where_clause}
            ORDER BY timestamp DESC
            LIMIT :limit OFFSET :offset
        """)

        result = await db.execute(select_query, params)
        rows = result.fetchall()

        events = [
            AuditEvent(
                audit_id=row[0],
                timestamp=row[1],
                mission_id=row[2],
                plan_id=row[3],
                job_id=row[4],
                attempt_id=row[5],
                resource_uuid=row[6],
                event_type=row[7],
                event_category=row[8],
                severity=row[9],
                message=row[10],
                details=json.loads(row[11]) if row[11] else {},
                caused_by_agent=row[12],
                caused_by_event=row[13],
            )
            for row in rows
        ]

        return AuditQueryResponse(
            events=events,
            total=total,
            limit=query.limit,
            offset=query.offset,
        )

    async def get_trace_audit(
        self,
        mission_id: str,
        db: AsyncSession
    ) -> List[AuditEvent]:
        """
        Get complete audit trail for a mission.

        Args:
            mission_id: Mission ID
            db: Database session

        Returns:
            All audit events for the mission, ordered by timestamp
        """
        query = AuditQuery(mission_id=mission_id, limit=1000)
        response = await self.query(query, db)
        return response.events

    # ========================================================================
    # Audit Statistics
    # ========================================================================

    async def get_stats(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        db: AsyncSession = None
    ) -> AuditStats:
        """
        Get audit log statistics.

        Args:
            start_time: Start of time range
            end_time: End of time range
            db: Database session

        Returns:
            Audit statistics
        """
        where_clauses = []
        params: Dict[str, Any] = {}

        if start_time:
            where_clauses.append("timestamp >= :start_time")
            params["start_time"] = start_time

        if end_time:
            where_clauses.append("timestamp <= :end_time")
            params["end_time"] = end_time

        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        # Total events
        total_query = text(f"SELECT COUNT(*) FROM neurorail_audit {where_clause}")
        total_result = await db.execute(total_query, params)
        total_events = total_result.scalar()

        # Events by category
        category_query = text(f"""
            SELECT event_category, COUNT(*) as count
            FROM neurorail_audit {where_clause}
            GROUP BY event_category
        """)
        category_result = await db.execute(category_query, params)
        events_by_category = {row[0]: row[1] for row in category_result.fetchall()}

        # Events by severity
        severity_query = text(f"""
            SELECT severity, COUNT(*) as count
            FROM neurorail_audit {where_clause}
            GROUP BY severity
        """)
        severity_result = await db.execute(severity_query, params)
        events_by_severity = {row[0]: row[1] for row in severity_result.fetchall()}

        # Events by type
        type_query = text(f"""
            SELECT event_type, COUNT(*) as count
            FROM neurorail_audit {where_clause}
            GROUP BY event_type
            LIMIT 20
        """)
        type_result = await db.execute(type_query, params)
        events_by_type = {row[0]: row[1] for row in type_result.fetchall()}

        return AuditStats(
            total_events=total_events,
            events_by_category=events_by_category,
            events_by_severity=events_by_severity,
            events_by_type=events_by_type,
            time_range_start=start_time or datetime.min,
            time_range_end=end_time or datetime.utcnow(),
        )


# Singleton instance
_audit_service: Optional[AuditService] = None


def get_audit_service() -> AuditService:
    """Get singleton audit service instance."""
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service
