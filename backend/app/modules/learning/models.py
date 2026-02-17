"""
Learning Module - Database Models

SQLAlchemy ORM models for:
- Learning strategies with adaptive behavior tracking
- A/B experiments with statistical evaluation
- Performance metrics with time-series data
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Column,
    String,
    Text,
    Float,
    Integer,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    Index,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class StrategyStatus(str):
    """Strategy lifecycle status values"""
    CANDIDATE = "candidate"
    ACTIVE = "active"
    EVALUATING = "evaluating"
    PROMOTED = "promoted"
    DEMOTED = "demoted"
    RETIRED = "retired"


class ExperimentStatus(str):
    """Experiment lifecycle status values"""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MetricType(str):
    """Metric type values"""
    LATENCY = "latency"
    SUCCESS_RATE = "success_rate"
    TOKEN_USAGE = "token_usage"
    QUALITY_SCORE = "quality_score"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    KARMA_DELTA = "karma_delta"
    COST = "cost"
    CUSTOM = "custom"


class LearningStrategyORM(Base):
    """
    Learning strategy database model.
    
    Stores adaptive behavior strategies with performance tracking
    and KARMA scoring for intelligent strategy selection.
    """
    __tablename__ = "learning_strategies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    agent_id = Column(String(100), nullable=False, index=True)
    domain = Column(String(50), nullable=False, default="general", index=True)
    
    # Strategy parameters (the "knobs" to tune)
    parameters = Column(JSONB, nullable=False, default=dict)
    
    # Performance tracking
    status = Column(
        String(20),
        nullable=False,
        default=StrategyStatus.CANDIDATE,
        index=True
    )
    karma_score = Column(Float, nullable=False, default=50.0)
    success_count = Column(Integer, nullable=False, default=0)
    failure_count = Column(Integer, nullable=False, default=0)
    total_applications = Column(Integer, nullable=False, default=0)
    
    # Adaptive weights
    exploration_weight = Column(Float, nullable=False, default=0.3)
    confidence = Column(Float, nullable=False, default=0.0)
    
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    experiments_as_control = relationship(
        "ExperimentORM",
        foreign_keys="ExperimentORM.control_strategy_id",
        back_populates="control_strategy"
    )
    experiments_as_treatment = relationship(
        "ExperimentORM",
        foreign_keys="ExperimentORM.treatment_strategy_id",
        back_populates="treatment_strategy"
    )
    
    __table_args__ = (
        Index("idx_strategies_agent_domain", "agent_id", "domain"),
        Index("idx_strategies_status_domain", "status", "domain"),
        Index("idx_strategies_agent_status", "agent_id", "status"),
    )
    
    def __repr__(self) -> str:
        return f"<LearningStrategy(id={self.strategy_id}, name={self.name}, agent={self.agent_id}, status={self.status})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {
            "id": str(self.id),
            "strategy_id": self.strategy_id,
            "name": self.name,
            "description": self.description,
            "agent_id": self.agent_id,
            "domain": self.domain,
            "parameters": self.parameters,
            "status": self.status,
            "karma_score": self.karma_score,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "total_applications": self.total_applications,
            "exploration_weight": self.exploration_weight,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ExperimentORM(Base):
    """
    A/B experiment database model.
    
    Stores experiments comparing two strategy variants (control vs treatment)
    with statistical evaluation and traffic splitting.
    """
    __tablename__ = "ab_experiments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    agent_id = Column(String(100), nullable=False, index=True)
    domain = Column(String(50), nullable=False, default="general")
    
    # Control variant (reference strategy)
    control_strategy_id = Column(String(50), ForeignKey("learning_strategies.strategy_id"), nullable=False)
    control_traffic_weight = Column(Float, nullable=False, default=0.5)
    control_sample_count = Column(Integer, nullable=False, default=0)
    control_success_count = Column(Integer, nullable=False, default=0)
    control_total_metric_value = Column(Float, nullable=False, default=0.0)
    
    # Treatment variant (new strategy to test)
    treatment_strategy_id = Column(String(50), ForeignKey("learning_strategies.strategy_id"), nullable=False)
    treatment_traffic_weight = Column(Float, nullable=False, default=0.5)
    treatment_sample_count = Column(Integer, nullable=False, default=0)
    treatment_success_count = Column(Integer, nullable=False, default=0)
    treatment_total_metric_value = Column(Float, nullable=False, default=0.0)
    
    # Configuration
    metric_type = Column(String(20), nullable=False, default=MetricType.SUCCESS_RATE)
    min_samples = Column(Integer, nullable=False, default=30)
    confidence_level = Column(Float, nullable=False, default=0.95)
    status = Column(String(20), nullable=False, default=ExperimentStatus.DRAFT, index=True)
    
    # Results
    winner = Column(String(50), nullable=True)  # strategy_id of winner
    p_value = Column(Float, nullable=True)
    effect_size = Column(Float, nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    control_strategy = relationship(
        "LearningStrategyORM",
        foreign_keys=[control_strategy_id],
        back_populates="experiments_as_control"
    )
    treatment_strategy = relationship(
        "LearningStrategyORM",
        foreign_keys=[treatment_strategy_id],
        back_populates="experiments_as_treatment"
    )
    
    __table_args__ = (
        Index("idx_experiments_agent_status", "agent_id", "status"),
        Index("idx_experiments_domain_status", "domain", "status"),
        Index("idx_experiments_status_created", "status", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<Experiment(id={self.experiment_id}, name={self.name}, status={self.status})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {
            "id": str(self.id),
            "experiment_id": self.experiment_id,
            "name": self.name,
            "description": self.description,
            "agent_id": self.agent_id,
            "domain": self.domain,
            "control_strategy_id": self.control_strategy_id,
            "control_traffic_weight": self.control_traffic_weight,
            "control_sample_count": self.control_sample_count,
            "control_success_count": self.control_success_count,
            "control_total_metric_value": self.control_total_metric_value,
            "treatment_strategy_id": self.treatment_strategy_id,
            "treatment_traffic_weight": self.treatment_traffic_weight,
            "treatment_sample_count": self.treatment_sample_count,
            "treatment_success_count": self.treatment_success_count,
            "treatment_total_metric_value": self.treatment_total_metric_value,
            "metric_type": self.metric_type,
            "min_samples": self.min_samples,
            "confidence_level": self.confidence_level,
            "status": self.status,
            "winner": self.winner,
            "p_value": self.p_value,
            "effect_size": self.effect_size,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class MetricORM(Base):
    """
    Performance metric database model.
    
    Stores time-series metric data points from agents
    for performance tracking and trend analysis.
    """
    __tablename__ = "learning_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_id = Column(String(50), unique=True, nullable=False, index=True)
    agent_id = Column(String(100), nullable=False, index=True)
    metric_type = Column(String(20), nullable=False, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False, default="")
    tags = Column(JSONB, nullable=False, default=dict)
    timestamp = Column(DateTime, nullable=False, index=True)
    context = Column(JSONB, nullable=False, default=dict)
    
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index("idx_metrics_agent_type", "agent_id", "metric_type"),
        Index("idx_metrics_agent_timestamp", "agent_id", "timestamp"),
        Index("idx_metrics_type_timestamp", "metric_type", "timestamp"),
        Index("idx_metrics_timestamp", "timestamp"),
    )
    
    def __repr__(self) -> str:
        return f"<Metric(id={self.metric_id}, agent={self.agent_id}, type={self.metric_type}, value={self.value})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {
            "id": str(self.id),
            "metric_id": self.metric_id,
            "agent_id": self.agent_id,
            "metric_type": self.metric_type,
            "value": self.value,
            "unit": self.unit,
            "tags": self.tags,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "context": self.context,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
