"""
Learning Service - Unified orchestration for the Real-Time Learning Loop.

Combines PerformanceTracker, AdaptiveBehavior, and ABTesting with PostgreSQL persistence.
"""

from __future__ import annotations

import math
import random
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from loguru import logger
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from .models import LearningStrategyORM, ExperimentORM, MetricORM
from .schemas import (
    Experiment,
    ExperimentStatus,
    ExperimentVariant,
    LearningStats,
    LearningStrategy,
    MetricEntry,
    MetricQuery,
    MetricSummary,
    MetricType,
    StrategyStatus,
)

MODULE_VERSION = "2.0.0"


class LearningService:
    """Unified service for BRAiN's Real-Time Learning Loop with PostgreSQL persistence."""

    def __init__(self, exploration_rate: float = 0.2) -> None:
        self._exploration_rate = exploration_rate

        logger.info("🎓 LearningService initialized with PostgreSQL persistence (v%s)", MODULE_VERSION)

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    async def record_metric(self, db: AsyncSession, entry: MetricEntry) -> MetricEntry:
        """Record a metric data point to the database."""
        metric = MetricORM(
            metric_id=entry.metric_id,
            agent_id=entry.agent_id,
            metric_type=entry.metric_type.value if isinstance(entry.metric_type, MetricType) else entry.metric_type,
            value=entry.value,
            unit=entry.unit,
            tags=entry.tags,
            timestamp=datetime.fromtimestamp(entry.timestamp, tz=timezone.utc),
            context=entry.context,
        )
        db.add(metric)
        await db.commit()
        await db.refresh(metric)
        return entry

    async def query_metrics(self, db: AsyncSession, query: MetricQuery) -> List[MetricEntry]:
        """Query metrics from the database with filters."""
        stmt = select(MetricORM)
        
        if query.agent_id:
            stmt = stmt.where(MetricORM.agent_id == query.agent_id)
        if query.metric_type:
            metric_type_value = query.metric_type.value if isinstance(query.metric_type, MetricType) else query.metric_type
            stmt = stmt.where(MetricORM.metric_type == metric_type_value)
        if query.since:
            since_dt = datetime.fromtimestamp(query.since, tz=timezone.utc)
            stmt = stmt.where(MetricORM.timestamp >= since_dt)
        if query.until:
            until_dt = datetime.fromtimestamp(query.until, tz=timezone.utc)
            stmt = stmt.where(MetricORM.timestamp <= until_dt)
        
        stmt = stmt.order_by(MetricORM.timestamp.desc()).limit(query.limit)
        
        result = await db.execute(stmt)
        metrics = result.scalars().all()
        
        return [
            MetricEntry(
                metric_id=m.metric_id,
                agent_id=m.agent_id,
                metric_type=MetricType(m.metric_type),
                value=m.value,
                unit=m.unit,
                tags=m.tags,
                timestamp=m.timestamp.timestamp(),
                context=m.context,
            )
            for m in metrics
        ]

    async def summarize_metric(
        self, db: AsyncSession, agent_id: str, metric_type: MetricType, since: Optional[float] = None,
    ) -> MetricSummary:
        """Compute summary statistics for an agent's metric."""
        metric_type_value = metric_type.value if isinstance(metric_type, MetricType) else metric_type
        
        stmt = select(MetricORM).where(
            and_(
                MetricORM.agent_id == agent_id,
                MetricORM.metric_type == metric_type_value
            )
        )
        
        if since:
            since_dt = datetime.fromtimestamp(since, tz=timezone.utc)
            stmt = stmt.where(MetricORM.timestamp >= since_dt)
        
        stmt = stmt.order_by(MetricORM.timestamp)
        
        result = await db.execute(stmt)
        metrics = result.scalars().all()
        
        if not metrics:
            return MetricSummary(
                metric_type=metric_type,
                agent_id=agent_id,
                count=0,
                mean=0.0,
                min_value=0.0,
                max_value=0.0,
            )
        
        values = sorted(m.value for m in metrics)
        n = len(values)
        
        return MetricSummary(
            metric_type=metric_type,
            agent_id=agent_id,
            count=n,
            mean=sum(values) / n,
            min_value=values[0],
            max_value=values[-1],
            p50=self._percentile(values, 50),
            p95=self._percentile(values, 95),
            p99=self._percentile(values, 99),
            trend=self._compute_trend(metrics),
        )

    async def get_agent_metrics(self, db: AsyncSession, agent_id: str) -> Dict[str, MetricSummary]:
        """Get summaries for all metric types of an agent."""
        stmt = select(MetricORM.metric_type).where(MetricORM.agent_id == agent_id).distinct()
        result = await db.execute(stmt)
        metric_types = result.scalars().all()
        
        result = {}
        for mt in metric_types:
            try:
                metric_type = MetricType(mt)
                result[mt] = await self.summarize_metric(db, agent_id, metric_type)
            except ValueError:
                continue  # Skip unknown metric types
        
        return result

    # ------------------------------------------------------------------
    # Strategies
    # ------------------------------------------------------------------

    async def register_strategy(self, db: AsyncSession, strategy: LearningStrategy) -> LearningStrategy:
        """Register a new learning strategy in the database."""
        # Check for duplicate name for this agent/domain
        stmt = select(LearningStrategyORM).where(
            and_(
                LearningStrategyORM.agent_id == strategy.agent_id,
                LearningStrategyORM.domain == strategy.domain,
                LearningStrategyORM.name == strategy.name
            )
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.warning("Strategy '%s' already exists for %s/%s", strategy.name, strategy.agent_id, strategy.domain)
            return self._strategy_from_orm(existing)
        
        orm_strategy = LearningStrategyORM(
            strategy_id=strategy.strategy_id,
            name=strategy.name,
            description=strategy.description,
            agent_id=strategy.agent_id,
            domain=strategy.domain,
            parameters=strategy.parameters,
            status=strategy.status.value if isinstance(strategy.status, StrategyStatus) else strategy.status,
            karma_score=strategy.karma_score,
            success_count=strategy.success_count,
            failure_count=strategy.failure_count,
            total_applications=strategy.total_applications,
            exploration_weight=strategy.exploration_weight,
            confidence=strategy.confidence,
            created_at=strategy.created_at,
            updated_at=strategy.updated_at,
        )
        
        db.add(orm_strategy)
        await db.commit()
        await db.refresh(orm_strategy)
        
        logger.info("📝 Strategy registered: '%s' for %s/%s", strategy.name, strategy.agent_id, strategy.domain)
        return strategy

    async def select_strategy(self, db: AsyncSession, agent_id: str, domain: str) -> Optional[LearningStrategy]:
        """Select the best strategy using epsilon-greedy with KARMA weighting."""
        usable_statuses = [
            StrategyStatus.ACTIVE.value,
            StrategyStatus.CANDIDATE.value,
            StrategyStatus.EVALUATING.value
        ]
        
        stmt = select(LearningStrategyORM).where(
            and_(
                LearningStrategyORM.agent_id == agent_id,
                LearningStrategyORM.domain == domain,
                LearningStrategyORM.status.in_(usable_statuses)
            )
        )
        
        result = await db.execute(stmt)
        strategies = list(result.scalars().all())
        
        if not strategies:
            return None

        # Epsilon-greedy
        if random.random() < self._exploration_rate:
            # Explore: prefer candidates (untested)
            candidates = [s for s in strategies if s.status == StrategyStatus.CANDIDATE.value]
            if candidates:
                selected = random.choice(candidates)
            else:
                selected = random.choice(strategies)
            logger.debug("🔍 Explore: selected '%s' for %s/%s", selected.name, agent_id, domain)
        else:
            # Exploit: pick highest score
            strategies.sort(key=lambda s: self._compute_score(s), reverse=True)
            selected = strategies[0]
            logger.debug("🎯 Exploit: selected '%s' (score=%.3f) for %s/%s", 
                        selected.name, self._compute_score(selected), agent_id, domain)
        
        # Update application count
        selected.total_applications += 1
        selected.updated_at = datetime.now(timezone.utc)
        await db.commit()
        
        return self._strategy_from_orm(selected)

    async def record_outcome(
        self, db: AsyncSession, strategy_id: str, success: bool, metric_value: Optional[float] = None,
    ) -> Optional[LearningStrategy]:
        """Record outcome of applying a strategy."""
        stmt = select(LearningStrategyORM).where(LearningStrategyORM.strategy_id == strategy_id)
        result = await db.execute(stmt)
        strategy = result.scalar_one_or_none()
        
        if not strategy:
            return None

        # KARMA change per outcome
        KARMA_SUCCESS_BOOST = 2.0
        KARMA_FAILURE_PENALTY = 1.5
        CONFIDENCE_GROWTH = 0.05
        CONFIDENCE_DECAY = 0.02
        MIN_APPLICATIONS_FOR_PROMOTION = 10
        
        if success:
            strategy.success_count += 1
            strategy.karma_score = min(100.0, strategy.karma_score + KARMA_SUCCESS_BOOST)
            strategy.confidence = min(1.0, strategy.confidence + CONFIDENCE_GROWTH)
        else:
            strategy.failure_count += 1
            strategy.karma_score = max(0.0, strategy.karma_score - KARMA_FAILURE_PENALTY)
            strategy.confidence = max(0.0, strategy.confidence - CONFIDENCE_DECAY)
        
        strategy.updated_at = datetime.now(timezone.utc)
        
        # Check for promotion/demotion
        await self._evaluate_strategy(db, strategy, MIN_APPLICATIONS_FOR_PROMOTION)
        
        await db.commit()
        await db.refresh(strategy)
        
        return self._strategy_from_orm(strategy)

    async def get_strategies(
        self, db: AsyncSession, agent_id: str, domain: Optional[str] = None, status: Optional[StrategyStatus] = None,
    ) -> List[LearningStrategy]:
        """Get strategies for an agent, optionally filtered."""
        stmt = select(LearningStrategyORM).where(LearningStrategyORM.agent_id == agent_id)
        
        if domain:
            stmt = stmt.where(LearningStrategyORM.domain == domain)
        
        if status:
            status_value = status.value if isinstance(status, StrategyStatus) else status
            stmt = stmt.where(LearningStrategyORM.status == status_value)
        
        stmt = stmt.order_by(LearningStrategyORM.created_at.desc())
        
        result = await db.execute(stmt)
        strategies = result.scalars().all()
        
        return [self._strategy_from_orm(s) for s in strategies]

    async def get_strategy(self, db: AsyncSession, strategy_id: str) -> Optional[LearningStrategy]:
        """Get a strategy by ID."""
        stmt = select(LearningStrategyORM).where(LearningStrategyORM.strategy_id == strategy_id)
        result = await db.execute(stmt)
        strategy = result.scalar_one_or_none()
        
        if not strategy:
            return None
        
        return self._strategy_from_orm(strategy)

    async def promote_strategy(self, db: AsyncSession, strategy_id: str) -> Optional[LearningStrategy]:
        """Manually promote a strategy."""
        stmt = select(LearningStrategyORM).where(LearningStrategyORM.strategy_id == strategy_id)
        result = await db.execute(stmt)
        strategy = result.scalar_one_or_none()
        
        if not strategy:
            return None
        
        strategy.status = StrategyStatus.PROMOTED.value
        strategy.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(strategy)
        
        return self._strategy_from_orm(strategy)

    async def demote_strategy(self, db: AsyncSession, strategy_id: str) -> Optional[LearningStrategy]:
        """Manually demote a strategy."""
        stmt = select(LearningStrategyORM).where(LearningStrategyORM.strategy_id == strategy_id)
        result = await db.execute(stmt)
        strategy = result.scalar_one_or_none()
        
        if not strategy:
            return None
        
        strategy.status = StrategyStatus.DEMOTED.value
        strategy.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(strategy)
        
        return self._strategy_from_orm(strategy)

    # ------------------------------------------------------------------
    # A/B Testing
    # ------------------------------------------------------------------

    async def create_experiment(self, db: AsyncSession, experiment: Experiment) -> Experiment:
        """Create a new A/B experiment."""
        orm_experiment = ExperimentORM(
            experiment_id=experiment.experiment_id,
            name=experiment.name,
            description=experiment.description,
            agent_id=experiment.agent_id,
            domain=experiment.domain,
            control_strategy_id=experiment.control.strategy_id,
            control_traffic_weight=experiment.control.traffic_weight,
            control_sample_count=experiment.control.sample_count,
            control_success_count=experiment.control.success_count,
            control_total_metric_value=experiment.control.total_metric_value,
            treatment_strategy_id=experiment.treatment.strategy_id,
            treatment_traffic_weight=experiment.treatment.traffic_weight,
            treatment_sample_count=experiment.treatment.sample_count,
            treatment_success_count=experiment.treatment.success_count,
            treatment_total_metric_value=experiment.treatment.total_metric_value,
            metric_type=experiment.metric_type.value if isinstance(experiment.metric_type, MetricType) else experiment.metric_type,
            min_samples=experiment.min_samples,
            confidence_level=experiment.confidence_level,
            status=experiment.status.value if isinstance(experiment.status, ExperimentStatus) else experiment.status,
            winner=experiment.winner,
            p_value=experiment.p_value,
            effect_size=experiment.effect_size,
            created_at=experiment.created_at,
            completed_at=experiment.completed_at,
            updated_at=datetime.now(timezone.utc),
        )
        
        db.add(orm_experiment)
        await db.commit()
        await db.refresh(orm_experiment)
        
        logger.info("🧪 Experiment created: '%s' (%s)", experiment.name, experiment.experiment_id)
        return experiment

    async def start_experiment(self, db: AsyncSession, experiment_id: str) -> Optional[Experiment]:
        """Start an experiment (DRAFT → RUNNING)."""
        stmt = select(ExperimentORM).where(ExperimentORM.experiment_id == experiment_id)
        result = await db.execute(stmt)
        exp = result.scalar_one_or_none()
        
        if not exp or exp.status != ExperimentStatus.DRAFT.value:
            return None
        
        exp.status = ExperimentStatus.RUNNING.value
        exp.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(exp)
        
        logger.info("▶️ Experiment started: '%s'", exp.name)
        return self._experiment_from_orm(exp)

    async def pause_experiment(self, db: AsyncSession, experiment_id: str) -> Optional[Experiment]:
        """Pause a running experiment."""
        stmt = select(ExperimentORM).where(ExperimentORM.experiment_id == experiment_id)
        result = await db.execute(stmt)
        exp = result.scalar_one_or_none()
        
        if not exp or exp.status != ExperimentStatus.RUNNING.value:
            return None
        
        exp.status = ExperimentStatus.PAUSED.value
        exp.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(exp)
        
        return self._experiment_from_orm(exp)

    async def cancel_experiment(self, db: AsyncSession, experiment_id: str) -> Optional[Experiment]:
        """Cancel an experiment."""
        stmt = select(ExperimentORM).where(ExperimentORM.experiment_id == experiment_id)
        result = await db.execute(stmt)
        exp = result.scalar_one_or_none()
        
        if not exp:
            return None
        
        exp.status = ExperimentStatus.CANCELLED.value
        exp.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(exp)
        
        return self._experiment_from_orm(exp)

    async def assign_variant(self, db: AsyncSession, experiment_id: str) -> Optional[ExperimentVariant]:
        """Assign a variant to a new sample using traffic weights."""
        stmt = select(ExperimentORM).where(ExperimentORM.experiment_id == experiment_id)
        result = await db.execute(stmt)
        exp = result.scalar_one_or_none()
        
        if not exp or exp.status != ExperimentStatus.RUNNING.value:
            return None
        
        # Weighted random assignment
        total_weight = exp.control_traffic_weight + exp.treatment_traffic_weight
        if random.random() < (exp.control_traffic_weight / total_weight):
            return self._control_variant_from_orm(exp)
        return self._treatment_variant_from_orm(exp)

    async def record_experiment_result(
        self, db: AsyncSession, experiment_id: str, variant_id: str, success: bool, metric_value: float = 0.0,
    ) -> bool:
        """Record a result for a variant in an experiment."""
        stmt = select(ExperimentORM).where(ExperimentORM.experiment_id == experiment_id)
        result = await db.execute(stmt)
        exp = result.scalar_one_or_none()
        
        if not exp or exp.status != ExperimentStatus.RUNNING.value:
            return False
        
        # Determine which variant
        control_variant = self._control_variant_from_orm(exp)
        treatment_variant = self._treatment_variant_from_orm(exp)
        
        if control_variant.variant_id == variant_id:
            exp.control_sample_count += 1
            if success:
                exp.control_success_count += 1
            exp.control_total_metric_value += metric_value
        elif treatment_variant.variant_id == variant_id:
            exp.treatment_sample_count += 1
            if success:
                exp.treatment_success_count += 1
            exp.treatment_total_metric_value += metric_value
        else:
            return False

        exp.updated_at = datetime.now(timezone.utc)
        
        # Auto-evaluate if both variants have min samples
        if (exp.control_sample_count >= exp.min_samples
                and exp.treatment_sample_count >= exp.min_samples):
            await self._evaluate_experiment(db, exp)
        
        await db.commit()
        await db.refresh(exp)
        
        return True

    async def get_experiment(self, db: AsyncSession, experiment_id: str) -> Optional[Experiment]:
        """Get an experiment by ID."""
        stmt = select(ExperimentORM).where(ExperimentORM.experiment_id == experiment_id)
        result = await db.execute(stmt)
        exp = result.scalar_one_or_none()
        
        if not exp:
            return None
        
        return self._experiment_from_orm(exp)

    async def list_experiments(
        self, db: AsyncSession, agent_id: Optional[str] = None, status: Optional[ExperimentStatus] = None,
    ) -> List[Experiment]:
        """List experiments with optional filtering."""
        stmt = select(ExperimentORM)
        
        if agent_id:
            stmt = stmt.where(ExperimentORM.agent_id == agent_id)
        
        if status:
            status_value = status.value if isinstance(status, ExperimentStatus) else status
            stmt = stmt.where(ExperimentORM.status == status_value)
        
        stmt = stmt.order_by(ExperimentORM.created_at.desc())
        
        result = await db.execute(stmt)
        experiments = result.scalars().all()
        
        return [self._experiment_from_orm(e) for e in experiments]

    async def evaluate_experiment(self, db: AsyncSession, experiment_id: str) -> Optional[Experiment]:
        """Manually trigger evaluation."""
        stmt = select(ExperimentORM).where(ExperimentORM.experiment_id == experiment_id)
        result = await db.execute(stmt)
        exp = result.scalar_one_or_none()
        
        if not exp:
            return None
        
        await self._evaluate_experiment(db, exp)
        await db.commit()
        await db.refresh(exp)
        
        return self._experiment_from_orm(exp)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    async def get_stats(self, db: AsyncSession) -> LearningStats:
        """Get module statistics from the database."""
        # Count strategies
        stmt = select(func.count(LearningStrategyORM.id))
        result = await db.execute(stmt)
        total_strategies = result.scalar() or 0
        
        stmt = select(func.count(LearningStrategyORM.id)).where(
            LearningStrategyORM.status == StrategyStatus.ACTIVE.value
        )
        result = await db.execute(stmt)
        active_strategies = result.scalar() or 0
        
        # Count experiments
        stmt = select(func.count(ExperimentORM.id))
        result = await db.execute(stmt)
        total_experiments = result.scalar() or 0
        
        stmt = select(func.count(ExperimentORM.id)).where(
            ExperimentORM.status == ExperimentStatus.RUNNING.value
        )
        result = await db.execute(stmt)
        running_experiments = result.scalar() or 0
        
        # Count metrics
        stmt = select(func.count(MetricORM.id))
        result = await db.execute(stmt)
        total_metrics = result.scalar() or 0
        
        return LearningStats(
            total_metrics_recorded=total_metrics,
            total_strategies=total_strategies,
            active_strategies=active_strategies,
            total_experiments=total_experiments,
            running_experiments=running_experiments,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_score(strategy: LearningStrategyORM) -> float:
        """Compute composite score for strategy selection."""
        total = strategy.success_count + strategy.failure_count
        success_rate = strategy.success_count / total if total > 0 else 0.5
        
        return (
            strategy.karma_score / 100.0 * 0.4
            + success_rate * 0.35
            + strategy.confidence * 0.25
        )

    @staticmethod
    def _strategy_from_orm(orm: LearningStrategyORM) -> LearningStrategy:
        """Convert ORM model to Pydantic model."""
        return LearningStrategy(
            strategy_id=orm.strategy_id,
            name=orm.name,
            description=orm.description or "",
            agent_id=orm.agent_id,
            domain=orm.domain,
            parameters=orm.parameters,
            status=StrategyStatus(orm.status),
            karma_score=orm.karma_score,
            success_count=orm.success_count,
            failure_count=orm.failure_count,
            total_applications=orm.total_applications,
            exploration_weight=orm.exploration_weight,
            confidence=orm.confidence,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    @staticmethod
    def _experiment_from_orm(orm: ExperimentORM) -> Experiment:
        """Convert ORM model to Pydantic model."""
        return Experiment(
            experiment_id=orm.experiment_id,
            name=orm.name,
            description=orm.description or "",
            agent_id=orm.agent_id,
            domain=orm.domain,
            control=ExperimentVariant(
                variant_id=f"{orm.experiment_id}_control",
                name="Control",
                strategy_id=orm.control_strategy_id,
                traffic_weight=orm.control_traffic_weight,
                sample_count=orm.control_sample_count,
                success_count=orm.control_success_count,
                total_metric_value=orm.control_total_metric_value,
            ),
            treatment=ExperimentVariant(
                variant_id=f"{orm.experiment_id}_treatment",
                name="Treatment",
                strategy_id=orm.treatment_strategy_id,
                traffic_weight=orm.treatment_traffic_weight,
                sample_count=orm.treatment_sample_count,
                success_count=orm.treatment_success_count,
                total_metric_value=orm.treatment_total_metric_value,
            ),
            metric_type=MetricType(orm.metric_type),
            min_samples=orm.min_samples,
            confidence_level=orm.confidence_level,
            status=ExperimentStatus(orm.status),
            winner=orm.winner,
            p_value=orm.p_value,
            effect_size=orm.effect_size,
            created_at=orm.created_at,
            completed_at=orm.completed_at,
        )

    @staticmethod
    def _control_variant_from_orm(orm: ExperimentORM) -> ExperimentVariant:
        """Extract control variant from ORM model."""
        return ExperimentVariant(
            variant_id=f"{orm.experiment_id}_control",
            name="Control",
            strategy_id=orm.control_strategy_id,
            traffic_weight=orm.control_traffic_weight,
            sample_count=orm.control_sample_count,
            success_count=orm.control_success_count,
            total_metric_value=orm.control_total_metric_value,
        )

    @staticmethod
    def _treatment_variant_from_orm(orm: ExperimentORM) -> ExperimentVariant:
        """Extract treatment variant from ORM model."""
        return ExperimentVariant(
            variant_id=f"{orm.experiment_id}_treatment",
            name="Treatment",
            strategy_id=orm.treatment_strategy_id,
            traffic_weight=orm.treatment_traffic_weight,
            sample_count=orm.treatment_sample_count,
            success_count=orm.treatment_success_count,
            total_metric_value=orm.treatment_total_metric_value,
        )

    async def _evaluate_strategy(self, db: AsyncSession, strategy: LearningStrategyORM, min_applications: int) -> None:
        """Evaluate whether to promote or demote a strategy."""
        if strategy.total_applications < min_applications:
            return
        
        total = strategy.success_count + strategy.failure_count
        success_rate = strategy.success_count / total if total > 0 else 0.5
        
        if strategy.status == StrategyStatus.CANDIDATE.value:
            # Promote candidates with good performance
            if success_rate >= 0.7 and strategy.karma_score >= 60.0:
                strategy.status = StrategyStatus.ACTIVE.value
                logger.info("⬆️ Strategy promoted to ACTIVE: '%s' (sr=%.2f, karma=%.1f)",
                            strategy.name, success_rate, strategy.karma_score)
        
        elif strategy.status == StrategyStatus.ACTIVE.value:
            # Demote active strategies with bad performance
            if success_rate < 0.3 and strategy.karma_score < 30.0:
                strategy.status = StrategyStatus.DEMOTED.value
                logger.info("⬇️ Strategy demoted: '%s' (sr=%.2f, karma=%.1f)",
                            strategy.name, success_rate, strategy.karma_score)

    async def _evaluate_experiment(self, db: AsyncSession, exp: ExperimentORM) -> None:
        """Evaluate experiment using Z-test for proportions."""
        n_c = exp.control_sample_count
        n_t = exp.treatment_sample_count
        s_c = exp.control_success_count
        s_t = exp.treatment_success_count
        
        if n_c == 0 or n_t == 0:
            return
        
        p_c = s_c / n_c
        p_t = s_t / n_t
        
        # Pooled proportion
        p_pool = (s_c + s_t) / (n_c + n_t)
        
        if p_pool == 0 or p_pool == 1:
            return  # Can't compute z-score
        
        # Standard error
        se = math.sqrt(p_pool * (1 - p_pool) * (1 / n_c + 1 / n_t))
        if se == 0:
            return
        
        # Z-score
        z = (p_t - p_c) / se
        
        # Two-tailed p-value approximation
        p_value = 2 * (1 - self._normal_cdf(abs(z)))
        
        exp.p_value = round(p_value, 6)
        exp.effect_size = round(p_t - p_c, 4)
        
        # Significance check
        alpha = 1 - exp.confidence_level
        if p_value < alpha:
            # Statistically significant
            if p_t > p_c:
                exp.winner = exp.treatment_strategy_id
            else:
                exp.winner = exp.control_strategy_id
            
            exp.status = ExperimentStatus.COMPLETED.value
            exp.completed_at = datetime.now(timezone.utc)
            
            winner_name = "treatment" if exp.winner == exp.treatment_strategy_id else "control"
            logger.info(
                "🏆 Experiment '%s' completed: winner=%s (p=%.4f, effect=%.4f)",
                exp.name,
                winner_name,
                p_value,
                exp.effect_size,
            )

    @staticmethod
    def _normal_cdf(x: float) -> float:
        """Approximate standard normal CDF using error function."""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    @staticmethod
    def _percentile(sorted_values: List[float], p: float) -> float:
        """Compute p-th percentile from sorted values."""
        if not sorted_values:
            return 0.0
        k = (len(sorted_values) - 1) * (p / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_values[int(k)]
        return sorted_values[f] * (c - k) + sorted_values[c] * (k - f)

    @staticmethod
    def _compute_trend(metrics: List[MetricORM]) -> float:
        """
        Compute trend as slope of linear regression on values over time.
        Positive = improving (for metrics where higher is better).
        Returns normalized slope per hour.
        """
        if len(metrics) < 3:
            return 0.0
        
        n = len(metrics)
        t0 = metrics[0].timestamp.timestamp()
        xs = [(m.timestamp.timestamp() - t0) / 3600.0 for m in metrics]  # hours
        ys = [m.value for m in metrics]
        
        x_mean = sum(xs) / n
        y_mean = sum(ys) / n
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
        denominator = sum((x - x_mean) ** 2 for x in xs)
        
        if denominator == 0:
            return 0.0
        return numerator / denominator


# ============================================================================
# Singleton
# ============================================================================

_service: Optional[LearningService] = None


def get_learning_service() -> LearningService:
    global _service
    if _service is None:
        _service = LearningService()
    return _service
