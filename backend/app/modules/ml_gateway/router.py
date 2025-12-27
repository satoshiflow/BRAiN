"""
ML Gateway API Router

REST API endpoints for ML Gateway service.
"""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status
from loguru import logger

from .schemas import (
    MLEnrichedContext,
    MLGatewayHealth,
    MLGatewayInfo,
    RiskScoreRequest,
    RiskScoreResponse,
)
from .service import get_ml_gateway_service

router = APIRouter(prefix="/api/ml", tags=["ml-gateway"])


@router.get("/health", response_model=MLGatewayHealth)
async def get_health():
    """
    Get ML Gateway health status

    Returns:
        MLGatewayHealth with system metrics
    """
    try:
        service = get_ml_gateway_service()
        return service.get_health()
    except Exception as e:
        logger.error(f"Error getting ML health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve ML Gateway health",
        )


@router.get("/info", response_model=MLGatewayInfo)
async def get_info():
    """
    Get ML Gateway system information

    Returns:
        MLGatewayInfo with configuration
    """
    try:
        service = get_ml_gateway_service()
        return service.get_info()
    except Exception as e:
        logger.error(f"Error getting ML info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve ML Gateway info",
        )


@router.post("/score", response_model=RiskScoreResponse)
async def get_risk_score(request: RiskScoreRequest):
    """
    Get ML risk score for context

    Request body should contain context data for risk assessment.
    Returns risk score with confidence and contributing factors.

    If ML service is unavailable, returns conservative fallback score.

    Args:
        request: RiskScoreRequest with context data

    Returns:
        RiskScoreResponse with risk score and metadata
    """
    try:
        service = get_ml_gateway_service()
        response = await service.get_risk_score(request)
        return response
    except Exception as e:
        logger.error(f"Error computing risk score: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compute risk score",
        )


@router.post("/enrich", response_model=MLEnrichedContext)
async def enrich_context(
    context: Dict[str, Any],
    mission_id: str | None = None,
    agent_id: str | None = None,
    action: str | None = None,
):
    """
    Enrich context with ML risk scores

    Used by Policy Engine and other governance components to
    augment decision context with ML-powered risk assessment.

    Args:
        context: Context data to enrich
        mission_id: Optional mission ID for audit trail
        agent_id: Optional agent ID for audit trail
        action: Optional action being evaluated

    Returns:
        MLEnrichedContext with risk scores added
    """
    try:
        service = get_ml_gateway_service()
        request_info = {
            "mission_id": mission_id,
            "agent_id": agent_id,
            "action": action,
        }
        enriched = await service.enrich_context(context, request_info)
        return enriched
    except Exception as e:
        logger.error(f"Error enriching context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enrich context",
        )
