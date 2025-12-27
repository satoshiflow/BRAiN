"""
Risk Scoring Module - Data Models

Schemas for ML-powered risk analysis.
"""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class DAGAnalysisResult(BaseModel):
    """Result of DAG/IR anomaly detection"""

    risk_score: float = Field(..., ge=0.0, le=1.0, description="Anomaly risk score")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence")
    anomalies_detected: List[str] = Field(
        default_factory=list, description="List of detected anomalies"
    )
    features: Dict[str, float] = Field(
        default_factory=dict, description="Extracted features"
    )


class RiskFactorContribution(BaseModel):
    """Individual risk factor with contribution weight"""

    factor: str = Field(..., description="Risk factor name")
    weight: float = Field(..., ge=0.0, le=1.0, description="Contribution weight")
    description: str = Field(default="", description="Human-readable explanation")
    raw_value: Any = Field(default=None, description="Raw feature value")
