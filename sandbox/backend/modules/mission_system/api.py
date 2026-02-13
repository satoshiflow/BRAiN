from fastapi import APIRouter
from .services import get_orchestrator

router = APIRouter()

@router.get("/info")
def mission_info():
    orchestrator = get_orchestrator()
    return {
        "name": "Mission System",
        "version": "1.0.0",
        # optional: etwas Debug/Status mitgeben
        "metrics": orchestrator.orchestration_metrics if hasattr(orchestrator, "orchestration_metrics") else {}
    }

@router.get("/health")
def mission_health():
    return {"status": "ok"}
