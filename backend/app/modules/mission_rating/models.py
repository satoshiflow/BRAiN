"""
Mission Rating System Models

Defines core data structures for mission rating, agent skills,
and performance tracking.
"""

from __future__ import annotations

import enum
import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class SkillLevel(str, enum.Enum):
    """Agent skill proficiency levels"""
    NOVICE = "novice"          # 0-25
    INTERMEDIATE = "intermediate"  # 26-50
    ADVANCED = "advanced"       # 51-75
    EXPERT = "expert"           # 76-100

    @staticmethod
    def from_score(score: float) -> SkillLevel:
        """Convert numeric score to skill level"""
        if score <= 25:
            return SkillLevel.NOVICE
        elif score <= 50:
            return SkillLevel.INTERMEDIATE
        elif score <= 75:
            return SkillLevel.ADVANCED
        else:
            return SkillLevel.EXPERT


class RatingCategory(str, enum.Enum):
    """Categories for rating evaluation"""
    QUALITY = "quality"          # Output quality
    TIMELINESS = "timeliness"    # Completion time
    EFFICIENCY = "efficiency"    # Resource usage
    ACCURACY = "accuracy"        # Correctness
    RELIABILITY = "reliability"  # Consistency


class SkillRequirement(BaseModel):
    """Defines skill requirements for a mission"""
    skill_name: str = Field(..., description="Name of required skill")
    min_level: SkillLevel = Field(default=SkillLevel.NOVICE, description="Minimum skill level")
    weight: float = Field(default=1.0, ge=0.0, le=1.0, description="Importance weight (0-1)")

    @field_validator("skill_name")
    @classmethod
    def validate_skill_name(cls, v: str) -> str:
        """Ensure skill name is normalized"""
        return v.lower().strip()


class SkillProfile(BaseModel):
    """Agent's skill profile with proficiency scores"""
    skill_name: str = Field(..., description="Name of the skill")
    score: float = Field(..., ge=0.0, le=100.0, description="Proficiency score (0-100)")
    level: SkillLevel = Field(..., description="Derived skill level")
    missions_completed: int = Field(default=0, ge=0, description="Number of missions using this skill")
    last_used: Optional[float] = Field(default=None, description="Timestamp of last use")

    @field_validator("skill_name")
    @classmethod
    def validate_skill_name(cls, v: str) -> str:
        """Ensure skill name is normalized"""
        return v.lower().strip()

    @staticmethod
    def create(skill_name: str, score: float, missions_completed: int = 0) -> SkillProfile:
        """Factory method to create skill profile"""
        return SkillProfile(
            skill_name=skill_name.lower().strip(),
            score=score,
            level=SkillLevel.from_score(score),
            missions_completed=missions_completed,
            last_used=time.time() if missions_completed > 0 else None,
        )


class PerformanceMetrics(BaseModel):
    """Detailed performance metrics for a mission execution"""
    # Time metrics
    start_time: float = Field(..., description="Mission start timestamp")
    end_time: Optional[float] = Field(default=None, description="Mission end timestamp")
    duration_seconds: Optional[float] = Field(default=None, description="Actual duration")
    estimated_duration: Optional[float] = Field(default=None, description="Estimated duration")

    # Quality metrics
    success_rate: float = Field(default=1.0, ge=0.0, le=1.0, description="Task success rate")
    error_count: int = Field(default=0, ge=0, description="Number of errors")
    retry_count: int = Field(default=0, ge=0, description="Number of retries")

    # Resource metrics
    credits_allocated: float = Field(default=0.0, ge=0.0, description="Credits allocated")
    credits_consumed: float = Field(default=0.0, ge=0.0, description="Credits actually consumed")
    cpu_usage_avg: Optional[float] = Field(default=None, ge=0.0, description="Average CPU usage %")
    memory_usage_avg: Optional[float] = Field(default=None, ge=0.0, description="Average memory usage MB")

    # Custom metrics
    custom_metrics: Dict[str, Any] = Field(default_factory=dict, description="Additional metrics")

    def calculate_efficiency(self) -> float:
        """Calculate resource efficiency (0-1)"""
        if self.credits_allocated == 0:
            return 1.0
        return max(0.0, 1.0 - (self.credits_consumed / self.credits_allocated))

    def calculate_timeliness(self) -> float:
        """Calculate timeliness score (0-1)"""
        if self.estimated_duration is None or self.duration_seconds is None:
            return 1.0
        if self.estimated_duration == 0:
            return 1.0
        ratio = self.duration_seconds / self.estimated_duration
        # Score: 1.0 if on time, decreases linearly if over time
        return max(0.0, min(1.0, 2.0 - ratio))


class CategoryRating(BaseModel):
    """Rating for a specific category"""
    category: RatingCategory = Field(..., description="Rating category")
    score: float = Field(..., ge=0.0, le=100.0, description="Score (0-100)")
    weight: float = Field(default=1.0, ge=0.0, le=1.0, description="Category weight")
    justification: Optional[str] = Field(default=None, description="Reason for score")


