"""
ARO API Router - REST Endpoints

Provides REST API for the Autonomous Repo Operator.

Endpoints:
- POST /api/aro/operations - Propose new operation
- POST /api/aro/operations/{id}/validate - Validate operation
- POST /api/aro/operations/{id}/authorize - Authorize operation
- POST /api/aro/operations/{id}/execute - Execute operation
- GET /api/aro/operations - List operations
- GET /api/aro/operations/{id} - Get operation details
- GET /api/aro/operations/{id}/status - Get operation status
- GET /api/aro/stats - Get statistics
- GET /api/aro/health - Health check
- GET /api/aro/info - System information
- GET /api/aro/audit - Get audit log
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from .service import get_aro_service
from .schemas import (
    ProposeOperationRequest,
    AuthorizeOperationRequest,
    ExecuteOperationRequest,
    RepoOperation,
    OperationStatusResponse,
    OperationState,
    AROStats,
    AROHealth,
    AROInfo,
    AuditLogEntry,
)

router = APIRouter(prefix="/api/aro", tags=["ARO"])


# ============================================================================
# Operation Lifecycle Endpoints
# ============================================================================


@router.post("/operations", response_model=RepoOperation)
async def propose_operation(request: ProposeOperationRequest):
    """
    Propose a new repository operation.

    This is step 1 in the operation lifecycle.

    Returns:
        Created operation (in PROPOSED state)
    """
    try:
        service = get_aro_service()
        operation = await service.propose_operation(request)
        return operation

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/operations/{operation_id}/validate", response_model=RepoOperation)
async def validate_operation(operation_id: str):
    """
    Validate a proposed operation.

    This is step 2 in the operation lifecycle.

    Returns:
        Updated operation (in VALIDATING, PENDING_AUTH, or DENIED state)
    """
    try:
        service = get_aro_service()
        operation = await service.validate_operation(operation_id)
        return operation

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/operations/{operation_id}/authorize", response_model=RepoOperation)
async def authorize_operation(
    operation_id: str,
    request: AuthorizeOperationRequest
):
    """
    Authorize a validated operation.

    This is step 3 in the operation lifecycle.

    Returns:
        Updated operation (in AUTHORIZED or DENIED state)
    """
    try:
        # Ensure operation_id matches
        if request.operation_id != operation_id:
            raise HTTPException(
                status_code=400,
                detail="Operation ID mismatch"
            )

        service = get_aro_service()
        operation = await service.authorize_operation(request)
        return operation

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/operations/{operation_id}/execute", response_model=RepoOperation)
async def execute_operation(operation_id: str):
    """
    Execute an authorized operation.

    This is step 4 in the operation lifecycle.

    Returns:
        Updated operation (in EXECUTING, COMPLETED, or FAILED state)
    """
    try:
        service = get_aro_service()
        operation = await service.execute_operation(operation_id)
        return operation

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# ============================================================================
# Query Endpoints
# ============================================================================


@router.get("/operations", response_model=List[RepoOperation])
async def list_operations(
    limit: int = Query(100, ge=1, le=1000),
    state: Optional[OperationState] = None
):
    """
    List repository operations.

    Args:
        limit: Maximum number of operations to return (1-1000)
        state: Filter by operation state (optional)

    Returns:
        List of operations (newest first)
    """
    try:
        service = get_aro_service()
        operations = await service.list_operations(
            limit=limit,
            state_filter=state
        )
        return operations

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/operations/{operation_id}", response_model=RepoOperation)
async def get_operation(operation_id: str):
    """
    Get operation by ID.

    Returns:
        Operation details
    """
    try:
        service = get_aro_service()
        operation = await service.get_operation(operation_id)

        if not operation:
            raise HTTPException(
                status_code=404,
                detail=f"Operation not found: {operation_id}"
            )

        return operation

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/operations/{operation_id}/status", response_model=OperationStatusResponse)
async def get_operation_status(operation_id: str):
    """
    Get operation status with execution readiness check.

    Returns:
        Operation status including blocking issues
    """
    try:
        service = get_aro_service()
        status = await service.get_operation_status(operation_id)
        return status

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# ============================================================================
# System Endpoints
# ============================================================================


@router.get("/stats", response_model=AROStats)
async def get_stats():
    """
    Get ARO system statistics.

    Returns:
        System statistics including operation counts and rates
    """
    try:
        service = get_aro_service()
        stats = await service.get_stats()
        return stats

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/health", response_model=AROHealth)
async def get_health():
    """
    Get ARO system health status.

    Returns:
        Health status including operational state and integrity checks
    """
    try:
        service = get_aro_service()
        health = await service.get_health()
        return health

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/info", response_model=AROInfo)
async def get_info():
    """
    Get ARO system information.

    Returns:
        System information including version and features
    """
    try:
        service = get_aro_service()
        info = await service.get_info()
        return info

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# ============================================================================
# Audit Log Endpoints
# ============================================================================


@router.get("/audit", response_model=List[AuditLogEntry])
async def get_audit_log(
    limit: int = Query(100, ge=1, le=1000),
    operation_id: Optional[str] = None
):
    """
    Get audit log entries.

    Args:
        limit: Maximum number of entries to return (1-1000)
        operation_id: Filter by operation ID (optional)

    Returns:
        List of audit log entries (newest first)
    """
    try:
        from .audit_logger import get_audit_logger

        audit_logger = get_audit_logger()

        if operation_id:
            # Get entries for specific operation
            entries = audit_logger.get_entries_for_operation(operation_id)
            # Limit entries
            entries = entries[-limit:]
        else:
            # Get recent entries
            entries = audit_logger.get_recent_entries(limit)

        return entries

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/audit/stats")
async def get_audit_stats():
    """
    Get audit log statistics.

    Returns:
        Audit log statistics
    """
    try:
        from .audit_logger import get_audit_logger

        audit_logger = get_audit_logger()
        stats = audit_logger.get_statistics()
        return stats

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/audit/integrity")
async def check_audit_integrity():
    """
    Check audit log chain integrity.

    Returns:
        Integrity check result
    """
    try:
        from .audit_logger import get_audit_logger

        audit_logger = get_audit_logger()
        is_valid, issues = audit_logger.verify_chain_integrity()

        return {
            "valid": is_valid,
            "issues": issues,
            "total_entries": audit_logger.entry_count,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
