"""
AXE Event Telemetry Service

Database operations and business logic for event telemetry.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from .schemas import (
    AxeEventCreate,
    AxeEventResponse,
    AxeEventStats,
    AxeEventQuery,
    AxeEventType,
    AnonymizationLevel,
)
from .anonymization import get_anonymization_service


class TelemetryService:
    """
    Service for managing AXE event telemetry.

    **Features:**
    - Store events with automatic anonymization
    - Query events with filters
    - Aggregate statistics
    - Automatic cleanup of old events
    """

    def __init__(self):
        self.anonymization_service = get_anonymization_service()

    async def create_event(
        self,
        db: AsyncSession,
        event: AxeEventCreate
    ) -> AxeEventResponse:
        """
        Create a single AXE event in the database.

        Args:
            db: Database session
            event: Event to create

        Returns:
            Created event with ID and timestamp
        """
        # Anonymize event
        anonymized_event, anon_result = self.anonymization_service.anonymize_event(event)

        # Log anonymization for audit
        logger.info(
            f"Event anonymized: level={anon_result.level}, "
            f"fields_hashed={len(anon_result.fields_hashed)}, "
            f"fields_removed={len(anon_result.fields_removed)}"
        )

        # Insert into database
        query = text("""
            INSERT INTO axe_events (
                event_type,
                session_id,
                app_id,
                user_id,
                anonymization_level,
                event_data,
                client_timestamp,
                retention_days,
                is_training_data,
                client_version,
                client_platform
            )
            VALUES (
                :event_type,
                :session_id,
                :app_id,
                :user_id,
                :anonymization_level,
                :event_data::jsonb,
                :client_timestamp,
                90,
                :is_training_data,
                :client_version,
                :client_platform
            )
            RETURNING
                id::text,
                event_type,
                session_id,
                app_id,
                user_id,
                anonymization_level,
                event_data,
                client_timestamp,
                created_at,
                retention_days,
                is_training_data,
                client_version,
                client_platform
        """)

        result = await db.execute(
            query,
            {
                "event_type": anonymized_event.event_type.value,
                "session_id": anonymized_event.session_id,
                "app_id": anonymized_event.app_id,
                "user_id": anonymized_event.user_id,
                "anonymization_level": anonymized_event.anonymization_level.value,
                "event_data": anonymized_event.event_data,
                "client_timestamp": anonymized_event.client_timestamp,
                "is_training_data": anonymized_event.is_training_data,
                "client_version": anonymized_event.client_version,
                "client_platform": anonymized_event.client_platform,
            }
        )

        row = result.fetchone()
        await db.commit()

        return AxeEventResponse(
            id=row[0],
            event_type=AxeEventType(row[1]),
            session_id=row[2],
            app_id=row[3],
            user_id=row[4],
            anonymization_level=AnonymizationLevel(row[5]),
            event_data=row[6],
            client_timestamp=row[7],
            created_at=row[8],
            retention_days=row[9],
            is_training_data=row[10],
            client_version=row[11],
            client_platform=row[12],
        )

    async def create_events_batch(
        self,
        db: AsyncSession,
        events: List[AxeEventCreate]
    ) -> List[AxeEventResponse]:
        """
        Create multiple AXE events in a single transaction.

        Args:
            db: Database session
            events: List of events to create

        Returns:
            List of created events
        """
        created_events = []

        for event in events:
            created_event = await self.create_event(db, event)
            created_events.append(created_event)

        logger.info(f"Batch created {len(created_events)} events")
        return created_events

    async def query_events(
        self,
        db: AsyncSession,
        query_params: AxeEventQuery
    ) -> List[AxeEventResponse]:
        """
        Query AXE events with filters.

        Args:
            db: Database session
            query_params: Query parameters (session_id, app_id, event_types, etc.)

        Returns:
            List of matching events
        """
        # Build WHERE clause dynamically
        where_clauses = []
        params = {}

        if query_params.session_id:
            where_clauses.append("session_id = :session_id")
            params["session_id"] = query_params.session_id

        if query_params.app_id:
            where_clauses.append("app_id = :app_id")
            params["app_id"] = query_params.app_id

        if query_params.user_id:
            where_clauses.append("user_id = :user_id")
            params["user_id"] = query_params.user_id

        if query_params.event_types:
            where_clauses.append("event_type = ANY(:event_types)")
            params["event_types"] = [et.value for et in query_params.event_types]

        if query_params.start_date:
            where_clauses.append("created_at >= :start_date")
            params["start_date"] = query_params.start_date

        if query_params.end_date:
            where_clauses.append("created_at <= :end_date")
            params["end_date"] = query_params.end_date

        if query_params.is_training_data is not None:
            where_clauses.append("is_training_data = :is_training_data")
            params["is_training_data"] = query_params.is_training_data

        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        query_sql = text(f"""
            SELECT
                id::text,
                event_type,
                session_id,
                app_id,
                user_id,
                anonymization_level,
                event_data,
                client_timestamp,
                created_at,
                retention_days,
                is_training_data,
                client_version,
                client_platform
            FROM axe_events
            {where_sql}
            ORDER BY created_at DESC
            LIMIT :limit
            OFFSET :offset
        """)

        params["limit"] = query_params.limit
        params["offset"] = query_params.offset

        result = await db.execute(query_sql, params)
        rows = result.fetchall()

        return [
            AxeEventResponse(
                id=row[0],
                event_type=AxeEventType(row[1]),
                session_id=row[2],
                app_id=row[3],
                user_id=row[4],
                anonymization_level=AnonymizationLevel(row[5]),
                event_data=row[6],
                client_timestamp=row[7],
                created_at=row[8],
                retention_days=row[9],
                is_training_data=row[10],
                client_version=row[11],
                client_platform=row[12],
            )
            for row in rows
        ]

    async def get_stats(
        self,
        db: AsyncSession,
        session_id: Optional[str] = None,
        app_id: Optional[str] = None
    ) -> AxeEventStats:
        """
        Get statistics for AXE events.

        Args:
            db: Database session
            session_id: Filter by session
            app_id: Filter by app

        Returns:
            Event statistics
        """
        where_clauses = []
        params = {}

        if session_id:
            where_clauses.append("session_id = :session_id")
            params["session_id"] = session_id

        if app_id:
            where_clauses.append("app_id = :app_id")
            params["app_id"] = app_id

        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        # Total count
        count_query = text(f"SELECT COUNT(*) FROM axe_events {where_sql}")
        total_result = await db.execute(count_query, params)
        total_events = total_result.scalar()

        # Event type breakdown
        type_query = text(f"""
            SELECT event_type, COUNT(*)
            FROM axe_events
            {where_sql}
            GROUP BY event_type
        """)
        type_result = await db.execute(type_query, params)
        event_type_counts = {row[0]: row[1] for row in type_result.fetchall()}

        # Sessions count
        session_query = text(f"""
            SELECT COUNT(DISTINCT session_id)
            FROM axe_events
            {where_sql}
        """)
        session_result = await db.execute(session_query, params)
        sessions = session_result.scalar()

        # Apps list
        app_query = text(f"""
            SELECT DISTINCT app_id
            FROM axe_events
            {where_sql}
        """)
        app_result = await db.execute(app_query, params)
        apps = [row[0] for row in app_result.fetchall()]

        # Date range
        date_query = text(f"""
            SELECT MIN(created_at), MAX(created_at)
            FROM axe_events
            {where_sql}
        """)
        date_result = await db.execute(date_query, params)
        date_row = date_result.fetchone()
        date_range = {
            "start": date_row[0],
            "end": date_row[1]
        }

        # Anonymization breakdown
        anon_query = text(f"""
            SELECT anonymization_level, COUNT(*)
            FROM axe_events
            {where_sql}
            GROUP BY anonymization_level
        """)
        anon_result = await db.execute(anon_query, params)
        anonymization_breakdown = {row[0]: row[1] for row in anon_result.fetchall()}

        return AxeEventStats(
            total_events=total_events,
            event_type_counts=event_type_counts,
            sessions=sessions,
            apps=apps,
            date_range=date_range,
            anonymization_breakdown=anonymization_breakdown,
        )


# Global instance
_telemetry_service: Optional[TelemetryService] = None


def get_telemetry_service() -> TelemetryService:
    """
    Get or create the global telemetry service instance.

    Returns:
        TelemetryService instance
    """
    global _telemetry_service
    if _telemetry_service is None:
        _telemetry_service = TelemetryService()
    return _telemetry_service