class MissionRating(BaseModel):
    """Complete mission rating with detailed breakdown"""
    mission_id: str = Field(..., description="Mission identifier")
    agent_id: str = Field(..., description="Agent who executed mission")

    # Overall rating
    overall_score: float = Field(..., ge=0.0, le=100.0, description="Overall rating (0-100)")

    # Category ratings
    category_ratings: List[CategoryRating] = Field(default_factory=list, description="Ratings by category")

    # Performance data
    metrics: PerformanceMetrics = Field(..., description="Performance metrics")

    # KARMA integration
    karma_score: Optional[float] = Field(default=None, description="KARMA-derived score")
    karma_updated: bool = Field(default=False, description="Whether agent KARMA was updated")

    # Metadata
    rated_at: float = Field(default_factory=time.time, description="Rating timestamp")
    rated_by: Optional[str] = Field(default=None, description="Who/what created rating (system/user_id)")
    is_verified: bool = Field(default=False, description="Whether rating is verified")

    # Audit
    rating_version: str = Field(default="1.0.0", description="Rating algorithm version")
    deterministic_hash: Optional[str] = Field(default=None, description="Hash for verification")

    def calculate_weighted_score(self) -> float:
        """Calculate weighted average of category ratings"""
        if not self.category_ratings:
            return self.overall_score

        total_weight = sum(r.weight for r in self.category_ratings)
        if total_weight == 0:
            return self.overall_score

        weighted_sum = sum(r.score * r.weight for r in self.category_ratings)
        return weighted_sum / total_weight


class AgentRating(BaseModel):
    """Aggregate agent rating across all missions"""
    agent_id: str = Field(..., description="Agent identifier")

    # Overall statistics
    overall_rating: float = Field(default=0.0, ge=0.0, le=100.0, description="Overall agent rating")
    total_missions: int = Field(default=0, ge=0, description="Total missions completed")
    successful_missions: int = Field(default=0, ge=0, description="Successfully completed missions")

    # Category averages
    category_averages: Dict[RatingCategory, float] = Field(
        default_factory=dict,
        description="Average scores by category"
    )

    # Skill profile
    skills: List[SkillProfile] = Field(default_factory=list, description="Agent skills")

    # Performance trends
    recent_ratings: List[float] = Field(default_factory=list, description="Last 10 mission ratings")
    trend: Optional[str] = Field(default=None, description="Performance trend: improving/declining/stable")

    # Reliability metrics
    avg_completion_time: Optional[float] = Field(default=None, description="Average mission duration")
    reliability_score: float = Field(default=100.0, ge=0.0, le=100.0, description="Reliability score")

    # Timestamps
    last_mission_at: Optional[float] = Field(default=None, description="Last mission timestamp")
    last_updated: float = Field(default_factory=time.time, description="Last update timestamp")

    def get_skill(self, skill_name: str) -> Optional[SkillProfile]:
        """Get skill by name"""
        skill_name_normalized = skill_name.lower().strip()
        for skill in self.skills:
            if skill.skill_name == skill_name_normalized:
                return skill
        return None

    def add_or_update_skill(self, skill: SkillProfile) -> None:
        """Add new skill or update existing"""
        existing = self.get_skill(skill.skill_name)
        if existing:
            # Update existing skill
            self.skills.remove(existing)
        self.skills.append(skill)

    def calculate_success_rate(self) -> float:
        """Calculate mission success rate"""
        if self.total_missions == 0:
            return 0.0
        return self.successful_missions / self.total_missions

    def calculate_trend(self) -> str:
        """Calculate performance trend from recent ratings"""
        if len(self.recent_ratings) < 3:
            return "stable"

        # Simple linear trend
        first_half = sum(self.recent_ratings[:len(self.recent_ratings)//2]) / (len(self.recent_ratings)//2)
        second_half = sum(self.recent_ratings[len(self.recent_ratings)//2:]) / (len(self.recent_ratings) - len(self.recent_ratings)//2)

        diff = second_half - first_half
        if diff > 5:
            return "improving"
        elif diff < -5:
            return "declining"
        else:
            return "stable"


class MissionWithRating(BaseModel):
    """Extended mission model with rating fields"""
    # Core mission fields (from existing Mission model)
    id: str
    name: str
    description: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    status: str  # We'll use string to avoid importing MissionStatus
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

    # Rating-specific fields
    agent_id: Optional[str] = Field(default=None, description="Assigned agent")
    required_skills: List[SkillRequirement] = Field(default_factory=list, description="Required skills")
    estimated_duration: Optional[float] = Field(default=None, description="Estimated duration in seconds")
    estimated_credits: Optional[float] = Field(default=None, description="Estimated credit cost")

    # Post-execution rating
    rating: Optional[MissionRating] = Field(default=None, description="Mission rating (after completion)")
    performance_metrics: Optional[PerformanceMetrics] = Field(default=None, description="Performance data")
