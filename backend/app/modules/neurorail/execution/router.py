"""
NeuroRail Execution API Router.

Provides REST endpoints for:
- Executing jobs with observation
- Getting execution status

Note: Direct execution via API is typically not needed - this is mainly
for testing and manual invocation. Normal flow is internal service calls.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.neurorail.execution.service import (
    ExecutionService,
    get_execution_service,
)
from app.modules.neurorail.execution.schemas import (
    ExecutionContext,
    ExecutionResult,
)

router = APIRouter(prefix="/api/neurorail/v1/execution", tags=["NeuroRail Execution"])


# ============================================================================
# Status Endpoints
# ============================================================================

@router.get("/status/{attempt_id}", response_model=dict)
async def get_execution_status(
    attempt_id: str,
    service: ExecutionService = Depends(get_execution_service)
) -> dict:
    """
    Get execution status for an attempt.

    Args:
        attempt_id: Attempt identifier

    Returns:
        Execution status (retrieves from lifecycle + telemetry)
    """
    # This would typically fetch from lifecycle service
    # For now, return a placeholder
    return {
        "attempt_id": attempt_id,
        "status": "not_implemented",
        "message": "Status endpoint is a placeholder - use lifecycle and telemetry APIs"
    }


# Note: Execution itself is not exposed as a direct API endpoint
# (jobs are executed internally via service, not via HTTP POST)
