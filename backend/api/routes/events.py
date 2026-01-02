"""
System Events API Routes

CRUD endpoints for system events.
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional

from backend.models.system_event import (
    SystemEventCreate,
    SystemEventUpdate,
    SystemEventResponse,
    EventStats,
    EventSeverity
)
from backend.services.system_events import SystemEventsService

# This will be injected from main app
# For now, this is a placeholder - actual dependency injection happens in main_minimal_v3.py
router = APIRouter(prefix="/api/events", tags=["events"])


# Dependency (will be properly implemented in main app)
async def get_events_service() -> SystemEventsService:
    """Get events service instance - placeholder"""
    # This will be replaced with proper dependency injection
    raise NotImplementedError("Service dependency not configured")


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
