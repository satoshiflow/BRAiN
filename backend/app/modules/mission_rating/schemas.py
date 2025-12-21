"""
Mission Rating System API Schemas

Request/response models for the mission rating API endpoints.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .models import (
    AgentRating,
    CategoryRating,
    MissionRating,
    PerformanceMetrics,
    SkillProfile,
    SkillRequirement,
    RatingCategory,
)


class MissionRatingCreate(BaseModel):
    """Request to create a mission rating"""
    mission_id: str = Field(..., description="Mission to rate")
    agent_id: str = Field(..., description="Agent who executed mission")

    # Performance metrics
    metrics: PerformanceMetrics = Field(..., description="Performance data")

    # Optional category overrides
    category_scores: Optional[Dict[RatingCategory, float]] = Field(
        default=None,
        description="Manual category scores (if not auto-calculated)"
    )

    # Rating metadata
    rated_by: Optional[str] = Field(default="system", description="Rating source")
    notes: Optional[str] = Field(default=None, description="Additional notes")


class MissionRatingResponse(BaseModel):
    """Response containing mission rating"""
    rating: MissionRating = Field(..., description="The mission rating")
    agent_updated: bool = Field(..., description="Whether agent rating was updated")
    karma_updated: bool = Field(..., description="Whether KARMA was updated")
    message: str = Field(default="Rating created successfully")


class AgentMatchRequest(BaseModel):
    """Request to find best agent for a mission"""
    mission_id: Optional[str] = Field(default=None, description="Mission ID (optional)")
    required_skills: List[SkillRequirement] = Field(..., description="Required skills")
    estimated_duration: Optional[float] = Field(default=None, description="Estimated duration")
    estimated_credits: Optional[float] = Field(default=None, description="Estimated credits")

    # Matching criteria weights
    skill_match_weight: float = Field(default=0.5, ge=0.0, le=1.0, description="Weight for skill matching")
    rating_weight: float = Field(default=0.3, ge=0.0, le=1.0, description="Weight for overall rating")
    availability_weight: float = Field(default=0.2, ge=0.0, le=1.0, description="Weight for availability")


class AgentMatchScore(BaseModel):
    """Matching score for a single agent"""
    agent_id: str = Field(..., description="Agent ID")
    overall_score: float = Field(..., ge=0.0, le=100.0, description="Overall match score")

    # Component scores
    skill_match_score: float = Field(..., ge=0.0, le=100.0, description="Skill matching score")
    rating_score: float = Field(..., ge=0.0, le=100.0, description="Agent rating score")
    availability_score: float = Field(..., ge=0.0, le=100.0, description="Availability score")

    # Details
    matched_skills: List[str] = Field(default_factory=list, description="Skills that matched")
    missing_skills: List[str] = Field(default_factory=list, description="Skills agent lacks")
    agent_rating: Optional[AgentRating] = Field(default=None, description="Agent's rating profile")


class AgentMatchResult(BaseModel):
    """Result of agent matching algorithm"""
    mission_id: Optional[str] = Field(default=None, description="Mission ID if provided")
    recommended_agent: Optional[str] = Field(default=None, description="Best matched agent")
    match_scores: List[AgentMatchScore] = Field(default_factory=list, description="All agent scores")

    # Matching metadata
    total_agents_evaluated: int = Field(..., description="Number of agents evaluated")
    matching_algorithm: str = Field(default="weighted_skill_match_v1", description="Algorithm used")
    timestamp: float = Field(default_factory=time.time, description="Matching timestamp")


class RatingAuditEntry(BaseModel):
    """Audit trail entry for rating decisions"""
    id: str = Field(..., description="Audit entry ID")
    mission_id: str = Field(..., description="Related mission")
    agent_id: str = Field(..., description="Related agent")

    action: str = Field(..., description="Action taken (created/updated/verified)")
    rating_before: Optional[float] = Field(default=None, description="Rating before change")
    rating_after: float = Field(..., description="Rating after change")

    # Decision transparency
    algorithm_version: str = Field(..., description="Rating algorithm version")
    decision_factors: Dict[str, Any] = Field(default_factory=dict, description="Factors that influenced rating")
    deterministic_hash: str = Field(..., description="Hash for verification")

    # Metadata
    timestamp: float = Field(default_factory=time.time, description="Audit timestamp")
    triggered_by: str = Field(..., description="What triggered this entry (system/user_id)")


class RatingAuditLog(BaseModel):
    """Collection of audit entries"""
    entries: List[RatingAuditEntry] = Field(default_factory=list, description="Audit entries")
    total_entries: int = Field(..., description="Total number of entries")
    oldest_entry: Optional[float] = Field(default=None, description="Oldest entry timestamp")
    newest_entry: Optional[float] = Field(default=None, description="Newest entry timestamp")


class AgentSkillUpdate(BaseModel):
    """Request to update agent skills"""
    agent_id: str = Field(..., description="Agent to update")
    skills: List[SkillProfile] = Field(..., description="Updated skill profiles")


class SkillMatchAnalysis(BaseModel):
    """Detailed analysis of skill matching"""
    required_skill: SkillRequirement = Field(..., description="Required skill")
    agent_skill: Optional[SkillProfile] = Field(default=None, description="Agent's skill (if present)")

    match_score: float = Field(..., ge=0.0, le=100.0, description="Match score")
    meets_requirement: bool = Field(..., description="Whether requirement is met")
    gap_analysis: Optional[str] = Field(default=None, description="Skill gap description")


class MissionAllocationRequest(BaseModel):
    """Request to allocate mission with automatic agent matching"""
    mission_id: str = Field(..., description="Mission to allocate")
    required_skills: List[SkillRequirement] = Field(..., description="Required skills")
    estimated_duration: Optional[float] = Field(default=None, description="Estimated duration")
    estimated_credits: Optional[float] = Field(default=None, description="Estimated credits")

    # Allocation preferences
    prefer_availability: bool = Field(default=True, description="Prefer available agents")
    min_skill_match: float = Field(default=70.0, ge=0.0, le=100.0, description="Minimum skill match %")


class MissionAllocationResponse(BaseModel):
    """Response from mission allocation"""
    mission_id: str = Field(..., description="Mission ID")
    allocated_agent: Optional[str] = Field(default=None, description="Agent allocated to mission")
    allocation_score: Optional[float] = Field(default=None, description="Allocation match score")

    success: bool = Field(..., description="Whether allocation succeeded")
    message: str = Field(..., description="Status message")

    # Details
    match_analysis: Optional[AgentMatchResult] = Field(default=None, description="Matching details")


class RatingStatistics(BaseModel):
    """Statistics about ratings in the system"""
    total_ratings: int = Field(default=0, description="Total ratings created")
    total_agents_rated: int = Field(default=0, description="Number of agents with ratings")

    # Distribution
    avg_overall_rating: float = Field(default=0.0, description="Average rating across all agents")
    rating_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Distribution by rating ranges (0-20, 21-40, etc.)"
    )

    # Category statistics
    category_averages: Dict[RatingCategory, float] = Field(
        default_factory=dict,
        description="Average scores by category"
    )

    # Metadata
    last_updated: float = Field(default_factory=time.time, description="Statistics timestamp")


class RatingHealth(BaseModel):
    """Health status of the rating system"""
    status: str = Field(..., description="Health status (healthy/degraded/error)")
    rating_service_available: bool = Field(..., description="Rating service availability")
    karma_service_available: bool = Field(..., description="KARMA service availability")
    credits_service_available: bool = Field(..., description="Credits service availability")

    # Metrics
    recent_ratings_count: int = Field(default=0, description="Ratings in last hour")
    recent_errors_count: int = Field(default=0, description="Errors in last hour")

    timestamp: float = Field(default_factory=time.time, description="Health check timestamp")
