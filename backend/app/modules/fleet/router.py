"""
Fleet Module Router

REST API endpoints for fleet management and multi-robot coordination.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status, Depends

from app.core.auth_deps import require_operator, Principal
from app.modules.fleet.schemas import (
    FleetInfo,
    FleetCreateRequest,
    FleetUpdateRequest,
    FleetListResponse,
    RobotInfo,
    RobotRegisterRequest,
    RobotUpdateRequest,
    RobotListResponse,
    FleetTask,
    TaskAssignRequest,
    TaskAssignmentResponse,
    TaskListResponse,
    CoordinationZone,
    ZoneEntryRequest,
    ZoneEntryResponse,
    FleetStatistics,
)
from app.modules.fleet.service import get_fleet_service


router = APIRouter(
    prefix="/api/fleet",
    tags=["Fleet"],
    dependencies=[Depends(require_operator)],
)


# ============================================================================
# MODULE INFO
# ============================================================================

@router.get("/info")
def get_fleet_info(
    principal: Principal = Depends(require_operator)
):
    """Get Fleet module information."""
    return {
        "name": "Fleet",
        "version": "1.0.0",
        "description": "Multi-robot fleet coordination and management system",
        "features": [
            "Fleet registration and management",
            "Robot status tracking",
            "Automated task assignment",
            "Load balancing across robots",
            "Coordination zone management",
            "Fleet-wide performance statistics",
        ],
        "endpoints": {
            "fleets": "GET/POST/PUT/DELETE /fleets/*",
            "robots": "GET/POST/PUT/DELETE /robots/*",
            "tasks": "GET/POST /tasks/*",
            "zones": "GET/POST /zones/*",
            "stats": "GET /fleets/{fleet_id}/statistics",
        },
    }


# ============================================================================
# FLEET MANAGEMENT
# ============================================================================

@router.get("/fleets", response_model=FleetListResponse)
def list_fleets(
    principal: Principal = Depends(require_operator)
):
    """List all registered fleets."""
    service = get_fleet_service()
    fleets = service.list_fleets()

    return FleetListResponse(
        total=len(fleets),
        fleets=fleets,
    )


@router.get("/fleets/{fleet_id}", response_model=FleetInfo)
def get_fleet(
    fleet_id: str,
    principal: Principal = Depends(require_operator)
):
    """Get information about a specific fleet."""
    service = get_fleet_service()
    fleet = service.get_fleet(fleet_id)

    if not fleet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fleet not found: {fleet_id}",
        )

    return fleet


@router.post("/fleets", response_model=FleetInfo, status_code=status.HTTP_201_CREATED)
def create_fleet(
    request: FleetCreateRequest,
    principal: Principal = Depends(require_operator)
):
    """Create a new fleet."""
    service = get_fleet_service()

    try:
        fleet = service.create_fleet(request)
        return fleet

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/fleets/{fleet_id}", response_model=FleetInfo)
def update_fleet(
    fleet_id: str,
    request: FleetUpdateRequest,
    principal: Principal = Depends(require_operator)
):
    """Update fleet information."""
    service = get_fleet_service()

    try:
        fleet = service.update_fleet(fleet_id, request)
        return fleet

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete("/fleets/{fleet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fleet(
    fleet_id: str,
    principal: Principal = Depends(require_operator)
):
    """Delete a fleet and unregister all its robots."""
    service = get_fleet_service()
    success = service.delete_fleet(fleet_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fleet not found: {fleet_id}",
        )


# ============================================================================
# ROBOT MANAGEMENT
# ============================================================================

@router.get("/robots", response_model=RobotListResponse)
def list_robots(
    fleet_id: Optional[str] = Query(None, description="Filter by fleet ID"),
    principal: Principal = Depends(require_operator)
):
    """List all registered robots, optionally filtered by fleet."""
    service = get_fleet_service()
    robots = service.list_robots(fleet_id=fleet_id)

    return RobotListResponse(
        total=len(robots),
        robots=robots,
    )


@router.get("/robots/{robot_id}", response_model=RobotInfo)
def get_robot(
    robot_id: str,
    principal: Principal = Depends(require_operator)
):
    """Get information about a specific robot."""
    service = get_fleet_service()
    robot = service.get_robot(robot_id)

    if not robot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Robot not found: {robot_id}",
        )

    return robot


@router.post("/robots", response_model=RobotInfo, status_code=status.HTTP_201_CREATED)
def register_robot(
    request: RobotRegisterRequest,
    principal: Principal = Depends(require_operator)
):
    """Register a new robot to a fleet."""
    service = get_fleet_service()

    try:
        robot = service.register_robot(request)
        return robot

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/robots/{robot_id}", response_model=RobotInfo)
def update_robot_status(
    robot_id: str,
    request: RobotUpdateRequest,
    principal: Principal = Depends(require_operator)
):
    """Update robot status."""
    service = get_fleet_service()

    try:
        robot = service.update_robot_status(robot_id, request)
        return robot

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete("/robots/{robot_id}", status_code=status.HTTP_204_NO_CONTENT)
def unregister_robot(
    robot_id: str,
    principal: Principal = Depends(require_operator)
):
    """Unregister a robot from its fleet."""
    service = get_fleet_service()
    success = service.unregister_robot(robot_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Robot not found: {robot_id}",
        )


# ============================================================================
# TASK ASSIGNMENT
# ============================================================================

@router.get("/tasks", response_model=TaskListResponse)
def list_tasks(
    fleet_id: Optional[str] = Query(None, description="Filter by fleet ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by task status"),
    principal: Principal = Depends(require_operator)
):
    """List tasks, optionally filtered by fleet and/or status."""
    service = get_fleet_service()
    tasks = service.list_tasks(fleet_id=fleet_id, status=status_filter)

    return TaskListResponse(
        total=len(tasks),
        tasks=tasks,
    )


@router.get("/tasks/{task_id}", response_model=FleetTask)
def get_task(
    task_id: str,
    principal: Principal = Depends(require_operator)
):
    """Get information about a specific task."""
    service = get_fleet_service()
    task = service.get_task(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {task_id}",
        )

    return task


@router.post("/fleets/{fleet_id}/tasks", response_model=TaskAssignmentResponse, status_code=status.HTTP_201_CREATED)
def assign_task(
    fleet_id: str,
    request: TaskAssignRequest,
    principal: Principal = Depends(require_operator)
):
    """
    Assign a task to the fleet.

    The system will automatically select the optimal robot based on:
    - Robot availability (idle robots preferred)
    - Capability match
    - Battery level
    - Distance to task location (if known)
    """
    service = get_fleet_service()

    try:
        assignment = service.assign_task(fleet_id, request)
        return assignment

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/tasks/{task_id}/complete", response_model=FleetTask)
def complete_task(
    task_id: str,
    success: bool = Query(True, description="Whether task completed successfully"),
    principal: Principal = Depends(require_operator)
):
    """Mark a task as completed (or failed)."""
    service = get_fleet_service()

    try:
        task = service.complete_task(task_id, success=success)
        return task

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# ============================================================================
# COORDINATION ZONES
# ============================================================================

@router.get("/zones", response_model=List[CoordinationZone])
def list_zones(
    principal: Principal = Depends(require_operator)
):
    """List all coordination zones."""
    service = get_fleet_service()
    return list(service.zones.values())


@router.get("/zones/{zone_id}", response_model=CoordinationZone)
def get_zone(
    zone_id: str,
    principal: Principal = Depends(require_operator)
):
    """Get information about a coordination zone."""
    service = get_fleet_service()
    zone = service.zones.get(zone_id)

    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone not found: {zone_id}",
        )

    return zone


@router.post("/zones", response_model=CoordinationZone, status_code=status.HTTP_201_CREATED)
def create_zone(
    zone_id: str = Query(..., description="Zone identifier"),
    zone_type: str = Query(..., description="Type of zone"),
    max_concurrent_robots: int = Query(1, ge=1, description="Max robots allowed simultaneously"),
    principal: Principal = Depends(require_operator)
):
    """Create a coordination zone."""
    service = get_fleet_service()
    zone = service.create_zone(
        zone_id=zone_id,
        zone_type=zone_type,
        max_concurrent_robots=max_concurrent_robots,
    )
    return zone


@router.post("/zones/request-entry", response_model=ZoneEntryResponse)
def request_zone_entry(
    request: ZoneEntryRequest,
    principal: Principal = Depends(require_operator)
):
    """
    Request permission for a robot to enter a coordination zone.

    Returns permission status and estimated wait time if zone is occupied.
    """
    service = get_fleet_service()
    response = service.request_zone_entry(request)
    return response


@router.post("/zones/{zone_id}/exit", status_code=status.HTTP_204_NO_CONTENT)
def exit_zone(
    zone_id: str,
    robot_id: str = Query(..., description="Robot exiting the zone"),
    principal: Principal = Depends(require_operator)
):
    """Robot exits a coordination zone."""
    service = get_fleet_service()
    success = service.exit_zone(zone_id, robot_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Robot {robot_id} not found in zone {zone_id}",
        )


# ============================================================================
# STATISTICS
# ============================================================================

@router.get("/fleets/{fleet_id}/statistics", response_model=FleetStatistics)
def get_fleet_statistics(
    fleet_id: str,
    principal: Principal = Depends(require_operator)
):
    """Get comprehensive statistics for a fleet."""
    service = get_fleet_service()

    try:
        stats = service.get_fleet_statistics(fleet_id)
        return stats

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
