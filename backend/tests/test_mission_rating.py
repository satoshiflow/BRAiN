"""
Tests for Mission Rating System

Comprehensive test suite for rating models, service logic, and API endpoints.
"""

import sys
import os
import time
from typing import List

# Path setup
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.app.modules.mission_rating.models import (
    AgentRating,
    CategoryRating,
    MissionRating,
    PerformanceMetrics,
    RatingCategory,
    SkillLevel,
    SkillProfile,
    SkillRequirement,
)
from backend.app.modules.mission_rating.schemas import (
    AgentMatchRequest,
    MissionRatingCreate,
)
from backend.app.modules.mission_rating.service import MissionRatingService

client = TestClient(app)


# ============================================================================
# Model Tests
# ============================================================================


def test_skill_level_from_score():
    """Test skill level derivation from numeric score"""
    assert SkillLevel.from_score(10) == SkillLevel.NOVICE
    assert SkillLevel.from_score(25) == SkillLevel.NOVICE
    assert SkillLevel.from_score(40) == SkillLevel.INTERMEDIATE
    assert SkillLevel.from_score(50) == SkillLevel.INTERMEDIATE
    assert SkillLevel.from_score(60) == SkillLevel.ADVANCED
    assert SkillLevel.from_score(75) == SkillLevel.ADVANCED
    assert SkillLevel.from_score(85) == SkillLevel.EXPERT
    assert SkillLevel.from_score(100) == SkillLevel.EXPERT


def test_skill_profile_creation():
    """Test SkillProfile factory method"""
    skill = SkillProfile.create("python", 75.0, missions_completed=10)

    assert skill.skill_name == "python"
    assert skill.score == 75.0
    assert skill.level == SkillLevel.ADVANCED
    assert skill.missions_completed == 10
    assert skill.last_used is not None


def test_skill_name_normalization():
    """Test that skill names are normalized to lowercase"""
    skill = SkillProfile.create("Python Programming", 80.0)
    assert skill.skill_name == "python programming"

    requirement = SkillRequirement(skill_name="JavaScript", min_level=SkillLevel.INTERMEDIATE)
    assert requirement.skill_name == "javascript"


def test_performance_metrics_efficiency():
    """Test efficiency calculation"""
    metrics = PerformanceMetrics(
        start_time=time.time(),
        end_time=time.time() + 100,
        duration_seconds=100,
        credits_allocated=100.0,
        credits_consumed=75.0,
    )

    efficiency = metrics.calculate_efficiency()
    assert efficiency == 0.25  # (100 - 75) / 100 = 0.25


def test_performance_metrics_timeliness():
    """Test timeliness calculation"""
    # On time (exactly as estimated)
    metrics1 = PerformanceMetrics(
        start_time=time.time(),
        duration_seconds=60.0,
        estimated_duration=60.0,
        credits_allocated=10.0,
    )
    assert metrics1.calculate_timeliness() == 1.0

    # Faster than estimated
    metrics2 = PerformanceMetrics(
        start_time=time.time(),
        duration_seconds=30.0,
        estimated_duration=60.0,
        credits_allocated=10.0,
    )
    assert metrics2.calculate_timeliness() == 1.0  # Clamped at 1.0

    # Slower than estimated
    metrics3 = PerformanceMetrics(
        start_time=time.time(),
        duration_seconds=90.0,
        estimated_duration=60.0,
        credits_allocated=10.0,
    )
    timeliness = metrics3.calculate_timeliness()
    assert 0.0 < timeliness < 1.0  # Should be between 0 and 1


def test_agent_rating_skill_management():
    """Test agent skill addition and updates"""
    agent = AgentRating(agent_id="test_agent")

    # Add new skill
    skill1 = SkillProfile.create("python", 75.0)
    agent.add_or_update_skill(skill1)

    assert len(agent.skills) == 1
    assert agent.get_skill("python") is not None
    assert agent.get_skill("python").score == 75.0

    # Update existing skill
    skill2 = SkillProfile.create("python", 85.0)
    agent.add_or_update_skill(skill2)

    assert len(agent.skills) == 1  # Still only one skill
    assert agent.get_skill("python").score == 85.0  # Score updated


def test_agent_rating_success_rate():
    """Test success rate calculation"""
    agent = AgentRating(
        agent_id="test_agent",
        total_missions=10,
        successful_missions=8,
    )

    assert agent.calculate_success_rate() == 0.8


def test_agent_rating_trend_calculation():
    """Test performance trend detection"""
    # Improving trend
    agent1 = AgentRating(agent_id="agent1")
    agent1.recent_ratings = [60, 65, 70, 75, 80]
    assert agent1.calculate_trend() == "improving"

    # Declining trend
    agent2 = AgentRating(agent_id="agent2")
    agent2.recent_ratings = [80, 75, 70, 65, 60]
    assert agent2.calculate_trend() == "declining"

    # Stable trend
    agent3 = AgentRating(agent_id="agent3")
    agent3.recent_ratings = [70, 72, 69, 71, 70]
    assert agent3.calculate_trend() == "stable"


