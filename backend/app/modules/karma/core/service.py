from datetime import datetime

from app.modules.karma.schemas import KarmaMetrics, KarmaScore
from app.modules.dna.core.service import DNAService


class KarmaService:
    """
    In-Memory KARMA/BCQL-Service.
    Nutzt DNAService, um karma_score im letzten Snapshot zu aktualisieren.
    """

    def __init__(self, dna_service: DNAService) -> None:
        self._dna = dna_service

    def compute_score(self, agent_id: str, metrics: KarmaMetrics) -> KarmaScore:
        # Einfacher Scoring-Ansatz – später verfeinern
        score = 0.0
        score += metrics.success_rate * 40.0
        score += max(0.0, 5.0 - (metrics.avg_latency_ms / 1000.0)) * 5.0
        score -= metrics.policy_violations * 10.0
        score += (metrics.user_rating_avg - 3.0) * 8.0
        score -= metrics.credit_consumption_per_task * 2.0

        score = max(0.0, min(100.0, score))

        # DNA aktualisieren
        self._dna.update_karma(agent_id, score)

        return KarmaScore(
            agent_id=agent_id,
            score=score,
            computed_at=datetime.utcnow(),
            details=metrics,
        )
