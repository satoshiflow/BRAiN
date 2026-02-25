"""Mission Rating System - Skill-based agent matching and performance evaluation.

Implements Myzel-Hybrid-Charta principles:
- Skill-based matching (not competition)
- Cooperation incentives
- Performance evaluation for credit allocation
- KARMA integration for semantic matching (Phase 9)
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# KARMA Integration (Phase 9)
try:
    from backend.app.modules.karma.core.service import KarmaService
    from backend.app.modules.karma.schemas import KarmaMetrics
    from backend.app.modules.dna.core.service import DNAService
    KARMA_AVAILABLE = True
except ImportError:
    KARMA_AVAILABLE = False
    logger.warning("[MissionRatingSystem] KARMA module not available - semantic matching disabled")


class MissionStatus(str, Enum):
    """Mission execution status."""

    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentSkills:
    """Agent skill profile."""

    agent_id: str
    skills: Dict[str, float]  # skill_name -> proficiency (0.0-1.0)
    specializations: List[str]
    experience_level: float  # 0.0-1.0
    collaboration_score: float  # 0.0-1.0 (cooperation metric)
    success_rate: float  # 0.0-1.0


@dataclass
class MissionRequirements:
    """Mission requirements."""

    mission_id: str
    required_skills: Dict[str, float]  # skill_name -> minimum_proficiency
    complexity: float  # 0.5-5.0
    estimated_duration_hours: float
    priority: int  # 1-10
    collaboration_allowed: bool = True


@dataclass
class MissionRating:
    """Mission completion rating."""

    mission_id: str
    agent_id: str
    started_at: datetime
    completed_at: Optional[datetime]
    status: MissionStatus

    # Performance metrics
    quality_score: Optional[float] = None  # 0.0-1.0
    efficiency_score: Optional[float] = None  # 0.0-1.0
    collaboration_score: Optional[float] = None  # 0.0-1.0
    overall_score: Optional[float] = None  # 0.0-1.0

    # Resource usage
    actual_duration_hours: Optional[float] = None
    credits_consumed: Optional[float] = None
    credits_allocated: Optional[float] = None

    # Feedback
    agent_feedback: Optional[str] = None
    supervisor_feedback: Optional[str] = None


class MissionRatingSystem:
    """Mission rating and skill-based agent matching.

    Responsibilities:
    - Match agents to missions based on skills (KARMA-enhanced)
    - Rate mission performance
    - Update agent skill profiles
    - Calculate credit adjustments
    - Semantic matching via KARMA integration (Phase 9)
    """

    def __init__(self, enable_karma: bool = True):
        self.agent_profiles: Dict[str, AgentSkills] = {}
        self.mission_ratings: List[MissionRating] = []

        # KARMA Integration (Phase 9)
        self.karma_service: Optional[KarmaService] = None
        if enable_karma and KARMA_AVAILABLE:
            try:
                dna_service = DNAService()
                self.karma_service = KarmaService(dna_service)
                logger.info("[MissionRatingSystem] KARMA integration enabled")
            except Exception as e:
                logger.error(f"[MissionRatingSystem] Failed to initialize KARMA: {e}")
                self.karma_service = None
        else:
            logger.info("[MissionRatingSystem] KARMA integration disabled")

        logger.info("[MissionRatingSystem] Initialized")

    def register_agent(
        self,
        agent_id: str,
        skills: Dict[str, float],
        specializations: List[str],
    ) -> AgentSkills:
        """Register agent with skill profile.

        Args:
            agent_id: Agent identifier
            skills: Skill proficiency map
            specializations: List of specializations

        Returns:
            Agent skill profile
        """
        profile = AgentSkills(
            agent_id=agent_id,
            skills=skills,
            specializations=specializations,
            experience_level=0.5,  # Default to average
            collaboration_score=1.0,  # Assume good until proven otherwise
            success_rate=1.0,  # Optimistic default
        )

        self.agent_profiles[agent_id] = profile

        logger.info(
            f"[MissionRatingSystem] Registered agent {agent_id} with "
            f"{len(skills)} skills and {len(specializations)} specializations"
        )

        return profile

    def find_best_match(
        self,
        requirements: MissionRequirements,
        available_agents: Optional[List[str]] = None,
        enable_karma: bool = True,
    ) -> List[Dict]:
        """Find best agent matches for mission.

        Myzel-Hybrid: Skill-based matching, not competition.
        Phase 9: KARMA-enhanced semantic matching.

        Args:
            requirements: Mission requirements
            available_agents: List of available agent IDs (None = all)
            enable_karma: Use KARMA-enhanced scoring (default: True)

        Returns:
            List of agent matches sorted by suitability score
        """
        if available_agents is None:
            available_agents = list(self.agent_profiles.keys())

        matches = []

        for agent_id in available_agents:
            if agent_id not in self.agent_profiles:
                continue

            profile = self.agent_profiles[agent_id]

            # Calculate base skill-based score
            base_score = self._calculate_match_score(profile, requirements)

            # Enhance with KARMA if enabled
            if enable_karma and self.karma_service is not None:
                final_score = self._calculate_karma_enhanced_score(profile, requirements, base_score)
            else:
                final_score = base_score

            match_entry = {
                "agent_id": agent_id,
                "match_score": final_score["total_score"],
                "skill_match": final_score["skill_match"],
                "experience_match": final_score["experience_match"],
                "collaboration_fit": final_score["collaboration_fit"],
                "success_rate": profile.success_rate,
                "recommended": final_score["total_score"] >= 0.6,  # Threshold
            }

            # Add KARMA score if available
            if "karma_score" in final_score:
                match_entry["karma_score"] = final_score["karma_score"]
                match_entry["karma_enabled"] = final_score.get("karma_enabled", False)

            matches.append(match_entry)

        # Sort by match score (descending)
        matches.sort(key=lambda m: m["match_score"], reverse=True)

        karma_status = "KARMA-enhanced" if enable_karma and self.karma_service else "skill-based"
        logger.info(
            f"[MissionRatingSystem] Found {len(matches)} {karma_status} matches for mission {requirements.mission_id} "
            f"(best: {matches[0]['match_score']:.3f})" if matches else "No matches found"
        )

        return matches

    def _calculate_match_score(
        self,
        agent: AgentSkills,
        requirements: MissionRequirements,
    ) -> Dict:
        """Calculate match score between agent and mission.

        Args:
            agent: Agent skill profile
            requirements: Mission requirements

        Returns:
            Match score breakdown
        """
        # Skill match: check if agent meets required skill levels
        skill_matches = []
        for skill, required_level in requirements.required_skills.items():
            agent_level = agent.skills.get(skill, 0.0)
            if agent_level >= required_level:
                skill_matches.append(1.0)
            else:
                # Partial credit for close matches
                skill_matches.append(agent_level / required_level if required_level > 0 else 0.0)

        skill_match = sum(skill_matches) / len(skill_matches) if skill_matches else 0.0

        # Experience match: does agent experience align with mission complexity?
        complexity_normalized = (requirements.complexity - 0.5) / 4.5  # 0.5-5.0 -> 0.0-1.0
        experience_diff = abs(agent.experience_level - complexity_normalized)
        experience_match = 1.0 - experience_diff  # Closer is better

        # Collaboration fit (if mission requires collaboration)
        if requirements.collaboration_allowed:
            collaboration_fit = agent.collaboration_score
        else:
            collaboration_fit = 1.0  # Not relevant

        # Overall score: weighted average
        total_score = (
            skill_match * 0.6 +        # 60% weight on skills
            experience_match * 0.2 +   # 20% weight on experience
            collaboration_fit * 0.1 +  # 10% weight on collaboration
            agent.success_rate * 0.1   # 10% weight on success rate
        )

        return {
            "total_score": total_score,
            "skill_match": skill_match,
            "experience_match": experience_match,
            "collaboration_fit": collaboration_fit,
        }

    def _calculate_karma_enhanced_score(
        self,
        agent: AgentSkills,
        requirements: MissionRequirements,
        base_score: Dict,
    ) -> Dict:
        """Calculate KARMA-enhanced match score (Phase 9).

        Integrates KARMA semantic scoring with skill-based matching.

        Args:
            agent: Agent skill profile
            requirements: Mission requirements
            base_score: Base skill-based score

        Returns:
            Enhanced score with KARMA integration
        """
        if self.karma_service is None:
            # No KARMA available - return base score
            return base_score

        try:
            # Build KARMA metrics from agent profile
            # Get recent performance data from mission ratings
            recent_ratings = [
                r for r in self.mission_ratings
                if r.agent_id == agent.agent_id and r.status == MissionStatus.COMPLETED
            ][-10:]  # Last 10 missions

            if not recent_ratings:
                # No history - use defaults
                karma_metrics = KarmaMetrics(
                    success_rate=agent.success_rate,
                    avg_latency_ms=5000.0,  # Default 5s
                    policy_violations=0,
                    user_rating_avg=3.0,  # Neutral
                    credit_consumption_per_task=10.0,  # Default
                )
            else:
                # Calculate metrics from recent ratings
                success_count = len([r for r in recent_ratings if r.overall_score and r.overall_score >= 0.7])
                success_rate = success_count / len(recent_ratings) if recent_ratings else agent.success_rate

                avg_duration = sum(
                    r.actual_duration_hours for r in recent_ratings if r.actual_duration_hours
                ) / len(recent_ratings) if recent_ratings else 1.0

                avg_latency_ms = avg_duration * 3600 * 1000  # Convert hours to ms

                avg_credits = sum(
                    r.credits_consumed for r in recent_ratings if r.credits_consumed
                ) / len(recent_ratings) if recent_ratings else 10.0

                # Assume no policy violations for now (would come from immune system)
                policy_violations = 0

                # Calculate average quality as proxy for user rating
                avg_quality = sum(
                    r.quality_score for r in recent_ratings if r.quality_score
                ) / len(recent_ratings) if recent_ratings else 0.7

                user_rating = 3.0 + (avg_quality - 0.5) * 4  # Map 0.0-1.0 to 1.0-5.0

                karma_metrics = KarmaMetrics(
                    success_rate=success_rate,
                    avg_latency_ms=avg_latency_ms,
                    policy_violations=policy_violations,
                    user_rating_avg=user_rating,
                    credit_consumption_per_task=avg_credits,
                )

            # Compute KARMA score
            karma_score_result = self.karma_service.compute_score(agent.agent_id, karma_metrics)
            karma_score_normalized = karma_score_result.score / 100.0  # 0-100 -> 0.0-1.0

            # Integrate KARMA score with base score
            # KARMA contributes 15% to overall score (skill-based matching still dominates)
            enhanced_score = (
                base_score["total_score"] * 0.85 +  # 85% from skill-based matching
                karma_score_normalized * 0.15        # 15% from KARMA semantic scoring
            )

            logger.info(
                f"[MissionRatingSystem] KARMA-enhanced score for {agent.agent_id}: "
                f"base={base_score['total_score']:.3f}, karma={karma_score_normalized:.3f}, "
                f"enhanced={enhanced_score:.3f}"
            )

            return {
                "total_score": enhanced_score,
                "skill_match": base_score["skill_match"],
                "experience_match": base_score["experience_match"],
                "collaboration_fit": base_score["collaboration_fit"],
                "karma_score": karma_score_normalized,
                "karma_enabled": True,
            }

        except Exception as e:
            logger.error(f"[MissionRatingSystem] KARMA scoring failed for {agent.agent_id}: {e}")
            # Fallback to base score
            return base_score

    def rate_mission(
        self,
        mission_id: str,
        agent_id: str,
        quality_score: float,
        efficiency_score: float,
        collaboration_score: float,
        actual_duration_hours: float,
        credits_consumed: float,
        credits_allocated: float,
        agent_feedback: Optional[str] = None,
        supervisor_feedback: Optional[str] = None,
    ) -> MissionRating:
        """Rate completed mission.

        Args:
            mission_id: Mission identifier
            agent_id: Agent identifier
            quality_score: Quality of work (0.0-1.0)
            efficiency_score: Efficiency (0.0-1.0)
            collaboration_score: Collaboration quality (0.0-1.0)
            actual_duration_hours: Actual time taken
            credits_consumed: Credits consumed
            credits_allocated: Credits allocated
            agent_feedback: Optional agent feedback
            supervisor_feedback: Optional supervisor feedback

        Returns:
            Mission rating
        """
        # Calculate overall score (weighted average)
        overall_score = (
            quality_score * 0.5 +         # 50% quality
            efficiency_score * 0.3 +      # 30% efficiency
            collaboration_score * 0.2     # 20% collaboration
        )

        rating = MissionRating(
            mission_id=mission_id,
            agent_id=agent_id,
            started_at=datetime.now(timezone.utc),  # TODO: Track actual start time
            completed_at=datetime.now(timezone.utc),
            status=MissionStatus.COMPLETED,
            quality_score=quality_score,
            efficiency_score=efficiency_score,
            collaboration_score=collaboration_score,
            overall_score=overall_score,
            actual_duration_hours=actual_duration_hours,
            credits_consumed=credits_consumed,
            credits_allocated=credits_allocated,
            agent_feedback=agent_feedback,
            supervisor_feedback=supervisor_feedback,
        )

        self.mission_ratings.append(rating)

        # Update agent profile based on performance
        self._update_agent_profile(agent_id, rating)

        logger.info(
            f"[MissionRatingSystem] Rated mission {mission_id} by agent {agent_id}: "
            f"overall={overall_score:.3f} (Q:{quality_score:.2f}, E:{efficiency_score:.2f}, C:{collaboration_score:.2f})"
        )

        return rating

    def _update_agent_profile(self, agent_id: str, rating: MissionRating):
        """Update agent profile based on mission performance.

        Args:
            agent_id: Agent identifier
            rating: Mission rating
        """
        if agent_id not in self.agent_profiles:
            logger.warning(f"[MissionRatingSystem] Agent {agent_id} not found, skipping profile update")
            return

        profile = self.agent_profiles[agent_id]

        # Update success rate (exponential moving average)
        success = 1.0 if rating.overall_score >= 0.7 else 0.0
        profile.success_rate = profile.success_rate * 0.9 + success * 0.1

        # Update collaboration score
        if rating.collaboration_score is not None:
            profile.collaboration_score = (
                profile.collaboration_score * 0.8 + rating.collaboration_score * 0.2
            )

        # Update experience level based on mission complexity
        # TODO: Extract complexity from mission requirements
        # profile.experience_level = ...

        logger.debug(
            f"[MissionRatingSystem] Updated agent {agent_id}: "
            f"success_rate={profile.success_rate:.3f}, "
            f"collaboration={profile.collaboration_score:.3f}"
        )

    def calculate_skill_bonus(
        self,
        agent_id: str,
        base_allocation: float,
    ) -> float:
        """Calculate skill-based credit bonus.

        Myzel-Hybrid: Reward skill development and collaboration.

        Args:
            agent_id: Agent identifier
            base_allocation: Base credit allocation

        Returns:
            Bonus amount (positive)
        """
        if agent_id not in self.agent_profiles:
            return 0.0

        profile = self.agent_profiles[agent_id]

        # Recent performance (last 10 missions)
        recent_ratings = [
            r for r in self.mission_ratings[-10:]
            if r.agent_id == agent_id and r.overall_score is not None
        ]

        if not recent_ratings:
            return 0.0

        avg_performance = sum(r.overall_score for r in recent_ratings) / len(recent_ratings)

        # Bonus factors
        performance_bonus = (avg_performance - 0.7) * 0.5 if avg_performance > 0.7 else 0.0
        collaboration_bonus = (profile.collaboration_score - 0.8) * 0.3 if profile.collaboration_score > 0.8 else 0.0

        total_bonus_multiplier = performance_bonus + collaboration_bonus
        bonus = base_allocation * total_bonus_multiplier

        logger.info(
            f"[MissionRatingSystem] Skill bonus for {agent_id}: "
            f"{bonus:.2f} credits ({total_bonus_multiplier * 100:.1f}% of base)"
        )

        return bonus

    def get_agent_statistics(self, agent_id: str) -> Optional[Dict]:
        """Get agent statistics.

        Args:
            agent_id: Agent identifier

        Returns:
            Statistics dictionary or None
        """
        if agent_id not in self.agent_profiles:
            return None

        profile = self.agent_profiles[agent_id]
        agent_ratings = [r for r in self.mission_ratings if r.agent_id == agent_id]

        completed_missions = len([r for r in agent_ratings if r.status == MissionStatus.COMPLETED])
        failed_missions = len([r for r in agent_ratings if r.status == MissionStatus.FAILED])

        completed_ratings = [r for r in agent_ratings if r.overall_score is not None]
        avg_score = (
            sum(r.overall_score for r in completed_ratings) / len(completed_ratings)
            if completed_ratings else 0.0
        )

        return {
            "agent_id": agent_id,
            "total_missions": len(agent_ratings),
            "completed_missions": completed_missions,
            "failed_missions": failed_missions,
            "success_rate": profile.success_rate,
            "average_score": avg_score,
            "collaboration_score": profile.collaboration_score,
            "experience_level": profile.experience_level,
            "skills": profile.skills,
            "specializations": profile.specializations,
        }


# Global rating system instance
_rating_system: Optional[MissionRatingSystem] = None


def get_rating_system() -> MissionRatingSystem:
    """Get global mission rating system instance.

    Returns:
        MissionRatingSystem instance
    """
    global _rating_system
    if _rating_system is None:
        _rating_system = MissionRatingSystem()
    return _rating_system
