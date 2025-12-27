"""
Risk Scoring Service

Service layer for ML-powered risk assessment.
"""

from __future__ import annotations

from typing import Any, Dict

from loguru import logger

from .models.dag_analyzer import DAGAnomalyAnalyzer


class RiskScoringService:
    """
    Risk Scoring Service

    Provides ML-powered risk assessment for governance decisions.
    Currently uses baseline heuristic analyzer - designed for PyTorch upgrade.
    """

    def __init__(self, model_version: str = "baseline-v1"):
        """
        Initialize risk scoring service

        Args:
            model_version: Model version identifier
        """
        self.model_version = model_version
        self.dag_analyzer = DAGAnomalyAnalyzer(model_version=model_version)
        logger.info(f"Risk Scoring Service initialized: {model_version}")

    async def score(self, request: Any) -> Dict[str, Any]:
        """
        Compute risk score for given request

        Args:
            request: RiskScoreRequest object

        Returns:
            Dictionary with risk_score, confidence, top_factors
        """
        context = request.context

        # Run DAG anomaly analysis
        analysis = await self.dag_analyzer.analyze(context)

        # Get top contributing factors
        top_factors = self.dag_analyzer.get_top_factors(
            analysis.features, top_n=5
        )

        return {
            "risk_score": analysis.risk_score,
            "confidence": analysis.confidence,
            "top_factors": [
                {
                    "factor": f.factor,
                    "weight": f.weight,
                    "description": f.description,
                }
                for f in top_factors
            ],
            "anomalies_detected": analysis.anomalies_detected,
        }


# ============================================================================
# Singleton Instance
# ============================================================================

_risk_scoring_service: RiskScoringService | None = None


def get_risk_scoring_service() -> RiskScoringService:
    """
    Get or create risk scoring service singleton

    Returns:
        RiskScoringService instance
    """
    global _risk_scoring_service
    if _risk_scoring_service is None:
        _risk_scoring_service = RiskScoringService()
    return _risk_scoring_service
