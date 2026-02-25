"""
Async integration tests for Learning module using actual DB.
Tests the LearningService with SQLAlchemy ORM.
"""

import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4

from app.modules.learning.models import Base
from app.modules.learning.service import LearningService
from app.modules.learning.schemas import (
    LearningStrategy,
    Experiment,
    ExperimentVariant,
    MetricEntry,
    MetricType,
    StrategyStatus,
    ExperimentStatus,
)


@pytest.fixture
async def async_db_session():
    """Create in-memory SQLite DB for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def learning_service():
    """Create a LearningService instance."""
    return LearningService()


@pytest.mark.asyncio
async def test_record_metric_persistence(async_db_session: AsyncSession, learning_service: LearningService):
    """Test that metrics are persisted to DB."""
    metric_entry = MetricEntry(
        metric_id=str(uuid4()),
        agent_id="test-agent-1",
        metric_type=MetricType.ACCURACY,
        value=0.95,
        unit="ratio",
        tags={},
        timestamp=datetime.now().timestamp(),
        context={"model_version": "v1"}
    )

    # Record metric
    result = await learning_service.record_metric(
        db=async_db_session,
        entry=metric_entry
    )

    assert result is not None
    assert result.value == 0.95
    assert result.agent_id == "test-agent-1"


@pytest.mark.asyncio
async def test_query_metrics_by_agent(async_db_session: AsyncSession, learning_service: LearningService):
    """Test querying metrics for specific agent."""
    # Record multiple metrics
    for i in range(5):
        metric_entry = MetricEntry(
            metric_id=str(uuid4()),
            agent_id="test-agent-multi",
            metric_type=MetricType.SUCCESS_RATE,
            value=0.80 + (i * 0.02),
            unit="ratio",
            tags={},
            timestamp=datetime.now().timestamp(),
            context={}
        )
        await learning_service.record_metric(
            db=async_db_session,
            entry=metric_entry
        )

    # Query them back
    from app.modules.learning.schemas import MetricQuery
    query = MetricQuery(
        agent_id="test-agent-multi",
        metric_type=MetricType.SUCCESS_RATE,
        limit=10
    )
    query_result = await learning_service.query_metrics(
        db=async_db_session,
        query=query
    )

    assert len(query_result) == 5
    assert query_result[0].value >= 0.80


@pytest.mark.asyncio
async def test_register_and_select_strategy(async_db_session: AsyncSession, learning_service: LearningService):
    """Test strategy registration and selection."""
    # Register strategy
    strat = LearningStrategy(
        strategy_id=str(uuid4()),
        name="nav-strategy-1",
        description="Navigation strategy",
        agent_id="test-agent-strategy",
        domain="navigation",
        parameters={"learning_rate": 0.1, "discount": 0.99},
        status=StrategyStatus.CANDIDATE,
        karma_score=50.0,
        success_count=0,
        failure_count=0,
        total_applications=0,
        exploration_weight=0.5,
        confidence=0.5,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

    registered = await learning_service.register_strategy(
        db=async_db_session,
        strategy=strat
    )

    assert registered is not None
    assert registered.domain == "navigation"

    # Select it (epsilon-greedy should pick it)
    selected = await learning_service.select_strategy(
        db=async_db_session,
        agent_id="test-agent-strategy",
        domain="navigation"
    )

    assert selected is not None
    assert selected.strategy_id == strat.strategy_id


@pytest.mark.asyncio
async def test_record_strategy_outcome(async_db_session: AsyncSession, learning_service: LearningService):
    """Test recording success/failure outcomes for strategies."""
    # Register strategy
    strat = LearningStrategy(
        strategy_id=str(uuid4()),
        name="outcome-strategy",
        description="Test strategy",
        agent_id="test-agent-outcome",
        domain="planning",
        parameters={},
        status=StrategyStatus.ACTIVE,
        karma_score=50.0,
        success_count=0,
        failure_count=0,
        total_applications=0,
        exploration_weight=0.5,
        confidence=0.5,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

    registered = await learning_service.register_strategy(
        db=async_db_session,
        strategy=strat
    )

    # Record success
    await learning_service.record_outcome(
        db=async_db_session,
        strategy_id=registered.strategy_id,
        success=True
    )

    # Record failure
    await learning_service.record_outcome(
        db=async_db_session,
        strategy_id=registered.strategy_id,
        success=False
    )

    # Verify counts updated
    updated = await learning_service.get_strategy(
        db=async_db_session,
        strategy_id=registered.strategy_id
    )

    assert updated.success_count == 1
    assert updated.failure_count == 1


@pytest.mark.asyncio
async def test_create_ab_experiment(async_db_session: AsyncSession, learning_service: LearningService):
    """Test creating and starting A/B experiments."""
    exp = Experiment(
        experiment_id=str(uuid4()),
        name="test-ab-experiment",
        description="Test A/B experiment",
        agent_id="test-agent-ab",
        domain="resource_allocation",
        control=ExperimentVariant(
            variant_id="control",
            name="Control",
            strategy_id="strategy-1",
            traffic_weight=50,
            sample_count=0,
            success_count=0,
            total_metric_value=0.0
        ),
        treatment=ExperimentVariant(
            variant_id="treatment",
            name="Treatment",
            strategy_id="strategy-2",
            traffic_weight=50,
            sample_count=0,
            success_count=0,
            total_metric_value=0.0
        ),
        metric_type=MetricType.SUCCESS_RATE,
        min_samples=10,
        confidence_level=0.95,
        status=ExperimentStatus.DRAFT,
        winner=None,
        p_value=None,
        effect_size=None,
        created_at=datetime.now(),
        completed_at=None
    )

    created = await learning_service.create_experiment(
        db=async_db_session,
        experiment=exp
    )

    assert created is not None
    assert created.domain == "resource_allocation"
    assert created.status == ExperimentStatus.DRAFT

    # Start experiment
    started = await learning_service.start_experiment(
        db=async_db_session,
        experiment_id=created.experiment_id
    )

    assert started is not None
    assert started.status == ExperimentStatus.RUNNING


@pytest.mark.asyncio
async def test_ab_experiment_result_recording(async_db_session: AsyncSession, learning_service: LearningService):
    """Test recording results for A/B experiment variants."""
    # Create and start experiment
    exp = Experiment(
        experiment_id=str(uuid4()),
        name="test-results-experiment",
        description="Test recording results",
        agent_id="test-agent-results",
        domain="testing",
        control=ExperimentVariant(
            variant_id="control",
            name="Control",
            strategy_id="strategy-1",
            traffic_weight=50,
            sample_count=0,
            success_count=0,
            total_metric_value=0.0
        ),
        treatment=ExperimentVariant(
            variant_id="treatment",
            name="Treatment",
            strategy_id="strategy-2",
            traffic_weight=50,
            sample_count=0,
            success_count=0,
            total_metric_value=0.0
        ),
        metric_type=MetricType.SUCCESS_RATE,
        min_samples=100,
        confidence_level=0.95,
        status=ExperimentStatus.DRAFT,
        winner=None,
        p_value=None,
        effect_size=None,
        created_at=datetime.now(),
        completed_at=None
    )

    created = await learning_service.create_experiment(
        db=async_db_session,
        experiment=exp
    )

    started = await learning_service.start_experiment(
        db=async_db_session,
        experiment_id=created.experiment_id
    )

    # Get variant IDs
    control_variant_id = f"{created.experiment_id}_control"
    treatment_variant_id = f"{created.experiment_id}_treatment"

    # Record control variant results
    for i in range(10):
        await learning_service.record_experiment_result(
            db=async_db_session,
            experiment_id=created.experiment_id,
            variant_id=control_variant_id,
            success=(i % 2 == 0),
            metric_value=0.5 if i % 2 == 0 else 0.3
        )

    # Record treatment variant results
    for i in range(10):
        await learning_service.record_experiment_result(
            db=async_db_session,
            experiment_id=created.experiment_id,
            variant_id=treatment_variant_id,
            success=(i % 3 == 0),
            metric_value=0.6 if i % 3 == 0 else 0.4
        )

    # Retrieve and verify
    updated = await learning_service.get_experiment(
        db=async_db_session,
        experiment_id=created.experiment_id
    )

    # Check that results were recorded
    assert updated is not None
    assert updated.control.sample_count == 10
    assert updated.treatment.sample_count == 10
    assert updated.control.success_count > 0
    assert updated.treatment.success_count > 0
