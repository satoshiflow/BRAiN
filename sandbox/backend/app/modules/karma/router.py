from typing import Optional
from fastapi import APIRouter, Query

from app.modules.karma.schemas import (
    KarmaMetrics,
    KarmaScore,
    RYRKarmaMetrics,
    RYRKarmaScore,
)
from app.modules.karma.core.service import KarmaService, RYRKarmaService
from app.modules.dna.core.service import DNAService
from app.modules.dna.router import dna_service  # Singleton

router = APIRouter(prefix="/api/karma", tags=["KARMA"])

# Services
karma_service = KarmaService(dna_service=dna_service)
ryr_karma_service = RYRKarmaService(dna_service=dna_service)


# ============================================================================
# GENERAL AGENT KARMA ENDPOINTS
# ============================================================================

@router.get("/info")
def get_karma_info():
    """Get KARMA module information."""
    return {
        "name": "KARMA",
        "version": "2.0.0",
        "description": "Behavior Credit and Quality Learning system for agent performance scoring",
        "features": [
            "General agent performance scoring",
            "RYR robot fleet performance scoring",
            "Multi-dimensional safety, fleet, and navigation metrics",
            "Critical warning generation",
            "Performance recommendations",
        ],
        "endpoints": {
            "general": [
                "POST /agents/{agent_id}/score - Compute general agent karma",
            ],
            "ryr": [
                "POST /ryr/agents/{agent_id}/score - Compute RYR agent karma",
                "POST /ryr/robots/{robot_id}/score - Compute robot karma",
                "POST /ryr/fleets/{fleet_id}/score - Compute fleet karma",
            ],
        },
    }


@router.post("/agents/{agent_id}/score", response_model=KarmaScore)
def compute_agent_karma(
    agent_id: str,
    metrics: KarmaMetrics,
) -> KarmaScore:
    """
    Compute general agent karma score based on performance metrics.

    Metrics include:
    - Success rate
    - Latency
    - Policy violations
    - User rating
    - Credit consumption
    """
    return karma_service.compute_score(agent_id, metrics)


# ============================================================================
# RYR-SPECIFIC KARMA ENDPOINTS
# ============================================================================

@router.post("/ryr/agents/{agent_id}/score", response_model=RYRKarmaScore)
def compute_ryr_agent_karma(
    agent_id: str,
    metrics: RYRKarmaMetrics,
    robot_id: Optional[str] = Query(None, description="Associated robot ID"),
    fleet_id: Optional[str] = Query(None, description="Associated fleet ID"),
) -> RYRKarmaScore:
    """
    Compute RYR agent karma score with detailed breakdown.

    Returns multi-dimensional scores:
    - Overall score (weighted average)
    - Fleet coordination score
    - Safety compliance score
    - Navigation performance score

    Also includes:
    - Critical safety warnings
    - Performance improvement recommendations
    """
    return ryr_karma_service.compute_ryr_score(
        agent_id=agent_id,
        metrics=metrics,
        robot_id=robot_id,
        fleet_id=fleet_id,
    )


@router.post("/ryr/robots/{robot_id}/score", response_model=RYRKarmaScore)
def compute_robot_karma(
    robot_id: str,
    metrics: RYRKarmaMetrics,
    agent_id: Optional[str] = Query(None, description="Associated agent ID"),
    fleet_id: Optional[str] = Query(None, description="Associated fleet ID"),
) -> RYRKarmaScore:
    """
    Compute karma score for a specific robot.

    Same as /ryr/agents/{agent_id}/score but using robot_id as primary identifier.
    """
    # Use robot_id as agent_id if agent_id not provided
    effective_agent_id = agent_id or f"robot_{robot_id}"

    return ryr_karma_service.compute_ryr_score(
        agent_id=effective_agent_id,
        metrics=metrics,
        robot_id=robot_id,
        fleet_id=fleet_id,
    )


@router.post("/ryr/fleets/{fleet_id}/score", response_model=RYRKarmaScore)
def compute_fleet_karma(
    fleet_id: str,
    metrics: RYRKarmaMetrics,
    agent_id: Optional[str] = Query(None, description="Associated agent ID"),
) -> RYRKarmaScore:
    """
    Compute karma score for an entire fleet.

    Aggregated metrics across all robots in the fleet.
    """
    # Use fleet_id as agent_id if agent_id not provided
    effective_agent_id = agent_id or f"fleet_{fleet_id}"

    return ryr_karma_service.compute_ryr_score(
        agent_id=effective_agent_id,
        metrics=metrics,
        robot_id=None,
        fleet_id=fleet_id,
    )
