"""
Learning Module - API Routes

FastAPI endpoints for Real-Time Learning Loop.
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status

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
async def learning_stats():
    return get_learning_service().get_stats()


# ============================================================================
# Metrics
# ============================================================================


@router.post("/metrics", response_model=MetricEntry, status_code=status.HTTP_201_CREATED)
async def record_metric(entry: MetricEntry):
    return get_learning_service().record_metric(entry)


@router.post("/metrics/query", response_model=List[MetricEntry])
async def query_metrics(query: MetricQuery):
    return get_learning_service().query_metrics(query)


@router.get("/metrics/{agent_id}/summary")
async def agent_metric_summary(
    agent_id: str,
    metric_type: MetricType = Query(...),
):
    return get_learning_service().summarize_metric(agent_id, metric_type)


@router.get("/metrics/{agent_id}")
async def agent_metrics(agent_id: str):
    return get_learning_service().get_agent_metrics(agent_id)


# ============================================================================
# Strategies
# ============================================================================


@router.post("/strategies", response_model=LearningStrategy, status_code=status.HTTP_201_CREATED)
async def register_strategy(strategy: LearningStrategy):
    return get_learning_service().register_strategy(strategy)


@router.get("/strategies/{agent_id}", response_model=List[LearningStrategy])
async def list_strategies(
    agent_id: str,
    domain: Optional[str] = Query(None),
    strategy_status: Optional[StrategyStatus] = Query(None),
):
    return get_learning_service().get_strategies(agent_id, domain, strategy_status)


@router.post("/strategies/{agent_id}/select")
async def select_strategy(agent_id: str, domain: str = Query(...)):
    strategy = get_learning_service().select_strategy(agent_id, domain)
    if not strategy:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No strategies available for this agent/domain")
    return strategy


@router.post("/strategies/{strategy_id}/outcome")
async def record_outcome(strategy_id: str, success: bool = Query(...)):
    result = get_learning_service().record_outcome(strategy_id, success)
    if not result:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Strategy '{strategy_id}' not found")
    return result


# ============================================================================
# A/B Testing
# ============================================================================


@router.post("/experiments", response_model=Experiment, status_code=status.HTTP_201_CREATED)
async def create_experiment(experiment: Experiment):
    return get_learning_service().create_experiment(experiment)


@router.post("/experiments/{experiment_id}/start", response_model=Experiment)
async def start_experiment(experiment_id: str):
    exp = get_learning_service().start_experiment(experiment_id)
    if not exp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Experiment not found or not in DRAFT status")
    return exp


@router.get("/experiments/{experiment_id}", response_model=Experiment)
async def get_experiment(experiment_id: str):
    exp = get_learning_service().get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Experiment '{experiment_id}' not found")
    return exp


@router.get("/experiments", response_model=List[Experiment])
async def list_experiments(
    agent_id: Optional[str] = Query(None),
    experiment_status: Optional[ExperimentStatus] = Query(None),
):
    return get_learning_service().list_experiments(agent_id, experiment_status)


@router.post("/experiments/{experiment_id}/assign")
async def assign_variant(experiment_id: str):
    variant = get_learning_service().assign_variant(experiment_id)
    if not variant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Experiment not running")
    return variant


@router.post("/experiments/{experiment_id}/result")
async def record_experiment_result(
    experiment_id: str,
    variant_id: str = Query(...),
    success: bool = Query(...),
    metric_value: float = Query(0.0),
):
    ok = get_learning_service().record_experiment_result(experiment_id, variant_id, success, metric_value)
    if not ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Could not record result")
    return {"recorded": True}
