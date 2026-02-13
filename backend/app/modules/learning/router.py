"""
Learning Module - API Routes

FastAPI endpoints for Real-Time Learning Loop with PostgreSQL persistence.
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from .schemas import (
    Experiment,
    ExperimentStatus,
    LearningInfo,
    LearningStats,
    LearningStrategy,
    MetricEntry,
    MetricQuery,
    MetricSummary,
    MetricType,
    StrategyStatus,
)
from .service import get_learning_service

router = APIRouter(prefix="/api/learning", tags=["learning"])


# ============================================================================
# Info & Stats
# ============================================================================


@router.get("/info", response_model=LearningInfo)
async def learning_info():
    return LearningInfo()


@router.get("/stats", response_model=LearningStats)
async def learning_stats(db: AsyncSession = Depends(get_db)):
    return await get_learning_service().get_stats(db)


# ============================================================================
# Metrics
# ============================================================================


@router.post("/metrics", response_model=MetricEntry, status_code=status.HTTP_201_CREATED)
async def record_metric(entry: MetricEntry, db: AsyncSession = Depends(get_db)):
    return await get_learning_service().record_metric(db, entry)


@router.post("/metrics/query", response_model=List[MetricEntry])
async def query_metrics(query: MetricQuery, db: AsyncSession = Depends(get_db)):
    return await get_learning_service().query_metrics(db, query)


@router.get("/metrics/{agent_id}/summary")
async def agent_metric_summary(
    agent_id: str,
    metric_type: MetricType = Query(...),
    db: AsyncSession = Depends(get_db),
):
    return await get_learning_service().summarize_metric(db, agent_id, metric_type)


@router.get("/metrics/{agent_id}")
async def agent_metrics(agent_id: str, db: AsyncSession = Depends(get_db)):
    return await get_learning_service().get_agent_metrics(db, agent_id)


# ============================================================================
# Strategies
# ============================================================================


@router.post("/strategies", response_model=LearningStrategy, status_code=status.HTTP_201_CREATED)
async def register_strategy(strategy: LearningStrategy, db: AsyncSession = Depends(get_db)):
    return await get_learning_service().register_strategy(db, strategy)


@router.get("/strategies/{agent_id}", response_model=List[LearningStrategy])
async def list_strategies(
    agent_id: str,
    domain: Optional[str] = Query(None),
    strategy_status: Optional[StrategyStatus] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await get_learning_service().get_strategies(db, agent_id, domain, strategy_status)


@router.post("/strategies/{agent_id}/select")
async def select_strategy(agent_id: str, domain: str = Query(...), db: AsyncSession = Depends(get_db)):
    strategy = await get_learning_service().select_strategy(db, agent_id, domain)
    if not strategy:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No strategies available for this agent/domain")
    return strategy


@router.post("/strategies/{strategy_id}/outcome")
async def record_outcome(strategy_id: str, success: bool = Query(...), db: AsyncSession = Depends(get_db)):
    result = await get_learning_service().record_outcome(db, strategy_id, success)
    if not result:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Strategy '{strategy_id}' not found")
    return result


# ============================================================================
# A/B Testing
# ============================================================================


@router.post("/experiments", response_model=Experiment, status_code=status.HTTP_201_CREATED)
async def create_experiment(experiment: Experiment, db: AsyncSession = Depends(get_db)):
    return await get_learning_service().create_experiment(db, experiment)


@router.post("/experiments/{experiment_id}/start", response_model=Experiment)
async def start_experiment(experiment_id: str, db: AsyncSession = Depends(get_db)):
    exp = await get_learning_service().start_experiment(db, experiment_id)
    if not exp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Experiment not found or not in DRAFT status")
    return exp


@router.get("/experiments/{experiment_id}", response_model=Experiment)
async def get_experiment(experiment_id: str, db: AsyncSession = Depends(get_db)):
    exp = await get_learning_service().get_experiment(db, experiment_id)
    if not exp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Experiment '{experiment_id}' not found")
    return exp


@router.get("/experiments", response_model=List[Experiment])
async def list_experiments(
    agent_id: Optional[str] = Query(None),
    experiment_status: Optional[ExperimentStatus] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await get_learning_service().list_experiments(db, agent_id, experiment_status)


@router.post("/experiments/{experiment_id}/assign")
async def assign_variant(experiment_id: str, db: AsyncSession = Depends(get_db)):
    variant = await get_learning_service().assign_variant(db, experiment_id)
    if not variant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Experiment not running")
    return variant


@router.post("/experiments/{experiment_id}/result")
async def record_experiment_result(
    experiment_id: str,
    variant_id: str = Query(...),
    success: bool = Query(...),
    metric_value: float = Query(0.0),
    db: AsyncSession = Depends(get_db),
):
    ok = await get_learning_service().record_experiment_result(db, experiment_id, variant_id, success, metric_value)
    if not ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Could not record result")
    return {"recorded": True}


@router.post("/experiments/{experiment_id}/evaluate", response_model=Experiment)
async def evaluate_experiment(experiment_id: str, db: AsyncSession = Depends(get_db)):
    """Manually trigger experiment evaluation."""
    exp = await get_learning_service().evaluate_experiment(db, experiment_id)
    if not exp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Experiment '{experiment_id}' not found")
    return exp