# ============================================================================
# Service Tests
# ============================================================================


@pytest.mark.asyncio
async def test_calculate_category_ratings():
    """Test category rating calculation"""
    service = MissionRatingService()

    metrics = PerformanceMetrics(
        start_time=time.time(),
        end_time=time.time() + 60,
        duration_seconds=60.0,
        estimated_duration=60.0,
        success_rate=1.0,
        error_count=0,
        retry_count=0,
        credits_allocated=100.0,
        credits_consumed=80.0,
    )

    ratings = service._calculate_category_ratings(metrics)

    assert len(ratings) == 5  # All 5 categories
    assert all(isinstance(r, CategoryRating) for r in ratings)
    assert all(0.0 <= r.score <= 100.0 for r in ratings)

    # Find quality rating
    quality = next(r for r in ratings if r.category == RatingCategory.QUALITY)
    assert quality.score == 100.0  # Perfect success rate, no errors


@pytest.mark.asyncio
async def test_calculate_overall_score():
    """Test overall score calculation from category ratings"""
    service = MissionRatingService()

    category_ratings = [
        CategoryRating(category=RatingCategory.QUALITY, score=90.0, weight=0.3),
        CategoryRating(category=RatingCategory.TIMELINESS, score=80.0, weight=0.25),
        CategoryRating(category=RatingCategory.EFFICIENCY, score=85.0, weight=0.2),
        CategoryRating(category=RatingCategory.ACCURACY, score=88.0, weight=0.15),
        CategoryRating(category=RatingCategory.RELIABILITY, score=87.0, weight=0.1),
    ]

    overall = service._calculate_overall_score(category_ratings)

    # Calculate expected weighted average
    expected = (
        90.0 * 0.3 +
        80.0 * 0.25 +
        85.0 * 0.2 +
        88.0 * 0.15 +
        87.0 * 0.1
    ) / 1.0

    assert abs(overall - expected) < 0.01


@pytest.mark.asyncio
async def test_rating_hash_deterministic():
    """Test that rating hash is deterministic"""
    service = MissionRatingService()

    metrics = PerformanceMetrics(
        start_time=1234567890.0,
        duration_seconds=60.0,
        success_rate=1.0,
        credits_allocated=100.0,
        credits_consumed=80.0,
    )

    rating1 = MissionRating(
        mission_id="test_mission",
        agent_id="test_agent",
        overall_score=85.0,
        category_ratings=[],
        metrics=metrics,
        rated_at=1234567890.0,
        rating_version="1.0.0",
    )

    rating2 = MissionRating(
        mission_id="test_mission",
        agent_id="test_agent",
        overall_score=85.0,
        category_ratings=[],
        metrics=metrics,
        rated_at=1234567890.0,
        rating_version="1.0.0",
    )

    hash1 = service._calculate_rating_hash(rating1)
    hash2 = service._calculate_rating_hash(rating2)

    assert hash1 == hash2  # Same inputs should produce same hash


@pytest.mark.asyncio
async def test_skill_matching():
    """Test skill matching algorithm"""
    service = MissionRatingService()

    agent_skills = [
        SkillProfile.create("python", 85.0),
        SkillProfile.create("javascript", 70.0),
        SkillProfile.create("docker", 60.0),
    ]

    required_skills = [
        SkillRequirement(skill_name="python", min_level=SkillLevel.ADVANCED, weight=1.0),
        SkillRequirement(skill_name="javascript", min_level=SkillLevel.INTERMEDIATE, weight=0.8),
        SkillRequirement(skill_name="kubernetes", min_level=SkillLevel.NOVICE, weight=0.5),
    ]

    score, matched, missing = service._calculate_skill_match(agent_skills, required_skills)

    assert "python" in matched  # Has skill and meets requirement
    assert "javascript" in matched  # Has skill and meets requirement
    assert "kubernetes" in missing  # Doesn't have this skill
    assert 0.0 < score < 100.0  # Partial match


# ============================================================================
# API Tests
# ============================================================================


def test_rating_info_endpoint():
    """Test /api/mission-rating/info endpoint"""
    response = client.get("/api/mission-rating/info")

    assert response.status_code == 200
    data = response.json()

    assert data["name"] == "BRAiN Mission Rating System"
    assert "version" in data
    assert "features" in data
    assert isinstance(data["features"], list)


def test_rating_health_endpoint():
    """Test /api/mission-rating/health endpoint"""
    response = client.get("/api/mission-rating/health")

    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert "rating_service_available" in data
    assert "karma_service_available" in data
    assert "credits_service_available" in data


def test_rating_stats_endpoint():
    """Test /api/mission-rating/stats endpoint"""
    response = client.get("/api/mission-rating/stats")

    assert response.status_code == 200
    data = response.json()

    assert "total_ratings" in data
    assert "total_agents_rated" in data
    assert "avg_overall_rating" in data


