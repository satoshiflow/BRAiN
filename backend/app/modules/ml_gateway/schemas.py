"""
ML Gateway Module - Data Models

Schemas for ML-powered risk scoring and governance augmentation.
All ML outputs are advisory only - final decisions remain deterministic.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# ML Provider Configuration
# ============================================================================


class MLProviderStatus(str, Enum):
    """ML provider health status"""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"
    DISABLED = "disabled"


class MLProviderConfig(BaseModel):
    """Configuration for ML service provider"""

    enabled: bool = Field(default=True, description="Whether ML gateway is enabled")
    timeout_ms: int = Field(
        default=200, ge=50, le=5000, description="Timeout for ML requests (ms)"
    )
    fallback_risk_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Conservative risk score when ML unavailable",
    )
    min_confidence_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for trusting ML scores",
    )
    model_version: str = Field(
        default="baseline-v1", description="Active model version identifier"
    )


# ============================================================================
# Risk Scoring
# ============================================================================


class RiskFactor(BaseModel):
    """Individual risk factor contributing to overall score"""

    factor: str = Field(..., description="Risk factor identifier")
    weight: float = Field(..., ge=0.0, le=1.0, description="Contribution weight")
    description: str = Field(default="", description="Human-readable explanation")


class RiskScoreRequest(BaseModel):
    """Request for ML risk scoring"""

    context: Dict[str, Any] = Field(..., description="Context data for risk assessment")
    mission_id: Optional[str] = Field(
        default=None, description="Associated mission ID for audit trail"
    )
    agent_id: Optional[str] = Field(
        default=None, description="Associated agent ID for audit trail"
    )
    action: Optional[str] = Field(
        default=None, description="Action being evaluated for risk"
    )


class RiskScoreResponse(BaseModel):
    """Response from ML risk scoring service"""

    risk_score: float = Field(
        ..., ge=0.0, le=1.0, description="Normalized risk score (0=safe, 1=critical)"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Model confidence in the score"
    )
    top_factors: List[RiskFactor] = Field(
        default_factory=list, description="Top contributing risk factors"
    )
    model_version: str = Field(..., description="Model version used for inference")
    inference_time_ms: float = Field(..., ge=0.0, description="Inference duration (ms)")
    is_fallback: bool = Field(
        default=False, description="Whether this is a fallback score"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Scoring timestamp"
    )

    @field_validator("risk_score", "confidence")
    @classmethod
    def validate_range(cls, v: float) -> float:
        """Ensure scores are in valid range"""
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Value must be between 0.0 and 1.0, got {v}")
        return v


# ============================================================================
# ML-Enriched Context (for Policy Engine Integration)
# ============================================================================


class MLEnrichedContext(BaseModel):
    """Context data enriched with ML risk scores for policy evaluation"""

    # Original context
    original_context: Dict[str, Any] = Field(
        default_factory=dict, description="Original context data"
    )

    # ML augmentation
    ml_risk_score: float = Field(
        ..., ge=0.0, le=1.0, description="ML-computed risk score"
    )
    ml_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="ML confidence level"
    )
    ml_model_version: str = Field(..., description="Model version identifier")
    ml_top_factors: List[RiskFactor] = Field(
        default_factory=list, description="Top risk factors"
    )
    ml_is_fallback: bool = Field(
        default=False, description="Whether fallback score was used"
    )

    # Audit metadata
    ml_inference_time_ms: float = Field(..., description="ML inference duration")
    ml_timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="ML scoring timestamp"
    )

    def to_flat_dict(self) -> Dict[str, Any]:
        """Convert to flat dictionary for policy condition evaluation"""
        result = {**self.original_context}
        result.update(
            {
                "ml_risk_score": self.ml_risk_score,
                "ml_confidence": self.ml_confidence,
                "ml_model_version": self.ml_model_version,
                "ml_is_fallback": self.ml_is_fallback,
            }
        )
        return result


# ============================================================================
# Health & Monitoring
# ============================================================================


class MLGatewayHealth(BaseModel):
    """ML Gateway health status"""

    status: MLProviderStatus
    provider_available: bool
    model_version: str
    uptime_seconds: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    fallback_requests: int
    avg_inference_time_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100

    @property
    def fallback_rate(self) -> float:
        """Calculate fallback usage rate percentage"""
        if self.total_requests == 0:
            return 0.0
        return (self.fallback_requests / self.total_requests) * 100


class MLGatewayInfo(BaseModel):
    """ML Gateway system information"""

    name: str = "ML Gateway"
    version: str = "1.0.0"
    description: str = "Machine Learning integration for governance augmentation"
    enabled: bool
    config: MLProviderConfig
