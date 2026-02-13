"""
NeuroRail Audit API Router.

Provides REST endpoints for:
- Querying audit log
- Getting audit statistics
- Viewing complete trace audit for a mission
"""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional, List

from app.core.database import get_db
from app.modules.neurorail.audit.service import (
    AuditService,
    get_audit_service,
)
from app.modules.neurorail.audit.schemas import (
    AuditEvent,
    AuditQuery,
    AuditQueryResponse,
    AuditStats,
)

router = APIRouter(prefix="/api/neurorail/v1/audit", tags=["NeuroRail Audit"])


# ============================================================================
# Audit Query Endpoints
# ============================================================================

@router.post("/query", response_model=AuditQueryResponse)
async def query_audit_log(
    query: AuditQuery,
    db: AsyncSession = Depends(get_db),
    service: AuditService = Depends(get_audit_service)
) -> AuditQueryResponse:
    """
    Query audit log with filters and pagination.

    Args:
        query: Query parameters (mission_id, event_type, severity, time range, etc.)

    Returns:
        Audit events matching the query

    Example:
        ```
        POST /api/neurorail/v1/audit/query
        {
          "mission_id": "m_a1b2c3d4e5f6",
          "severity": "error",
          "limit": 50
        }
        ```
    """
    try:
        return await service.query(query, db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query audit log: {str(e)}"
        )


@router.get("/mission/{mission_id}", response_model=List[AuditEvent])
async def get_mission_audit(
    mission_id: str,
    db: AsyncSession = Depends(get_db),
    service: AuditService = Depends(get_audit_service)
) -> List[AuditEvent]:
    """
    Get complete audit trail for a mission.

    Args:
        mission_id: Mission identifier (m_xxxxx)

    Returns:
        All audit events for the mission, ordered by timestamp

    Example:
        ```
        GET /api/neurorail/v1/audit/mission/m_a1b2c3d4e5f6
        ```
    """
    try:
        return await service.get_trace_audit(mission_id, db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get mission audit: {str(e)}"
        )


@router.get("/stats", response_model=AuditStats)
async def get_audit_stats(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    service: AuditService = Depends(get_audit_service)
) -> AuditStats:
    """
    Get audit log statistics.

    Args:
        start_time: Start of time range (optional)
        end_time: End of time range (optional)

    Returns:
        Audit statistics including event counts by category, severity, and type

    Example:
        ```
        GET /api/neurorail/v1/audit/stats?start_time=2025-12-30T00:00:00Z
        ```
    """
    try:
        return await service.get_stats(start_time, end_time, db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get audit stats: {str(e)}"
        )


# Note: Audit log writes are done via service, not exposed as API endpoints
# (only internal modules can write to audit log)
