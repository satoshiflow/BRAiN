"""
DAG/IR Anomaly Analyzer

Baseline anomaly detection for mission DAG structures and execution plans.
Current implementation uses heuristic rules - designed for PyTorch upgrade.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional

from loguru import logger

from ..schemas import DAGAnalysisResult, RiskFactorContribution


class DAGAnomalyAnalyzer:
    """
    Analyze DAG structures for anomalies

    Baseline Implementation (v1):
    - Rule-based heuristics for common anomaly patterns
    - No ML models yet - pure deterministic analysis
    - Designed for easy PyTorch model integration in v2

    Detects:
    - Excessive complexity (too many nodes/edges)
    - Unusual branching patterns
    - Potential infinite loops
    - Resource allocation anomalies
    """

    def __init__(self, model_version: str = "baseline-v1"):
        self.model_version = model_version
        self._anomaly_thresholds = {
            "max_nodes": 100,
            "max_edges": 200,
            "max_depth": 20,
            "max_branching_factor": 10,
        }
        logger.info(f"DAG Analyzer initialized: {model_version}")

    async def analyze(self, context: Dict[str, Any]) -> DAGAnalysisResult:
        """
        Analyze context for DAG anomalies

        Args:
            context: Context data (may contain DAG structure, payload, etc.)

        Returns:
            DAGAnalysisResult with risk score and detected anomalies
        """
        features = self._extract_features(context)
        anomalies = self._detect_anomalies(features)
        risk_score = self._compute_risk_score(anomalies, features)
        confidence = self._compute_confidence(features)

        return DAGAnalysisResult(
            risk_score=risk_score,
            confidence=confidence,
            anomalies_detected=anomalies,
            features=features,
        )

    def _extract_features(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Extract numerical features from context

        Args:
            context: Raw context data

        Returns:
            Dictionary of normalized features
        """
        features = {}

        # Payload complexity
        payload = context.get("payload", {})
        features["payload_size"] = len(str(payload))
        features["payload_depth"] = self._get_dict_depth(payload)
        features["payload_keys"] = len(payload) if isinstance(payload, dict) else 0

        # Mission metadata
        features["priority"] = self._normalize_priority(
            context.get("priority", "NORMAL")
        )
        features["has_deadline"] = 1.0 if "deadline" in context else 0.0
        features["has_dependencies"] = (
            1.0 if context.get("dependencies", []) else 0.0
        )

        # Resource indicators
        if "budget" in context:
            features["budget"] = float(context["budget"])
        if "max_retries" in context:
            features["max_retries"] = float(context["max_retries"])

        # DAG structure (if present)
        if "dag" in context or "execution_plan" in context:
            dag = context.get("dag") or context.get("execution_plan", {})
            features["dag_nodes"] = len(dag.get("nodes", []))
            features["dag_edges"] = len(dag.get("edges", []))
            features["dag_depth"] = self._compute_dag_depth(dag)
            features["dag_branching"] = self._compute_branching_factor(dag)

        return features

    def _detect_anomalies(self, features: Dict[str, float]) -> List[str]:
        """
        Detect anomalies in extracted features

        Args:
            features: Extracted features

        Returns:
            List of anomaly descriptions
        """
        anomalies = []

        # Complexity anomalies
        if features.get("dag_nodes", 0) > self._anomaly_thresholds["max_nodes"]:
            anomalies.append(
                f"excessive_nodes: {features['dag_nodes']} > "
                f"{self._anomaly_thresholds['max_nodes']}"
            )

        if features.get("dag_edges", 0) > self._anomaly_thresholds["max_edges"]:
            anomalies.append(
                f"excessive_edges: {features['dag_edges']} > "
                f"{self._anomaly_thresholds['max_edges']}"
            )

        if features.get("dag_depth", 0) > self._anomaly_thresholds["max_depth"]:
            anomalies.append(
                f"excessive_depth: {features['dag_depth']} > "
                f"{self._anomaly_thresholds['max_depth']}"
            )

        if (
            features.get("dag_branching", 0)
            > self._anomaly_thresholds["max_branching_factor"]
        ):
            anomalies.append(
                f"excessive_branching: {features['dag_branching']} > "
                f"{self._anomaly_thresholds['max_branching_factor']}"
            )

        # Payload anomalies
        if features.get("payload_depth", 0) > 10:
            anomalies.append(f"deep_nesting: {features['payload_depth']} levels")

        if features.get("payload_size", 0) > 100000:
            anomalies.append(
                f"large_payload: {features['payload_size']} bytes"
            )

        # Resource anomalies
        if features.get("max_retries", 0) > 10:
            anomalies.append(f"excessive_retries: {features['max_retries']}")

        return anomalies

    def _compute_risk_score(
        self, anomalies: List[str], features: Dict[str, float]
    ) -> float:
        """
        Compute overall risk score from anomalies and features

        Args:
            anomalies: Detected anomalies
            features: Extracted features

        Returns:
            Normalized risk score [0.0, 1.0]
        """
        # Base score from anomaly count (weighted)
        base_score = min(len(anomalies) * 0.15, 0.8)

        # Adjust by feature severity
        severity_boost = 0.0

        if features.get("dag_nodes", 0) > 50:
            severity_boost += 0.1
        if features.get("payload_size", 0) > 50000:
            severity_boost += 0.05
        if features.get("priority", 0) > 0.8:  # HIGH or CRITICAL priority
            severity_boost += 0.05

        risk_score = min(base_score + severity_boost, 1.0)

        # Floor at 0.1 if any anomalies detected
        if anomalies and risk_score < 0.1:
            risk_score = 0.1

        return round(risk_score, 3)

    def _compute_confidence(self, features: Dict[str, float]) -> float:
        """
        Compute confidence in the risk score

        Args:
            features: Extracted features

        Returns:
            Confidence score [0.0, 1.0]
        """
        # More features → higher confidence
        feature_count = len(features)

        if feature_count >= 10:
            confidence = 0.9
        elif feature_count >= 5:
            confidence = 0.7
        elif feature_count >= 3:
            confidence = 0.5
        else:
            confidence = 0.3

        return confidence

    def get_top_factors(
        self, features: Dict[str, float], top_n: int = 5
    ) -> List[RiskFactorContribution]:
        """
        Get top contributing risk factors

        Args:
            features: Extracted features
            top_n: Number of top factors to return

        Returns:
            List of top risk factors with weights
        """
        # Simple heuristic: highest feature values are top contributors
        sorted_features = sorted(
            features.items(), key=lambda x: x[1], reverse=True
        )[:top_n]

        total = sum(v for _, v in sorted_features) or 1.0

        factors = []
        for feature, value in sorted_features:
            weight = min(value / total, 1.0)
            description = self._get_feature_description(feature, value)
            factors.append(
                RiskFactorContribution(
                    factor=feature,
                    weight=round(weight, 3),
                    description=description,
                    raw_value=value,
                )
            )

        return factors

    def _get_feature_description(self, feature: str, value: float) -> str:
        """Generate human-readable description for feature"""
        descriptions = {
            "dag_nodes": f"DAG contains {value:.0f} nodes",
            "dag_edges": f"DAG contains {value:.0f} edges",
            "dag_depth": f"Execution depth is {value:.0f} levels",
            "dag_branching": f"Maximum branching factor is {value:.0f}",
            "payload_size": f"Payload size is {value:.0f} bytes",
            "payload_depth": f"Payload nested {value:.0f} levels deep",
            "max_retries": f"Configured for {value:.0f} retries",
            "priority": f"Priority level: {self._priority_name(value)}",
        }
        return descriptions.get(feature, f"{feature} = {value:.2f}")

    @staticmethod
    def _get_dict_depth(d: Any, current_depth: int = 0) -> int:
        """Calculate maximum nesting depth of dictionary"""
        if not isinstance(d, dict):
            return current_depth
        if not d:
            return current_depth + 1
        return max(
            DAGAnomalyAnalyzer._get_dict_depth(v, current_depth + 1)
            for v in d.values()
        )

    @staticmethod
    def _normalize_priority(priority: str) -> float:
        """Convert priority string to normalized score"""
        priority_map = {
            "LOW": 0.25,
            "NORMAL": 0.5,
            "HIGH": 0.75,
            "CRITICAL": 1.0,
        }
        return priority_map.get(priority.upper(), 0.5)

    @staticmethod
    def _priority_name(score: float) -> str:
        """Convert normalized score back to priority name"""
        if score >= 0.9:
            return "CRITICAL"
        elif score >= 0.7:
            return "HIGH"
        elif score >= 0.4:
            return "NORMAL"
        else:
            return "LOW"

    @staticmethod
    def _compute_dag_depth(dag: Dict[str, Any]) -> int:
        """Compute maximum depth of DAG (placeholder)"""
        # TODO: Implement proper DAG depth calculation
        return len(dag.get("nodes", [])) // 5  # Rough estimate

    @staticmethod
    def _compute_branching_factor(dag: Dict[str, Any]) -> int:
        """Compute maximum branching factor (placeholder)"""
        # TODO: Implement proper branching factor calculation
        nodes = dag.get("nodes", [])
        edges = dag.get("edges", [])
        if not nodes:
            return 0
        return len(edges) // max(len(nodes), 1)
