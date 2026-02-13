"""
Governor API Router.

Provides REST endpoints for:
- Mode decision (direct vs. rail)
- Shadow evaluation
- Manifest management (Phase 2)
"""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.governor.service import (
    GovernorService,
    get_governor_service,
)
from app.modules.governor.schemas import (
    ModeDecision,
    DecisionRequest,
)

router = APIRouter(prefix="/api/neurorail/v1/governor", tags=["NeuroRail Governor"])


# ============================================================================
# Mode Decision Endpoints
# ============================================================================

@router.post("/decide", response_model=ModeDecision)
async def decide_mode(
    request: DecisionRequest,
    db: AsyncSession = Depends(get_db),
    service: GovernorService = Depends(get_governor_service)
) -> ModeDecision:
    """
    Get mode decision for a job.

    **Phase 1**: Decision is logged but NOT enforced.

    Args:
        request: Decision request with job type and context

    Returns:
        Mode decision (direct or rail)

    Example:
        ```
        POST /api/neurorail/v1/governor/decide
        {
          "job_type": "llm_call",
          "context": {"uses_personal_data": true},
          "shadow_evaluate": false
        }
        ```

        Response:
        ```
        {
          "decision_id": "dec_20251230140000",
          "mode": "rail",
          "reason": "Personal data processing requires governance",
          ...
        }
        ```
    """
    try:
        return await service.decide_mode(request, db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to make decision: {str(e)}"
        )


@router.get("/info", response_model=dict)
async def get_governor_info(
    service: GovernorService = Depends(get_governor_service)
) -> dict:
    """
    Get governor information.

    Returns:
        Governor configuration and status
    """
    return {
        "name": "NeuroRail Governor",
        "version": "0.1.0 (Phase 1 Stub)",
        "phase": "1 - Observation Only",
        "enforcement_enabled": False,
        "active_manifest": {
            "name": service.active_manifest.name,
            "version": service.active_manifest.version,
            "description": service.active_manifest.description,
            "rule_count": len(service.active_manifest.mode_rules)
        },
        "shadow_manifest": {
            "enabled": service.shadow_manifest is not None,
            "version": service.shadow_manifest.version if service.shadow_manifest else None
        }
    }


# Note: Manifest management endpoints will be added in Phase 2
