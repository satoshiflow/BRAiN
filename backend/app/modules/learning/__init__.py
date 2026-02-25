"""
Learning Module - Real-Time Learning Loop

BRAiN's learning system combining:
- Performance tracking with PostgreSQL persistence
- Adaptive behavior with KARMA integration
- A/B testing with statistical evaluation

Models, schemas, and service for intelligent agent learning.
"""

from .models import LearningStrategyORM, ExperimentORM, MetricORM
from .schemas import (
    Experiment,
    ExperimentStatus,
    ExperimentVariant,
    LearningInfo,
    LearningStats,
    LearningStrategy,
    MetricEntry,
    MetricQuery,
    MetricSummary,
    MetricType,
    StrategyStatus,
)
from .service import LearningService, get_learning_service
from .router import router

# Note: Legacy classes (PerformanceTracker, AdaptiveBehavior, ABTesting)
# are deprecated. Use LearningService instead.

__all__ = [
    # ORM Models
    "LearningStrategyORM",
    "ExperimentORM",
    "MetricORM",
    # Schemas
    "Experiment",
    "ExperimentStatus",
    "ExperimentVariant",
    "LearningInfo",
    "LearningStats",
    "LearningStrategy",
    "MetricEntry",
    "MetricQuery",
    "MetricSummary",
    "MetricType",
    "StrategyStatus",
    # Service
    "LearningService",
    "get_learning_service",
    # Router
    "router",
]
