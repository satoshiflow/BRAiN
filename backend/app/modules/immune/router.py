from fastapi import APIRouter

from backend.app.modules.immune.core.service import ImmuneService
from backend.app.modules.immune.schemas import ImmuneEvent, ImmuneHealthSummary

router = APIRouter(prefix="/api/immune", tags=["Immune"])

# Singleton instance (EventStream can be injected at startup)
immune_service = ImmuneService()


@router.post("/event", response_model=int)
async def publish_immune_event(payload: ImmuneEvent) -> int:
    """Publish immune event (async for EventStream integration)"""
    return await immune_service.publish_event(payload)


@router.get("/health", response_model=ImmuneHealthSummary)
def get_immune_health() -> ImmuneHealthSummary:
    """Get immune health summary"""
    return immune_service.health_summary()