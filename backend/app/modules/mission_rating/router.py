"""
Mission Rating System API Router

RESTful endpoints for mission rating, agent matching, and skill management.
"""

from __future__ import annotations

import time
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from .models import AgentRating, MissionRating, SkillProfile
from .schemas import (
    AgentMatchRequest,
    AgentMatchResult,
    AgentSkillUpdate,
    MissionAllocationRequest,
    MissionAllocationResponse,
    MissionRatingCreate,
    MissionRatingResponse,
    RatingAuditEntry,
    RatingAuditLog,
    RatingHealth,
    RatingStatistics,
)
from .service import MissionRatingService

router = APIRouter(prefix="/api/mission-rating", tags=["mission-rating"])

# Service instance (will be initialized with KARMA service if available)
_service: Optional[MissionRatingService] = None


def get_service() -> MissionRatingService:
    """Get or create service instance"""
    global _service
    if _service is None:
        # Initialize service
        # In production, would inject KARMA service here
        _service = MissionRatingService()
    return _service


@router.post("/ratings", response_model=MissionRatingResponse)
async def create_mission_rating(payload: MissionRatingCreate):
    """
    Create a rating for a completed mission.

    This endpoint evaluates mission performance across multiple categories:
    - Quality: Success rate and error metrics
    - Timeliness: Actual vs estimated duration
    - Efficiency: Credit consumption
    - Accuracy: Retry count and success rate
    - Reliability: Composite score

    The rating is deterministic and includes a hash for verification.
    Agent ratings are automatically updated, and KARMA scores are integrated.
    """
    service = get_service()

    try:
        rating, agent_updated, karma_updated = await service.create_rating(payload)

        return MissionRatingResponse(
            rating=rating,
            agent_updated=agent_updated,
            karma_updated=karma_updated,
            message="Rating created successfully",
        )

    except Exception as e:
        logger.error(f"Failed to create rating: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create rating: {str(e)}")


@router.get("/ratings/mission/{mission_id}", response_model=MissionRating)
async def get_mission_rating(mission_id: str):
    """Get rating for a specific mission"""
    service = get_service()

    rating = await service.get_mission_rating(mission_id)
    if not rating:
        raise HTTPException(status_code=404, detail=f"Rating not found for mission {mission_id}")

    return rating


@router.get("/ratings/agent/{agent_id}", response_model=AgentRating)
async def get_agent_rating(agent_id: str):
    """
    Get aggregate rating for an agent.

    Returns complete agent performance profile including:
    - Overall rating
    - Category averages
    - Skill profile
    - Performance trends
    - Reliability metrics
    """
    service = get_service()

    rating = await service.get_agent_rating(agent_id)
    if not rating:
        raise HTTPException(status_code=404, detail=f"Rating not found for agent {agent_id}")

    return rating


@router.post("/match", response_model=AgentMatchResult)
async def match_agent_for_mission(request: AgentMatchRequest):
    """
    Find the best agent for a mission based on required skills.

    Uses weighted scoring algorithm that considers:
    - Skill matching (skills and proficiency levels)
    - Agent rating (historical performance)
    - Availability (current workload)

    Returns ranked list of all agents with detailed match analysis.
    """
    service = get_service()

    try:
        result = await service.match_agent(request)
        return result

    except Exception as e:
        logger.error(f"Failed to match agent: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to match agent: {str(e)}")


@router.post("/allocate", response_model=MissionAllocationResponse)
async def allocate_mission(request: MissionAllocationRequest):
    """
    Allocate a mission to the best-matched agent.

    Combines agent matching with mission assignment.
    Ensures minimum skill match threshold is met.
    """
    service = get_service()

    try:
        # Find best agent
        match_request = AgentMatchRequest(
            mission_id=request.mission_id,
            required_skills=request.required_skills,
            estimated_duration=request.estimated_duration,
            estimated_credits=request.estimated_credits,
        )

        match_result = await service.match_agent(match_request)

        # Check if we have a suitable agent
        if not match_result.recommended_agent:
            return MissionAllocationResponse(
                mission_id=request.mission_id,
                allocated_agent=None,
                allocation_score=None,
                success=False,
                message="No agents available",
                match_analysis=match_result,
            )

        # Get top match score
        top_match = match_result.match_scores[0]

        # Check minimum skill threshold
        if top_match.skill_match_score < request.min_skill_match:
            return MissionAllocationResponse(
                mission_id=request.mission_id,
                allocated_agent=None,
                allocation_score=top_match.overall_score,
                success=False,
                message=f"No agent meets minimum skill requirement ({request.min_skill_match}%)",
                match_analysis=match_result,
            )

        # Allocation successful
        return MissionAllocationResponse(
            mission_id=request.mission_id,
            allocated_agent=match_result.recommended_agent,
            allocation_score=top_match.overall_score,
            success=True,
            message=f"Mission allocated to {match_result.recommended_agent}",
            match_analysis=match_result,
        )

    except Exception as e:
        logger.error(f"Failed to allocate mission: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to allocate mission: {str(e)}")


