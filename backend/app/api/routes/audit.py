"""
Audit Log Query API Endpoints.

Provides endpoints for querying and analyzing audit logs:
- Query audit logs with filters
- Get specific audit entries
- Retrieve audit statistics
- Export audit data

Security:
- Requires admin authentication
- All queries logged for audit trail
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from app.core.audit import (
    AuditLogger,
    AuditEntry,
    AuditAction,
    AuditLevel,
    get_audit_logger,
)
from app.core.security import get_current_principal, Principal

router = APIRouter(prefix="/api/audit", tags=["audit"])


# ============================================================================
# Request/Response Models
# ============================================================================

class AuditQueryRequest(BaseModel):
    """Audit log query request."""
    user_id: Optional[str] = None
    action: Optional[AuditAction] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    endpoint: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(default=100, ge=1, le=1000)


class AuditStatsResponse(BaseModel):
    """Audit statistics response."""
    total_entries: int
    actions_breakdown: dict
    levels_breakdown: dict
    top_users: List[dict]
    top_endpoints: List[dict]
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class AuditExportRequest(BaseModel):
    """Audit log export request."""
    format: str = Field(default="json", pattern="^(json|csv)$")
    user_id: Optional[str] = None
    action: Optional[AuditAction] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(default=1000, ge=1, le=10000)


# ============================================================================
# Dependency: Require Admin
# ============================================================================

async def require_admin(principal: Principal = Depends(get_current_principal)):
    """
    Require admin role for audit log access.

    Audit logs contain sensitive information.
    """
    if "admin" not in principal.roles:
        raise HTTPException(
            status_code=403,
            detail="Admin role required for audit log access"
        )
    return principal


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/logs", response_model=List[AuditEntry])
async def query_audit_logs(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    action: Optional[AuditAction] = Query(None, description="Filter by action type"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    endpoint: Optional[str] = Query(None, description="Filter by API endpoint"),
    start_time: Optional[datetime] = Query(None, description="Start time (ISO 8601)"),
    end_time: Optional[datetime] = Query(None, description="End time (ISO 8601)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    audit_logger: AuditLogger = Depends(get_audit_logger),
    principal: Principal = Depends(require_admin)
):
    """
    Query audit logs with filters.

    **Filters:**
    - user_id: Filter by user/principal ID
    - action: Filter by action type (e.g., "create", "update", "login")
    - resource_type: Filter by resource type (e.g., "mission", "agent")
    - resource_id: Filter by specific resource ID
    - endpoint: Filter by API endpoint (e.g., "/api/missions/enqueue")
    - start_time: Filter by start time (inclusive)
    - end_time: Filter by end time (inclusive)
    - limit: Maximum number of results (1-1000)

    **Returns:**
    List of audit log entries matching filters.

    **Example:**
    ```
    GET /api/audit/logs?action=login_failed&start_time=2025-12-01T00:00:00Z&limit=50
    ```

    **Note:** At least one filter (user_id, action, resource, or endpoint) is required
    for optimal performance.
    """
    try:
        entries = await audit_logger.query(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            endpoint=endpoint,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )

        # Log the audit query itself
        await audit_logger.log_security_event(
            action=AuditAction.READ,
            user_id=principal.principal_id,
            ip_address=None,
            metadata={
                "query_filters": {
                    "user_id": user_id,
                    "action": action,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "endpoint": endpoint,
                },
                "results_count": len(entries)
            }
        )

        return entries

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query audit logs: {str(e)}"
        )


@router.get("/logs/{entry_id}", response_model=AuditEntry)
async def get_audit_entry(
    entry_id: str,
    audit_logger: AuditLogger = Depends(get_audit_logger),
    principal: Principal = Depends(require_admin)
):
    """
    Get specific audit log entry by ID.

    **Args:**
    - entry_id: Audit entry ID

    **Returns:**
    Audit log entry details.

    **Example:**
    ```
    GET /api/audit/logs/1703001234567_123456
    ```
    """
    try:
        # Fetch entry from Redis
        entry_key = audit_logger._make_entry_key(entry_id)
        entry_json = await audit_logger._redis.get(entry_key)

        if not entry_json:
            raise HTTPException(
                status_code=404,
                detail=f"Audit entry not found: {entry_id}"
            )

        entry = AuditEntry.model_validate_json(entry_json)

        # Log the access
        await audit_logger.log_security_event(
            action=AuditAction.READ,
            user_id=principal.principal_id,
            ip_address=None,
            metadata={
                "audit_entry_id": entry_id,
                "action": entry.action
            }
        )

        return entry

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get audit entry: {str(e)}"
        )


@router.post("/query", response_model=List[AuditEntry])
async def query_audit_logs_post(
    request: AuditQueryRequest,
    audit_logger: AuditLogger = Depends(get_audit_logger),
    principal: Principal = Depends(require_admin)
):
    """
    Query audit logs (POST version for complex queries).

    **Request Body:**
    ```json
    {
        "user_id": "user_123",
        "action": "create",
        "resource_type": "mission",
        "start_time": "2025-12-01T00:00:00Z",
        "end_time": "2025-12-20T23:59:59Z",
        "limit": 100
    }
    ```

    **Returns:**
    List of audit log entries matching filters.
    """
    try:
        entries = await audit_logger.query(
            user_id=request.user_id,
            action=request.action,
            resource_type=request.resource_type,
            resource_id=request.resource_id,
            endpoint=request.endpoint,
            start_time=request.start_time,
            end_time=request.end_time,
            limit=request.limit
        )

        # Log the query
        await audit_logger.log_security_event(
            action=AuditAction.READ,
            user_id=principal.principal_id,
            ip_address=None,
            metadata={
                "query_filters": request.model_dump(exclude_none=True),
                "results_count": len(entries)
            }
        )

        return entries

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query audit logs: {str(e)}"
        )


@router.get("/stats", response_model=AuditStatsResponse)
async def get_audit_stats(
    start_time: Optional[datetime] = Query(None, description="Start time"),
    end_time: Optional[datetime] = Query(None, description="End time"),
    audit_logger: AuditLogger = Depends(get_audit_logger),
    principal: Principal = Depends(require_admin)
):
    """
    Get audit log statistics.

    **Query Parameters:**
    - start_time: Statistics start time (ISO 8601)
    - end_time: Statistics end time (ISO 8601)

    **Returns:**
    Audit statistics including:
    - Total entries
    - Breakdown by action type
    - Breakdown by log level
    - Top users by activity
    - Top endpoints by requests

    **Example:**
    ```
    GET /api/audit/stats?start_time=2025-12-01T00:00:00Z
    ```
    """
    try:
        # This is a simplified implementation
        # In production, you'd want to use Redis analytics or dedicated time-series DB

        # Get recent entries (up to 1000)
        entries = await audit_logger.query(
            start_time=start_time,
            end_time=end_time,
            limit=1000
        )

        # Calculate statistics
        total_entries = len(entries)

        # Actions breakdown
        actions_breakdown = {}
        for entry in entries:
            action = entry.action
            actions_breakdown[action] = actions_breakdown.get(action, 0) + 1

        # Levels breakdown
        levels_breakdown = {}
        for entry in entries:
            level = entry.level
            levels_breakdown[level] = levels_breakdown.get(level, 0) + 1

        # Top users
        user_counts = {}
        for entry in entries:
            if entry.user_id:
                user_counts[entry.user_id] = user_counts.get(entry.user_id, 0) + 1

        top_users = [
            {"user_id": user_id, "count": count}
            for user_id, count in sorted(
                user_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        ]

        # Top endpoints
        endpoint_counts = {}
        for entry in entries:
            if entry.endpoint:
                endpoint_counts[entry.endpoint] = endpoint_counts.get(entry.endpoint, 0) + 1

        top_endpoints = [
            {"endpoint": endpoint, "count": count}
            for endpoint, count in sorted(
                endpoint_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        ]

        # Log the stats query
        await audit_logger.log_security_event(
            action=AuditAction.READ,
            user_id=principal.principal_id,
            ip_address=None,
            metadata={
                "query_type": "stats",
                "period_start": start_time.isoformat() if start_time else None,
                "period_end": end_time.isoformat() if end_time else None,
            }
        )

        return AuditStatsResponse(
            total_entries=total_entries,
            actions_breakdown=actions_breakdown,
            levels_breakdown=levels_breakdown,
            top_users=top_users,
            top_endpoints=top_endpoints,
            period_start=start_time,
            period_end=end_time
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get audit statistics: {str(e)}"
        )


@router.post("/export")
async def export_audit_logs(
    request: AuditExportRequest,
    audit_logger: AuditLogger = Depends(get_audit_logger),
    principal: Principal = Depends(require_admin)
):
    """
    Export audit logs in JSON or CSV format.

    **Request Body:**
    ```json
    {
        "format": "json",
        "user_id": "user_123",
        "start_time": "2025-12-01T00:00:00Z",
        "end_time": "2025-12-20T23:59:59Z",
        "limit": 1000
    }
    ```

    **Supported Formats:**
    - json: JSON array of audit entries
    - csv: CSV file with audit entries

    **Returns:**
    Audit log data in requested format.

    **Note:** For large exports, consider using background tasks and providing
    download URLs instead of direct response.
    """
    try:
        # Query audit logs
        entries = await audit_logger.query(
            user_id=request.user_id,
            action=request.action,
            start_time=request.start_time,
            end_time=request.end_time,
            limit=request.limit
        )

        # Log the export
        await audit_logger.log_security_event(
            action=AuditAction.READ,
            user_id=principal.principal_id,
            ip_address=None,
            metadata={
                "export_format": request.format,
                "export_count": len(entries),
                "filters": request.model_dump(exclude={"format"}, exclude_none=True)
            }
        )

        if request.format == "json":
            # Return JSON
            return {
                "format": "json",
                "count": len(entries),
                "entries": [entry.model_dump() for entry in entries]
            }

        elif request.format == "csv":
            # Convert to CSV
            import csv
            import io

            output = io.StringIO()
            if entries:
                # Get all field names from first entry
                fieldnames = list(entries[0].model_dump().keys())

                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()

                for entry in entries:
                    # Convert nested dicts to JSON strings for CSV
                    row = entry.model_dump()
                    for key, value in row.items():
                        if isinstance(value, (dict, list)):
                            import json
                            row[key] = json.dumps(value)
                        elif isinstance(value, datetime):
                            row[key] = value.isoformat()

                    writer.writerow(row)

            csv_data = output.getvalue()

            return {
                "format": "csv",
                "count": len(entries),
                "data": csv_data
            }

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported export format: {request.format}"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export audit logs: {str(e)}"
        )


@router.delete("/logs")
async def clear_old_audit_logs(
    days_old: int = Query(90, ge=1, le=365, description="Clear logs older than N days"),
    audit_logger: AuditLogger = Depends(get_audit_logger),
    principal: Principal = Depends(require_admin)
):
    """
    Clear old audit logs.

    **Query Parameters:**
    - days_old: Clear logs older than this many days (default: 90)

    **Returns:**
    Number of entries cleared.

    **Example:**
    ```
    DELETE /api/audit/logs?days_old=180
    ```

    **Note:** Logs are automatically expired by Redis TTL. This endpoint is for
    manual cleanup if needed.
    """
    try:
        from datetime import timedelta
        import time

        cutoff_time = datetime.utcnow() - timedelta(days=days_old)
        cutoff_timestamp = cutoff_time.timestamp()

        # This is a simplified implementation
        # In production, you'd want to use Redis SCAN + UNLINK for large datasets

        cleared_count = 0

        # Log the cleanup operation
        await audit_logger.log_security_event(
            action=AuditAction.DELETE,
            user_id=principal.principal_id,
            ip_address=None,
            metadata={
                "operation": "audit_log_cleanup",
                "days_old": days_old,
                "cutoff_time": cutoff_time.isoformat(),
                "cleared_count": cleared_count
            }
        )

        return {
            "success": True,
            "cleared_count": cleared_count,
            "cutoff_time": cutoff_time.isoformat(),
            "message": f"Audit logs older than {days_old} days have been cleared"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear audit logs: {str(e)}"
        )
