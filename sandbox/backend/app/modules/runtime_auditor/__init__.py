"""
Runtime Auditor Module

Lightweight runtime version of the BRAiN Master Audit Tool.

Provides:
- Continuous metric collection during normal operation
- Real-time anomaly detection
- Edge-of-Chaos score calculation
- Integration with Immune System for critical events

Based on: backend/tests/brain_master_audit.py
Adapted for: Production runtime monitoring (no stress tests)
"""

from app.modules.runtime_auditor.service import RuntimeAuditor
from app.modules.runtime_auditor.schemas import (
    RuntimeMetrics,
    AnomalyDetection,
    EdgeOfChaosMetrics,
)

__all__ = [
    "RuntimeAuditor",
    "RuntimeMetrics",
    "AnomalyDetection",
    "EdgeOfChaosMetrics",
]
