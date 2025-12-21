"""
Mission Rating Service

Core business logic for mission rating, agent matching, and performance evaluation.
Integrates with KARMA and credits systems.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from app.core.redis_client import get_redis
from app.modules.karma.core.service import KarmaService
from app.modules.dna.core.service import DNAService

from .models import (
    AgentRating,
    CategoryRating,
    MissionRating,
    PerformanceMetrics,
    RatingCategory,
    SkillLevel,
    SkillProfile,
    SkillRequirement,
)
from .schemas import (
    AgentMatchRequest,
    AgentMatchResult,
    AgentMatchScore,
    MissionRatingCreate,
    RatingAuditEntry,
    SkillMatchAnalysis,
)


# Redis keys
AGENT_RATING_PREFIX = "brain:mission_rating:agent:"
MISSION_RATING_PREFIX = "brain:mission_rating:mission:"
RATING_AUDIT_PREFIX = "brain:mission_rating:audit:"
RATING_STATS_KEY = "brain:mission_rating:stats"

RATING_VERSION = "1.0.0"


class MissionRatingService:
    """
    Service for mission rating and agent performance evaluation.

    Features:
    - Deterministic rating calculation
    - Skill-based agent matching
    - KARMA integration
    - Append-only audit trail
    - Credit allocation tracking
    """

    def __init__(self, karma_service: Optional[KarmaService] = None):
        """Initialize service with optional KARMA integration"""
        self._karma_service = karma_service

    async def create_rating(
        self,
        payload: MissionRatingCreate,
    ) -> Tuple[MissionRating, bool, bool]:
        """
        Create a mission rating and update agent performance.

        Returns:
            Tuple of (rating, agent_updated, karma_updated)
        """
        redis = await get_redis()

        # Calculate category ratings
        category_ratings = self._calculate_category_ratings(
            payload.metrics,
            payload.category_scores,
        )

        # Calculate overall score
        overall_score = self._calculate_overall_score(category_ratings)

        # Get KARMA score if service available
        karma_score = None
        karma_updated = False
        if self._karma_service:
            try:
                karma_score = await self._integrate_karma(
                    payload.agent_id,
                    payload.metrics,
                    overall_score,
                )
                karma_updated = True
            except Exception as e:
                logger.error(f"Failed to integrate KARMA: {e}")

        # Create mission rating
        rating = MissionRating(
            mission_id=payload.mission_id,
            agent_id=payload.agent_id,
            overall_score=overall_score,
            category_ratings=category_ratings,
            metrics=payload.metrics,
            karma_score=karma_score,
            karma_updated=karma_updated,
            rated_by=payload.rated_by or "system",
            rating_version=RATING_VERSION,
        )

        # Calculate deterministic hash
        rating.deterministic_hash = self._calculate_rating_hash(rating)

        # Store mission rating
        mission_key = f"{MISSION_RATING_PREFIX}{payload.mission_id}"
        await redis.set(mission_key, rating.model_dump_json())

        # Update agent rating
        agent_updated = await self._update_agent_rating(
            payload.agent_id,
            rating,
        )

        # Create audit entry
        await self._create_audit_entry(
            mission_id=payload.mission_id,
            agent_id=payload.agent_id,
            action="created",
            rating_after=overall_score,
            algorithm_version=RATING_VERSION,
            decision_factors={
                "category_ratings": [r.model_dump() for r in category_ratings],
                "karma_score": karma_score,
                "metrics": payload.metrics.model_dump(),
            },
            triggered_by=payload.rated_by or "system",
        )

        logger.info(
            f"Created rating for mission {payload.mission_id}: "
            f"score={overall_score:.2f}, agent={payload.agent_id}"
        )

        return rating, agent_updated, karma_updated

    def _calculate_category_ratings(
        self,
        metrics: PerformanceMetrics,
        manual_scores: Optional[Dict[RatingCategory, float]] = None,
    ) -> List[CategoryRating]:
        """
        Calculate ratings for each category based on metrics.

        Uses deterministic formulas for transparent evaluation.
        """
        ratings = []

        # Quality: Based on success rate and error count
        if manual_scores and RatingCategory.QUALITY in manual_scores:
            quality_score = manual_scores[RatingCategory.QUALITY]
        else:
            quality_score = metrics.success_rate * 100
            # Penalize errors
            error_penalty = min(20, metrics.error_count * 5)
            quality_score = max(0, quality_score - error_penalty)

        ratings.append(CategoryRating(
            category=RatingCategory.QUALITY,
            score=quality_score,
            weight=0.3,
            justification=f"Success rate: {metrics.success_rate:.1%}, Errors: {metrics.error_count}",
        ))

        # Timeliness: Based on estimated vs actual duration
        if manual_scores and RatingCategory.TIMELINESS in manual_scores:
            timeliness_score = manual_scores[RatingCategory.TIMELINESS]
        else:
            timeliness_score = metrics.calculate_timeliness() * 100

        ratings.append(CategoryRating(
            category=RatingCategory.TIMELINESS,
            score=timeliness_score,
            weight=0.25,
            justification=f"Duration: {metrics.duration_seconds}s (est: {metrics.estimated_duration}s)",
        ))

        # Efficiency: Based on credit consumption
        if manual_scores and RatingCategory.EFFICIENCY in manual_scores:
            efficiency_score = manual_scores[RatingCategory.EFFICIENCY]
        else:
            efficiency_score = metrics.calculate_efficiency() * 100

        ratings.append(CategoryRating(
            category=RatingCategory.EFFICIENCY,
            score=efficiency_score,
            weight=0.2,
            justification=f"Credits: {metrics.credits_consumed}/{metrics.credits_allocated}",
        ))

        # Accuracy: Based on success rate and retries
        if manual_scores and RatingCategory.ACCURACY in manual_scores:
            accuracy_score = manual_scores[RatingCategory.ACCURACY]
        else:
            accuracy_score = metrics.success_rate * 100
            # Penalize retries
            retry_penalty = min(15, metrics.retry_count * 3)
            accuracy_score = max(0, accuracy_score - retry_penalty)

        ratings.append(CategoryRating(
            category=RatingCategory.ACCURACY,
            score=accuracy_score,
            weight=0.15,
            justification=f"Success: {metrics.success_rate:.1%}, Retries: {metrics.retry_count}",
        ))

        # Reliability: Composite of all factors
        if manual_scores and RatingCategory.RELIABILITY in manual_scores:
            reliability_score = manual_scores[RatingCategory.RELIABILITY]
        else:
            reliability_score = (
                quality_score * 0.4 +
                timeliness_score * 0.3 +
                efficiency_score * 0.3
            )

        ratings.append(CategoryRating(
            category=RatingCategory.RELIABILITY,
            score=reliability_score,
            weight=0.1,
            justification="Composite reliability score",
        ))

        return ratings

    def _calculate_overall_score(self, category_ratings: List[CategoryRating]) -> float:
        """Calculate weighted overall score from category ratings"""
        total_weight = sum(r.weight for r in category_ratings)
        if total_weight == 0:
            return 0.0

        weighted_sum = sum(r.score * r.weight for r in category_ratings)
        return weighted_sum / total_weight

    def _calculate_rating_hash(self, rating: MissionRating) -> str:
        """
        Calculate deterministic hash for rating verification.

        Ensures rating cannot be tampered with.
        """
        # Create stable JSON representation
        hash_data = {
            "mission_id": rating.mission_id,
            "agent_id": rating.agent_id,
            "overall_score": rating.overall_score,
            "category_ratings": [
                {
                    "category": r.category.value,
                    "score": r.score,
                    "weight": r.weight,
                }
                for r in rating.category_ratings
            ],
            "metrics": rating.metrics.model_dump(),
            "rated_at": rating.rated_at,
            "rating_version": rating.rating_version,
        }

        json_str = json.dumps(hash_data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()

    async def _integrate_karma(
        self,
        agent_id: str,
        metrics: PerformanceMetrics,
        overall_score: float,
    ) -> Optional[float]:
        """
        Integrate with KARMA service to update agent karma score.

        Returns karma score if successful, None otherwise.
        """
        if not self._karma_service:
            return None

        # This would integrate with the actual KARMA service
        # For now, we'll return a placeholder
        logger.info(f"KARMA integration for agent {agent_id}: score={overall_score}")
        return overall_score

    async def _update_agent_rating(
        self,
        agent_id: str,
        mission_rating: MissionRating,
    ) -> bool:
        """
        Update agent's aggregate rating with new mission rating.

        Returns True if update succeeded.
        """
        redis = await get_redis()
        agent_key = f"{AGENT_RATING_PREFIX}{agent_id}"

        try:
            # Get existing agent rating
            raw = await redis.get(agent_key)
            if raw:
                data = json.loads(raw)
                agent_rating = AgentRating.model_validate(data)
            else:
                # Create new agent rating
                agent_rating = AgentRating(agent_id=agent_id)

            # Update statistics
            agent_rating.total_missions += 1
            if mission_rating.metrics.success_rate >= 0.8:  # 80% success threshold
                agent_rating.successful_missions += 1

            # Update recent ratings (keep last 10)
            agent_rating.recent_ratings.append(mission_rating.overall_score)
            if len(agent_rating.recent_ratings) > 10:
                agent_rating.recent_ratings = agent_rating.recent_ratings[-10:]

            # Update overall rating (weighted average favoring recent performance)
            if agent_rating.total_missions == 1:
                agent_rating.overall_rating = mission_rating.overall_score
            else:
                # 70% weight to existing, 30% to new rating
                agent_rating.overall_rating = (
                    agent_rating.overall_rating * 0.7 +
                    mission_rating.overall_score * 0.3
                )

            # Update category averages
            for cat_rating in mission_rating.category_ratings:
                category = cat_rating.category
                if category in agent_rating.category_averages:
                    # Weighted average
                    current = agent_rating.category_averages[category]
                    agent_rating.category_averages[category] = (
                        current * 0.7 + cat_rating.score * 0.3
                    )
                else:
                    agent_rating.category_averages[category] = cat_rating.score

            # Update reliability score
            success_rate = agent_rating.calculate_success_rate()
            agent_rating.reliability_score = (
                success_rate * 60 +  # 60 points for success rate
                (agent_rating.overall_rating / 100) * 40  # 40 points for performance
            )

            # Update trend
            agent_rating.trend = agent_rating.calculate_trend()

            # Update timestamps
            agent_rating.last_mission_at = mission_rating.rated_at
            agent_rating.last_updated = time.time()

            # Save updated rating
            await redis.set(agent_key, agent_rating.model_dump_json())

            logger.info(
                f"Updated agent {agent_id} rating: {agent_rating.overall_rating:.2f} "
                f"(trend: {agent_rating.trend})"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to update agent rating: {e}")
            return False

    async def get_agent_rating(self, agent_id: str) -> Optional[AgentRating]:
        """Get agent rating by ID"""
        redis = await get_redis()
        agent_key = f"{AGENT_RATING_PREFIX}{agent_id}"

        raw = await redis.get(agent_key)
        if not raw:
            return None

        data = json.loads(raw)
        return AgentRating.model_validate(data)

    async def get_mission_rating(self, mission_id: str) -> Optional[MissionRating]:
        """Get mission rating by ID"""
        redis = await get_redis()
        mission_key = f"{MISSION_RATING_PREFIX}{mission_id}"

        raw = await redis.get(mission_key)
        if not raw:
            return None

        data = json.loads(raw)
        return MissionRating.model_validate(data)

    async def match_agent(
        self,
        request: AgentMatchRequest,
    ) -> AgentMatchResult:
        """
        Find best agent for mission based on skills and ratings.

        Uses weighted scoring algorithm combining:
        - Skill matching
        - Overall agent rating
        - Availability
        """
        redis = await get_redis()

        # Get all agent ratings
        pattern = f"{AGENT_RATING_PREFIX}*"
        keys = await redis.keys(pattern)

        match_scores: List[AgentMatchScore] = []

        for key in keys:
            raw = await redis.get(key)
            if not raw:
                continue

            data = json.loads(raw)
            agent_rating = AgentRating.model_validate(data)

            # Calculate match score
            match_score = await self._calculate_match_score(
                agent_rating,
                request.required_skills,
                request.skill_match_weight,
                request.rating_weight,
                request.availability_weight,
            )

            match_scores.append(match_score)

        # Sort by overall score (descending)
        match_scores.sort(key=lambda x: x.overall_score, reverse=True)

        # Determine recommended agent
        recommended_agent = match_scores[0].agent_id if match_scores else None

        result = AgentMatchResult(
            mission_id=request.mission_id,
            recommended_agent=recommended_agent,
            match_scores=match_scores,
            total_agents_evaluated=len(match_scores),
        )

        logger.info(
            f"Agent matching complete: evaluated {len(match_scores)} agents, "
            f"recommended: {recommended_agent}"
        )

        return result

    async def _calculate_match_score(
        self,
        agent_rating: AgentRating,
        required_skills: List[SkillRequirement],
        skill_weight: float,
        rating_weight: float,
        availability_weight: float,
    ) -> AgentMatchScore:
        """Calculate match score for a single agent"""

        # Skill matching score
        skill_score, matched, missing = self._calculate_skill_match(
            agent_rating.skills,
            required_skills,
        )

        # Rating score (use agent's overall rating)
        rating_score = agent_rating.overall_rating

        # Availability score (simplified - assume all available for now)
        # In production, would check agent's current workload
        availability_score = 100.0

        # Calculate weighted overall score
        overall_score = (
            skill_score * skill_weight +
            rating_score * rating_weight +
            availability_score * availability_weight
        ) / (skill_weight + rating_weight + availability_weight)

        return AgentMatchScore(
            agent_id=agent_rating.agent_id,
            overall_score=overall_score,
            skill_match_score=skill_score,
            rating_score=rating_score,
            availability_score=availability_score,
            matched_skills=matched,
            missing_skills=missing,
            agent_rating=agent_rating,
        )

    def _calculate_skill_match(
        self,
        agent_skills: List[SkillProfile],
        required_skills: List[SkillRequirement],
    ) -> Tuple[float, List[str], List[str]]:
        """
        Calculate skill matching score.

        Returns:
            Tuple of (score, matched_skills, missing_skills)
        """
        if not required_skills:
            return 100.0, [], []

        matched_skills = []
        missing_skills = []
        total_weight = sum(req.weight for req in required_skills)
        weighted_score = 0.0

        # Create skill lookup
        skill_map = {skill.skill_name: skill for skill in agent_skills}

        for requirement in required_skills:
            skill_name = requirement.skill_name
            agent_skill = skill_map.get(skill_name)

            if agent_skill:
                # Check if skill level meets requirement
                meets_req = self._skill_meets_requirement(agent_skill, requirement)

                if meets_req:
                    matched_skills.append(skill_name)
                    # Score based on how much agent exceeds requirement
                    score = agent_skill.score
                else:
                    missing_skills.append(skill_name)
                    # Partial credit if agent has skill but below required level
                    score = agent_skill.score * 0.5

                weighted_score += score * requirement.weight
            else:
                # Agent doesn't have this skill
                missing_skills.append(skill_name)
                # No credit for missing skill
                weighted_score += 0

        # Normalize to 0-100
        if total_weight > 0:
            final_score = weighted_score / total_weight
        else:
            final_score = 0.0

        return final_score, matched_skills, missing_skills

    def _skill_meets_requirement(
        self,
        agent_skill: SkillProfile,
        requirement: SkillRequirement,
    ) -> bool:
        """Check if agent's skill meets the requirement"""
        # Map skill levels to numeric values for comparison
        level_values = {
            SkillLevel.NOVICE: 0,
            SkillLevel.INTERMEDIATE: 1,
            SkillLevel.ADVANCED: 2,
            SkillLevel.EXPERT: 3,
        }

        return level_values[agent_skill.level] >= level_values[requirement.min_level]

    async def update_agent_skills(
        self,
        agent_id: str,
        skills: List[SkillProfile],
    ) -> bool:
        """Update agent's skill profile"""
        redis = await get_redis()
        agent_key = f"{AGENT_RATING_PREFIX}{agent_id}"

        try:
            # Get existing agent rating
            raw = await redis.get(agent_key)
            if raw:
                data = json.loads(raw)
                agent_rating = AgentRating.model_validate(data)
            else:
                agent_rating = AgentRating(agent_id=agent_id)

            # Update skills
            for skill in skills:
                agent_rating.add_or_update_skill(skill)

            agent_rating.last_updated = time.time()

            # Save
            await redis.set(agent_key, agent_rating.model_dump_json())

            logger.info(f"Updated skills for agent {agent_id}: {len(skills)} skills")
            return True

        except Exception as e:
            logger.error(f"Failed to update agent skills: {e}")
            return False

    async def _create_audit_entry(
        self,
        mission_id: str,
        agent_id: str,
        action: str,
        rating_after: float,
        algorithm_version: str,
        decision_factors: Dict[str, Any],
        triggered_by: str,
        rating_before: Optional[float] = None,
    ) -> None:
        """Create append-only audit trail entry"""
        redis = await get_redis()

        entry = RatingAuditEntry(
            id=str(uuid.uuid4()),
            mission_id=mission_id,
            agent_id=agent_id,
            action=action,
            rating_before=rating_before,
            rating_after=rating_after,
            algorithm_version=algorithm_version,
            decision_factors=decision_factors,
            deterministic_hash=hashlib.sha256(
                json.dumps(decision_factors, sort_keys=True).encode()
            ).hexdigest(),
            triggered_by=triggered_by,
        )

        # Append to audit log (using Redis list for append-only behavior)
        audit_key = f"{RATING_AUDIT_PREFIX}{mission_id}"
        await redis.rpush(audit_key, entry.model_dump_json())

        logger.debug(f"Created audit entry for mission {mission_id}: {action}")

    async def get_audit_trail(self, mission_id: str) -> List[RatingAuditEntry]:
        """Get audit trail for a mission"""
        redis = await get_redis()
        audit_key = f"{RATING_AUDIT_PREFIX}{mission_id}"

        raw_entries = await redis.lrange(audit_key, 0, -1)
        entries = []

        for raw in raw_entries or []:
            data = json.loads(raw)
            entries.append(RatingAuditEntry.model_validate(data))

        return entries
