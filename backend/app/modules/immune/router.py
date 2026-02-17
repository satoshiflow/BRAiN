from fastapi import APIRouter, Request
from typing import Dict, Any

from app.modules.immune.core.service import ImmuneService
from app.modules.immune.schemas import ImmuneEvent, ImmuneHealthSummary
from app.core.rate_limit import limiter, RateLimits

router = APIRouter(prefix="/api/immune", tags=["Immune"])

# Singleton instance (EventStream can be injected at startup)
# PHASE 3: Auto-protection enabled by default
immune_service = ImmuneService(enable_auto_protection=True)


# =============================================================================
# EXISTING ENDPOINTS
# =============================================================================

@router.post("/event", response_model=int)
@limiter.limit(RateLimits.IMMUNE_EVENTS)
async def publish_immune_event(request: Request, payload: ImmuneEvent) -> int:
    """Publish immune event (async for EventStream integration)"""
    return await immune_service.publish_event(payload)


@router.get("/health", response_model=ImmuneHealthSummary)
def get_immune_health() -> ImmuneHealthSummary:
    """Get immune health summary"""
    return immune_service.health_summary()


# =============================================================================
# PHASE 3: SELF-PROTECTION ENDPOINTS
# =============================================================================

@router.get(
    "/protection/status",
    response_model=Dict[str, Any],
    summary="Get self-protection status",
    description="Get current self-protection status including backpressure and circuit breaker state",
)
def get_protection_status() -> Dict[str, Any]:
    """Get self-protection status"""
    return immune_service.get_protection_status()


@router.post(
    "/protection/backpressure/disable",
    summary="Disable backpressure",
    description="Manually disable backpressure (use with caution)",
)
def disable_backpressure() -> dict:
    """Disable backpressure manually"""
    immune_service.disable_backpressure()
    return {"message": "Backpressure disabled", "status": immune_service.get_protection_status()}


@router.post(
    "/protection/circuit-breaker/close",
    summary="Close circuit breaker",
    description="Manually close circuit breaker to resume normal operations",
)
def close_circuit_breaker() -> dict:
    """Close circuit breaker manually"""
    immune_service.close_circuit_breaker()
    return {"message": "Circuit breaker closed", "status": immune_service.get_protection_status()}