"""
Runtime Auditor Router

API endpoints for runtime audit metrics and anomaly detection.
"""

from fastapi import APIRouter, Depends
from typing import Optional

from app.modules.runtime_auditor.service import RuntimeAuditor
from app.modules.runtime_auditor.schemas import (
    RuntimeMetrics,
    RuntimeAuditorStatus,
)

router = APIRouter(prefix="/api/audit/runtime", tags=["Runtime Auditor"])

# Singleton instance
_runtime_auditor: Optional[RuntimeAuditor] = None


def get_runtime_auditor() -> RuntimeAuditor:
    """Dependency injection for RuntimeAuditor"""
    global _runtime_auditor
    if _runtime_auditor is None:
        # Initialize with Immune System integration
        try:
            from app.modules.immune.core.service import ImmuneService
            immune_service = ImmuneService()
        except:
            immune_service = None

        _runtime_auditor = RuntimeAuditor(
            collection_interval=60.0,  # Collect every minute
            immune_service=immune_service,
        )

    return _runtime_auditor


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get(
    "/metrics",
    response_model=RuntimeMetrics,
    summary="Get current runtime metrics",
    description="""
    Get current runtime audit metrics including:
    - Performance metrics (latency, throughput)
    - Resource metrics (memory, CPU)
    - Queue metrics
    - Edge-of-Chaos score
    - Detected anomalies
    """,
)
async def get_metrics(
    auditor: RuntimeAuditor = Depends(get_runtime_auditor),
) -> RuntimeMetrics:
    """Get current runtime metrics"""
    return await auditor.get_current_metrics()


@router.get(
    "/status",
    response_model=RuntimeAuditorStatus,
    summary="Get auditor status",
    description="Get Runtime Auditor status and collection statistics",
)
def get_status(
    auditor: RuntimeAuditor = Depends(get_runtime_auditor),
) -> RuntimeAuditorStatus:
    """Get auditor status"""
    return auditor.get_status()


@router.post(
    "/start",
    summary="Start background collection",
    description="Start background metric collection loop",
)
async def start_collection(
    auditor: RuntimeAuditor = Depends(get_runtime_auditor),
) -> dict:
    """Start background collection"""
    await auditor.start()
    return {"message": "Background collection started", "running": True}


@router.post(
    "/stop",
    summary="Stop background collection",
    description="Stop background metric collection loop",
)
async def stop_collection(
    auditor: RuntimeAuditor = Depends(get_runtime_auditor),
) -> dict:
    """Stop background collection"""
    await auditor.stop()
    return {"message": "Background collection stopped", "running": False}


@router.post(
    "/sample/latency",
    summary="Record latency sample",
    description="Record a request latency sample for performance tracking",
)
def sample_latency(
    latency_ms: float,
    auditor: RuntimeAuditor = Depends(get_runtime_auditor),
) -> dict:
    """Record latency sample"""
    auditor.sample_latency(latency_ms)
    return {"message": "Latency sample recorded", "latency_ms": latency_ms}


@router.post(
    "/sample/queue",
    summary="Record queue depth sample",
    description="Record mission queue depth sample for queue tracking",
)
def sample_queue_depth(
    depth: int,
    auditor: RuntimeAuditor = Depends(get_runtime_auditor),
) -> dict:
    """Record queue depth sample"""
    auditor.sample_queue_depth(depth)
    return {"message": "Queue depth sample recorded", "depth": depth}
