"""Priority scoring for incident signals."""

from __future__ import annotations

from app.modules.immune_orchestrator.schemas import IncidentSignal, SignalSeverity


class PriorityEngine:
    """Computes a normalized priority score in range [0.0, 1.0]."""

    _SEVERITY_WEIGHT = {
        SignalSeverity.INFO: 0.25,
        SignalSeverity.WARNING: 0.6,
        SignalSeverity.CRITICAL: 1.0,
    }

    def score(self, signal: IncidentSignal) -> float:
        severity_score = self._SEVERITY_WEIGHT[signal.severity]
        blast_score = min(signal.blast_radius / 10.0, 1.0)
        confidence_score = signal.confidence
        recurrence_score = min(signal.recurrence / 5.0, 1.0)

        # Weighted blend tuned for incident handling.
        score = (
            severity_score * 0.45
            + blast_score * 0.25
            + confidence_score * 0.20
            + recurrence_score * 0.10
        )
        return max(0.0, min(score, 1.0))
