from fastapi import APIRouter

from app.modules.immune.core.service import ImmuneService
from app.modules.immune.schemas import ImmuneEvent, ImmuneHealthSummary

router = APIRouter(prefix="/api/immune", tags=["Immune"])

immune_service = ImmuneService()


@router.post("/event", response_model=int)
def publish_immune_event(payload: ImmuneEvent) -> int:
    return immune_service.publish_event(payload)


@router.get("/health", response_model=ImmuneHealthSummary)
def get_immune_health() -> ImmuneHealthSummary:
    return immune_service.health_summary()