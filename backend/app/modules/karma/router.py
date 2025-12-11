from fastapi import APIRouter

from app.modules.karma.schemas import KarmaMetrics, KarmaScore
from app.modules.karma.core.service import KarmaService
from app.modules.dna.core.service import DNAService
from app.modules.dna.router import dna_service  # unseren Singleton wiederverwenden

router = APIRouter(prefix="/api/karma", tags=["KARMA"])

karma_service = KarmaService(dna_service=dna_service)


@router.post("/agents/{agent_id}/score", response_model=KarmaScore)
def compute_agent_karma(
    agent_id: str,
    metrics: KarmaMetrics,
) -> KarmaScore:
    return karma_service.compute_score(agent_id, metrics)