def test_create_rating_endpoint():
    """Test POST /api/mission-rating/ratings endpoint"""
    payload = {
        "mission_id": f"test_mission_{int(time.time())}",
        "agent_id": f"test_agent_{int(time.time())}",
        "metrics": {
            "start_time": time.time(),
            "end_time": time.time() + 60,
            "duration_seconds": 60.0,
            "estimated_duration": 60.0,
            "success_rate": 1.0,
            "error_count": 0,
            "retry_count": 0,
            "credits_allocated": 100.0,
            "credits_consumed": 80.0,
        },
        "rated_by": "test_system",
    }

    response = client.post("/api/mission-rating/ratings", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert "rating" in data
    assert "agent_updated" in data
    assert "karma_updated" in data
    assert data["message"] == "Rating created successfully"

    # Verify rating structure
    rating = data["rating"]
    assert rating["mission_id"] == payload["mission_id"]
    assert rating["agent_id"] == payload["agent_id"]
    assert 0.0 <= rating["overall_score"] <= 100.0
    assert "category_ratings" in rating
    assert "deterministic_hash" in rating


def test_agent_matching_endpoint():
    """Test POST /api/mission-rating/match endpoint"""
    payload = {
        "mission_id": "test_mission_match",
        "required_skills": [
            {
                "skill_name": "python",
                "min_level": "intermediate",
                "weight": 1.0,
            },
            {
                "skill_name": "docker",
                "min_level": "novice",
                "weight": 0.5,
            },
        ],
        "skill_match_weight": 0.5,
        "rating_weight": 0.3,
        "availability_weight": 0.2,
    }

    response = client.post("/api/mission-rating/match", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert "mission_id" in data
    assert "recommended_agent" in data
    assert "match_scores" in data
    assert "total_agents_evaluated" in data
    assert isinstance(data["match_scores"], list)


def test_update_agent_skills_endpoint():
    """Test PUT /api/mission-rating/agents/{agent_id}/skills endpoint"""
    agent_id = f"test_agent_{int(time.time())}"

    payload = {
        "agent_id": agent_id,
        "skills": [
            {
                "skill_name": "python",
                "score": 85.0,
                "level": "expert",
                "missions_completed": 10,
            },
            {
                "skill_name": "javascript",
                "score": 70.0,
                "level": "advanced",
                "missions_completed": 5,
            },
        ],
    }

    response = client.put(
        f"/api/mission-rating/agents/{agent_id}/skills",
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "Updated 2 skills" in data["message"]


def test_mission_allocation_endpoint():
    """Test POST /api/mission-rating/allocate endpoint"""
    payload = {
        "mission_id": f"test_mission_alloc_{int(time.time())}",
        "required_skills": [
            {
                "skill_name": "python",
                "min_level": "intermediate",
                "weight": 1.0,
            },
        ],
        "estimated_duration": 120.0,
        "estimated_credits": 50.0,
        "prefer_availability": True,
        "min_skill_match": 70.0,
    }

    response = client.post("/api/mission-rating/allocate", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert "mission_id" in data
    assert "allocated_agent" in data
    assert "success" in data
    assert "message" in data
    assert "match_analysis" in data


def test_get_audit_trail_endpoint():
    """Test GET /api/mission-rating/audit/{mission_id} endpoint"""
    # First create a rating to generate audit trail
    mission_id = f"test_mission_audit_{int(time.time())}"

    create_payload = {
        "mission_id": mission_id,
        "agent_id": "test_agent_audit",
        "metrics": {
            "start_time": time.time(),
            "duration_seconds": 60.0,
            "success_rate": 1.0,
            "credits_allocated": 100.0,
            "credits_consumed": 80.0,
        },
    }

    client.post("/api/mission-rating/ratings", json=create_payload)

    # Now get audit trail
    response = client.get(f"/api/mission-rating/audit/{mission_id}")

    assert response.status_code == 200
    data = response.json()

    assert "entries" in data
    assert "total_entries" in data
    assert isinstance(data["entries"], list)

    if data["total_entries"] > 0:
        entry = data["entries"][0]
        assert "mission_id" in entry
        assert "agent_id" in entry
        assert "action" in entry
        assert "deterministic_hash" in entry


def test_rating_validation():
    """Test that invalid rating data is rejected"""
    # Invalid: score out of range
    invalid_payload = {
        "mission_id": "invalid_test",
        "agent_id": "test_agent",
        "metrics": {
            "start_time": time.time(),
            "success_rate": 1.5,  # Invalid: > 1.0
            "credits_allocated": 100.0,
            "credits_consumed": 80.0,
        },
    }

    response = client.post("/api/mission-rating/ratings", json=invalid_payload)
    assert response.status_code == 422  # Validation error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
