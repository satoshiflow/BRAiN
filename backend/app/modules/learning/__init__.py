"""
Real-Time Learning Loop - Sprint 7B

Online learning, performance metrics, KARMA-integrated adaptive behavior,
and A/B testing for BRAIN agents.

Architecture:
    PerformanceTracker  → Metric collection and time-series aggregation
    AdaptiveBehavior    → KARMA-scored strategy selection and adaptation
    ABTesting           → Experiment framework with statistical evaluation
    LearningService     → Unified orchestration layer
"""

from .schemas import (
    MetricEntry,
    MetricType,
    LearningStrategy,
    Experiment,
    ExperimentVariant,
)

__all__ = [
    "MetricEntry",
    "MetricType",
    "LearningStrategy",
    "Experiment",
    "ExperimentVariant",
]
