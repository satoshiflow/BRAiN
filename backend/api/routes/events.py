"""
System Events API Routes

CRUD endpoints for system events.
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from datetime import datetime, timedelta

from services.system_events import SystemEventsService

from models.system_event import (
    SystemEventCreate,
    SystemEventUpdate,
    SystemEventResponse,
    EventStats,
    EventSeverity
)

# This will be injected from main app
# For now, this is a placeholder - actual dependency injection happens in main_minimal_v3.py
router = APIRouter(prefix="/api/events", tags=["events"])


# Dependency (will be properly implemented in main app)
_events_service: Optional[SystemEventsService] = None


class InMemorySystemEventsService:
    """In-memory fallback for local/test environments without DB/Redis."""

    def __init__(self) -> None:
        self._events: dict[int, SystemEventResponse] = {}
        self._next_id = 1

    async def create_event(self, event_data: SystemEventCreate) -> SystemEventResponse:
        now = datetime.utcnow()
        event = SystemEventResponse(
            id=self._next_id,
            event_type=event_data.event_type,
            severity=event_data.severity,
            message=event_data.message,
            details=event_data.details,
            source=event_data.source,
            timestamp=now,
            created_at=now,
        )
        self._events[self._next_id] = event
        self._next_id += 1
        return event

    async def get_event(self, event_id: int) -> Optional[SystemEventResponse]:
        return self._events.get(event_id)

    async def list_events(
        self,
        limit: int = 100,
        offset: int = 0,
        event_type: Optional[str] = None,
        severity: Optional[EventSeverity] = None,
    ) -> List[SystemEventResponse]:
        events = list(self._events.values())
        events.sort(key=lambda e: e.timestamp, reverse=True)

        if event_type is not None:
            events = [e for e in events if e.event_type == event_type]
        if severity is not None:
            events = [e for e in events if e.severity == severity]

        return events[offset : offset + limit]

    async def update_event(self, event_id: int, event_data: SystemEventUpdate) -> Optional[SystemEventResponse]:
        existing = self._events.get(event_id)
        if existing is None:
            return None

        updated = existing.model_copy(
            update={k: v for k, v in event_data.model_dump(exclude_unset=True).items()}
        )
        self._events[event_id] = updated
        return updated

    async def delete_event(self, event_id: int) -> bool:
        return self._events.pop(event_id, None) is not None

    async def get_stats(self) -> EventStats:
        events = list(self._events.values())
        by_severity: dict[str, int] = {}
        by_type: dict[str, int] = {}
        now = datetime.utcnow()

        for event in events:
            by_severity[event.severity.value] = by_severity.get(event.severity.value, 0) + 1
            by_type[event.event_type] = by_type.get(event.event_type, 0) + 1

        recent_events = sum(1 for event in events if event.timestamp >= now - timedelta(hours=24))
        last_event_timestamp = max((event.timestamp for event in events), default=None)

        return EventStats(
            total_events=len(events),
            events_by_severity=by_severity,
            events_by_type=by_type,
            recent_events=recent_events,
            last_event_timestamp=last_event_timestamp,
        )

async def get_events_service() -> SystemEventsService:
    """Get events service instance"""
    global _events_service
    if _events_service is None:
        try:
            _events_service = SystemEventsService()
        except TypeError:
            _events_service = InMemorySystemEventsService()
    return _events_service


@router.post("", response_model=SystemEventResponse, status_code=201)
async def create_event(
    event_data: SystemEventCreate,
    service: SystemEventsService = Depends(get_events_service)
):
    """
    Create a new system event.

    **Example:**
    ```json
    {
        "event_type": "health_check",
        "severity": "info",
        "message": "System health check passed",
        "details": {"postgres": "connected", "redis": "connected"},
        "source": "backend"
    }
    ```
    """
    return await service.create_event(event_data)


@router.get("", response_model=List[SystemEventResponse])
async def list_events(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    severity: Optional[EventSeverity] = Query(None, description="Filter by severity"),
    service: SystemEventsService = Depends(get_events_service)
):
    """
    List system events with optional filtering.

    **Filters:**
    - `event_type`: Filter by event type (e.g., "health_check")
    - `severity`: Filter by severity (info, warning, error, critical)
    - `limit`: Maximum results (default 100, max 1000)
    - `offset`: Pagination offset
    """
    return await service.list_events(
        limit=limit,
        offset=offset,
        event_type=event_type,
        severity=severity
    )


@router.get("/stats", response_model=EventStats)
async def get_event_stats(
    service: SystemEventsService = Depends(get_events_service)
):
    """
    Get event statistics.

    Returns:
    - Total number of events
    - Events grouped by severity
    - Events grouped by type
    - Recent events count (last 24 hours)
    - Last event timestamp
    """
    return await service.get_stats()


@router.get("/{event_id}", response_model=SystemEventResponse)
async def get_event(
    event_id: int,
    service: SystemEventsService = Depends(get_events_service)
):
    """
    Get a specific event by ID.
    """
    event = await service.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
    return event


@router.put("/{event_id}", response_model=SystemEventResponse)
async def update_event(
    event_id: int,
    event_data: SystemEventUpdate,
    service: SystemEventsService = Depends(get_events_service)
):
    """
    Update an existing event.

    **Note:** Only provided fields will be updated.
    """
    event = await service.update_event(event_id, event_data)
    if not event:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
    return event


@router.delete("/{event_id}", status_code=204)
async def delete_event(
    event_id: int,
    service: SystemEventsService = Depends(get_events_service)
):
    """
    Delete an event.
    """
    success = await service.delete_event(event_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
    return None