@router.put("/agents/{agent_id}/skills", response_model=dict)
async def update_agent_skills(agent_id: str, payload: AgentSkillUpdate):
    """
    Update an agent's skill profile.

    Allows manual or automated skill updates based on training,
    certifications, or performance analysis.
    """
    service = get_service()

    if payload.agent_id != agent_id:
        raise HTTPException(status_code=400, detail="Agent ID mismatch")

    try:
        success = await service.update_agent_skills(agent_id, payload.skills)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update skills")

        return {
            "success": True,
            "message": f"Updated {len(payload.skills)} skills for agent {agent_id}",
        }

    except Exception as e:
        logger.error(f"Failed to update agent skills: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update skills: {str(e)}")


@router.get("/audit/{mission_id}", response_model=RatingAuditLog)
async def get_rating_audit_trail(mission_id: str):
    """
    Get audit trail for a mission's ratings.

    Returns append-only log of all rating decisions with:
    - Timestamps
    - Rating changes
    - Decision factors
    - Algorithm versions
    - Deterministic hashes for verification
    """
    service = get_service()

    try:
        entries = await service.get_audit_trail(mission_id)

        oldest = min((e.timestamp for e in entries), default=None)
        newest = max((e.timestamp for e in entries), default=None)

        return RatingAuditLog(
            entries=entries,
            total_entries=len(entries),
            oldest_entry=oldest,
            newest_entry=newest,
        )

    except Exception as e:
        logger.error(f"Failed to get audit trail: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get audit trail: {str(e)}")


@router.get("/stats", response_model=RatingStatistics)
async def get_rating_statistics():
    """
    Get system-wide rating statistics.

    Provides aggregated metrics about all ratings in the system.
    """
    # This would aggregate data from Redis
    # For now, return placeholder data
    return RatingStatistics(
        total_ratings=0,
        total_agents_rated=0,
        avg_overall_rating=0.0,
        rating_distribution={},
        category_averages={},
        last_updated=time.time(),
    )


@router.get("/health", response_model=RatingHealth)
async def get_rating_health():
    """
    Health check for the rating system.

    Verifies connectivity to dependent services:
    - Rating service
    - KARMA service
    - Credits service
    """
    service = get_service()

    # Check service availability
    rating_available = service is not None
    karma_available = service._karma_service is not None if service else False
    credits_available = True  # Placeholder

    status = "healthy" if rating_available else "error"

    return RatingHealth(
        status=status,
        rating_service_available=rating_available,
        karma_service_available=karma_available,
        credits_service_available=credits_available,
        recent_ratings_count=0,  # Would query Redis
        recent_errors_count=0,   # Would query error logs
        timestamp=time.time(),
    )


@router.get("/info", response_model=dict)
async def get_rating_info():
    """Get mission rating system information"""
    return {
        "name": "BRAiN Mission Rating System",
        "version": "1.0.0",
        "description": "Comprehensive mission rating and agent performance evaluation",
        "features": [
            "Deterministic rating calculation",
            "Skill-based agent matching",
            "KARMA integration",
            "Append-only audit trail",
            "Multi-category performance evaluation",
        ],
        "rating_categories": [
            "quality",
            "timeliness",
            "efficiency",
            "accuracy",
            "reliability",
        ],
        "skill_levels": [
            "novice",
            "intermediate",
            "advanced",
            "expert",
        ],
    }
