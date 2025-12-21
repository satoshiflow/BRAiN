# Mission Rating System

**Version:** 1.0.0
**Module:** `backend/app/modules/mission_rating/`

## Overview

The Mission Rating System provides comprehensive mission performance evaluation, skill-based agent matching, and transparent rating mechanisms integrated with the KARMA framework. It enables:

- **Deterministic Rating**: Transparent, reproducible performance scores
- **Skill-Based Matching**: Intelligent agent-to-mission allocation
- **Performance Tracking**: Multi-category evaluation across quality, timeliness, efficiency, accuracy, and reliability
- **Audit Trail**: Append-only logging of all rating decisions
- **KARMA Integration**: Automatic update of agent KARMA scores based on performance

## Architecture

### Components

```
mission_rating/
├── __init__.py          # Module exports
├── models.py            # Core data models (Pydantic)
├── schemas.py           # API request/response schemas
├── service.py           # Business logic
├── router.py            # REST API endpoints
└── README.md            # This file
```

### Key Models

#### SkillProfile
Represents an agent's proficiency in a specific skill.

```python
SkillProfile(
    skill_name="python",
    score=85.0,              # 0-100
    level=SkillLevel.EXPERT, # NOVICE/INTERMEDIATE/ADVANCED/EXPERT
    missions_completed=10,
    last_used=1234567890.0
)
```

**Skill Levels:**
- `NOVICE`: 0-25 score
- `INTERMEDIATE`: 26-50 score
- `ADVANCED`: 51-75 score
- `EXPERT`: 76-100 score

#### SkillRequirement
Defines skill requirements for a mission.

```python
SkillRequirement(
    skill_name="python",
    min_level=SkillLevel.INTERMEDIATE,
    weight=1.0  # Importance weight (0-1)
)
```

#### PerformanceMetrics
Captures detailed performance data for a mission execution.

```python
PerformanceMetrics(
    start_time=1234567890.0,
    end_time=1234567950.0,
    duration_seconds=60.0,
    estimated_duration=60.0,
    success_rate=1.0,           # 0-1
    error_count=0,
    retry_count=0,
    credits_allocated=100.0,
    credits_consumed=80.0,
    cpu_usage_avg=45.5,         # Optional
    memory_usage_avg=512.0,     # Optional MB
    custom_metrics={}           # Additional metrics
)
```

**Calculated Metrics:**
- `calculate_efficiency()`: Resource efficiency based on credit consumption
- `calculate_timeliness()`: Time efficiency based on estimated vs actual duration

#### MissionRating
Complete mission rating with category breakdown.

```python
MissionRating(
    mission_id="mission_123",
    agent_id="coder_agent",
    overall_score=87.5,         # 0-100
    category_ratings=[...],     # List[CategoryRating]
    metrics=PerformanceMetrics(...),
    karma_score=85.0,           # Optional
    karma_updated=True,
    rated_at=1234567890.0,
    rated_by="system",
    is_verified=False,
    rating_version="1.0.0",
    deterministic_hash="abc123..." # SHA-256 hash for verification
)
```

**Rating Categories:**
- `QUALITY`: Success rate and error metrics (weight: 0.3)
- `TIMELINESS`: Actual vs estimated duration (weight: 0.25)
- `EFFICIENCY`: Credit consumption (weight: 0.2)
- `ACCURACY`: Retry count and success rate (weight: 0.15)
- `RELIABILITY`: Composite score (weight: 0.1)

#### AgentRating
Aggregate agent performance profile.

```python
AgentRating(
    agent_id="coder_agent",
    overall_rating=85.0,        # 0-100
    total_missions=50,
    successful_missions=47,
    category_averages={...},    # Dict[RatingCategory, float]
    skills=[...],               # List[SkillProfile]
    recent_ratings=[...],       # Last 10 ratings
    trend="improving",          # improving/declining/stable
    avg_completion_time=120.0,
    reliability_score=92.0,
    last_mission_at=1234567890.0,
    last_updated=1234567890.0
)
```

## Rating Algorithm

### Category Scoring

#### 1. Quality Score
```
score = success_rate * 100
score -= min(20, error_count * 5)  # Penalty for errors
score = clamp(score, 0, 100)
```

#### 2. Timeliness Score
```
if estimated_duration == 0:
    score = 100
else:
    ratio = actual_duration / estimated_duration
    score = max(0, min(100, (2.0 - ratio) * 100))
```

#### 3. Efficiency Score
```
if allocated_credits == 0:
    score = 100
else:
    efficiency = 1.0 - (consumed_credits / allocated_credits)
    score = max(0, efficiency * 100)
```

#### 4. Accuracy Score
```
score = success_rate * 100
score -= min(15, retry_count * 3)  # Penalty for retries
score = clamp(score, 0, 100)
```

#### 5. Reliability Score
```
score = (
    quality_score * 0.4 +
    timeliness_score * 0.3 +
    efficiency_score * 0.3
)
```

### Overall Score Calculation

Weighted average of category scores:

```
overall_score = Σ(category_score * category_weight) / Σ(category_weight)
```

### Agent Rating Update

When a new mission rating is created:

```python
# First mission
if total_missions == 1:
    overall_rating = mission_score

# Subsequent missions (70% existing, 30% new)
else:
    overall_rating = overall_rating * 0.7 + mission_score * 0.3

# Update reliability
success_rate = successful_missions / total_missions
reliability_score = success_rate * 60 + (overall_rating / 100) * 40

# Update trend
if len(recent_ratings) >= 3:
    first_half_avg = avg(recent_ratings[:half])
    second_half_avg = avg(recent_ratings[half:])

    if second_half_avg - first_half_avg > 5:
        trend = "improving"
    elif second_half_avg - first_half_avg < -5:
        trend = "declining"
    else:
        trend = "stable"
```

## Skill Matching Algorithm

### Match Score Calculation

For each agent, calculate:

1. **Skill Match Score** (0-100):
```python
total_weight = Σ(requirement.weight for requirement in required_skills)
weighted_score = 0

for requirement in required_skills:
    if agent has skill:
        if agent_skill.level >= requirement.min_level:
            # Full credit
            weighted_score += agent_skill.score * requirement.weight
        else:
            # Partial credit (50%)
            weighted_score += agent_skill.score * 0.5 * requirement.weight
    else:
        # No credit for missing skill
        weighted_score += 0

skill_match_score = weighted_score / total_weight
```

2. **Rating Score** (0-100):
```python
rating_score = agent.overall_rating
```

3. **Availability Score** (0-100):
```python
# Simplified - would check actual workload in production
availability_score = 100.0
```

4. **Overall Match Score**:
```python
overall_score = (
    skill_match_score * skill_weight +
    rating_score * rating_weight +
    availability_score * availability_weight
) / (skill_weight + rating_weight + availability_weight)
```

### Agent Selection

Agents are ranked by overall match score (descending). The top-ranked agent is recommended.

## API Endpoints

### 1. Create Rating

**POST** `/api/mission-rating/ratings`

Create a rating for a completed mission.

**Request:**
```json
{
  "mission_id": "mission_123",
  "agent_id": "coder_agent",
  "metrics": {
    "start_time": 1234567890.0,
    "end_time": 1234567950.0,
    "duration_seconds": 60.0,
    "estimated_duration": 60.0,
    "success_rate": 1.0,
    "error_count": 0,
    "retry_count": 0,
    "credits_allocated": 100.0,
    "credits_consumed": 80.0
  },
  "category_scores": null,
  "rated_by": "system",
  "notes": "Excellent performance"
}
```

**Response:**
```json
{
  "rating": {
    "mission_id": "mission_123",
    "agent_id": "coder_agent",
    "overall_score": 87.5,
    "category_ratings": [...],
    "metrics": {...},
    "karma_score": 85.0,
    "karma_updated": true,
    "deterministic_hash": "abc123..."
  },
  "agent_updated": true,
  "karma_updated": true,
  "message": "Rating created successfully"
}
```

### 2. Get Mission Rating

**GET** `/api/mission-rating/ratings/mission/{mission_id}`

Retrieve rating for a specific mission.

**Response:**
```json
{
  "mission_id": "mission_123",
  "agent_id": "coder_agent",
  "overall_score": 87.5,
  "category_ratings": [
    {
      "category": "quality",
      "score": 95.0,
      "weight": 0.3,
      "justification": "Success rate: 100%, Errors: 0"
    },
    ...
  ],
  "metrics": {...},
  "rated_at": 1234567890.0
}
```

### 3. Get Agent Rating

**GET** `/api/mission-rating/ratings/agent/{agent_id}`

Retrieve aggregate rating for an agent.

**Response:**
```json
{
  "agent_id": "coder_agent",
  "overall_rating": 85.0,
  "total_missions": 50,
  "successful_missions": 47,
  "category_averages": {
    "quality": 88.5,
    "timeliness": 82.3,
    "efficiency": 90.1,
    "accuracy": 86.7,
    "reliability": 87.9
  },
  "skills": [
    {
      "skill_name": "python",
      "score": 85.0,
      "level": "expert",
      "missions_completed": 30
    }
  ],
  "recent_ratings": [82, 84, 87, 85, 88, 86, 89, 87, 90, 85],
  "trend": "improving",
  "reliability_score": 92.0
}
```

### 4. Match Agent for Mission

**POST** `/api/mission-rating/match`

Find best agent for a mission based on required skills.

**Request:**
```json
{
  "mission_id": "mission_456",
  "required_skills": [
    {
      "skill_name": "python",
      "min_level": "advanced",
      "weight": 1.0
    },
    {
      "skill_name": "docker",
      "min_level": "intermediate",
      "weight": 0.5
    }
  ],
  "skill_match_weight": 0.5,
  "rating_weight": 0.3,
  "availability_weight": 0.2
}
```

**Response:**
```json
{
  "mission_id": "mission_456",
  "recommended_agent": "coder_agent",
  "match_scores": [
    {
      "agent_id": "coder_agent",
      "overall_score": 88.5,
      "skill_match_score": 92.0,
      "rating_score": 85.0,
      "availability_score": 100.0,
      "matched_skills": ["python", "docker"],
      "missing_skills": []
    },
    ...
  ],
  "total_agents_evaluated": 5
}
```

### 5. Allocate Mission

**POST** `/api/mission-rating/allocate`

Allocate mission to best-matched agent (combines matching + assignment).

**Request:**
```json
{
  "mission_id": "mission_789",
  "required_skills": [...],
  "estimated_duration": 120.0,
  "estimated_credits": 50.0,
  "prefer_availability": true,
  "min_skill_match": 70.0
}
```

**Response:**
```json
{
  "mission_id": "mission_789",
  "allocated_agent": "coder_agent",
  "allocation_score": 88.5,
  "success": true,
  "message": "Mission allocated to coder_agent",
  "match_analysis": {...}
}
```

### 6. Update Agent Skills

**PUT** `/api/mission-rating/agents/{agent_id}/skills`

Update agent's skill profile.

**Request:**
```json
{
  "agent_id": "coder_agent",
  "skills": [
    {
      "skill_name": "python",
      "score": 90.0,
      "level": "expert",
      "missions_completed": 35
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Updated 1 skills for agent coder_agent"
}
```

### 7. Get Audit Trail

**GET** `/api/mission-rating/audit/{mission_id}`

Retrieve append-only audit log for mission ratings.

**Response:**
```json
{
  "entries": [
    {
      "id": "audit_001",
      "mission_id": "mission_123",
      "agent_id": "coder_agent",
      "action": "created",
      "rating_before": null,
      "rating_after": 87.5,
      "algorithm_version": "1.0.0",
      "decision_factors": {...},
      "deterministic_hash": "def456...",
      "timestamp": 1234567890.0,
      "triggered_by": "system"
    }
  ],
  "total_entries": 1,
  "oldest_entry": 1234567890.0,
  "newest_entry": 1234567890.0
}
```

### 8. Get Statistics

**GET** `/api/mission-rating/stats`

System-wide rating statistics.

### 9. Health Check

**GET** `/api/mission-rating/health`

Service health status.

### 10. System Info

**GET** `/api/mission-rating/info`

Module information and capabilities.

## Usage Examples

### Example 1: Rate a Completed Mission

```python
import httpx

# Mission completed - create rating
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/mission-rating/ratings",
        json={
            "mission_id": "deploy_prod_v2",
            "agent_id": "ops_agent",
            "metrics": {
                "start_time": 1234567890.0,
                "end_time": 1234567950.0,
                "duration_seconds": 60.0,
                "estimated_duration": 90.0,  # Faster than estimated!
                "success_rate": 1.0,
                "error_count": 0,
                "retry_count": 0,
                "credits_allocated": 50.0,
                "credits_consumed": 35.0,  # Efficient!
            },
            "rated_by": "supervisor",
        }
    )

    rating = response.json()
    print(f"Overall score: {rating['rating']['overall_score']}")
    # Output: Overall score: 92.3
```

### Example 2: Find Best Agent for Mission

```python
# Find agent for code review mission
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/mission-rating/match",
        json={
            "mission_id": "code_review_pr_123",
            "required_skills": [
                {
                    "skill_name": "python",
                    "min_level": "expert",
                    "weight": 1.0
                },
                {
                    "skill_name": "code_review",
                    "min_level": "advanced",
                    "weight": 0.8
                }
            ],
            "skill_match_weight": 0.6,  # Prioritize skills
            "rating_weight": 0.4,
        }
    )

    result = response.json()
    best_agent = result["recommended_agent"]
    print(f"Recommended: {best_agent}")
    # Output: Recommended: coder_agent
```

### Example 3: Update Agent Skills After Training

```python
# Agent completed Python training - update skill
async with httpx.AsyncClient() as client:
    response = await client.put(
        "http://localhost:8000/api/mission-rating/agents/junior_dev/skills",
        json={
            "agent_id": "junior_dev",
            "skills": [
                {
                    "skill_name": "python",
                    "score": 65.0,  # Improved from 45
                    "level": "advanced",
                    "missions_completed": 15
                }
            ]
        }
    )

    print(response.json()["message"])
    # Output: Updated 1 skills for agent junior_dev
```

## Security & Integrity

### Deterministic Rating

All ratings are deterministic and verifiable:

1. **Hash Calculation**: SHA-256 hash of rating inputs
2. **Immutable Inputs**: mission_id, agent_id, metrics, scores, timestamp
3. **Verification**: Anyone can recalculate hash to verify integrity

### Append-Only Audit Trail

All rating decisions are logged with:
- Timestamp
- Rating changes (before/after)
- Decision factors (transparent)
- Algorithm version
- Deterministic hash

**Properties:**
- **Immutable**: Cannot be modified after creation
- **Traceable**: Complete history of all changes
- **Transparent**: All decision factors recorded
- **Verifiable**: Hash-based integrity checks

### Fail-Closed Design

The system fails securely:
- Invalid ratings rejected (validation)
- Missing skills = no credit (strict matching)
- Errors heavily penalized (quality score)
- Manual overrides logged (audit trail)

## Integration with KARMA

The rating system integrates with the KARMA framework to update agent KARMA scores:

```python
# After rating creation
karma_score = await karma_service.compute_score(
    agent_id=agent_id,
    metrics=KarmaMetrics(
        success_rate=performance_metrics.success_rate,
        avg_latency_ms=performance_metrics.duration_seconds * 1000,
        policy_violations=0,
        user_rating_avg=overall_score / 20,  # Convert to 0-5 scale
        credit_consumption_per_task=performance_metrics.credits_consumed,
    )
)

# KARMA score is stored in rating for reference
mission_rating.karma_score = karma_score.score
```

## Performance Considerations

### Redis Storage

- **Agent Ratings**: `brain:mission_rating:agent:{agent_id}`
- **Mission Ratings**: `brain:mission_rating:mission:{mission_id}`
- **Audit Logs**: `brain:mission_rating:audit:{mission_id}` (List)

### Caching Strategy

- Agent ratings cached in Redis
- Frequently accessed ratings kept in memory
- Audit logs append-only (optimized for writes)

### Scaling

- Stateless service (horizontal scaling)
- Redis for shared state
- Async I/O for concurrency

## Future Enhancements

### Phase 2 (Planned)
- [ ] Machine learning-based skill recommendations
- [ ] Predictive mission duration estimation
- [ ] Anomaly detection for rating outliers
- [ ] Advanced trend analysis
- [ ] Skill decay over time
- [ ] Peer review integration

### Phase 3 (Planned)
- [ ] Multi-agent collaborative ratings
- [ ] Skill certification system
- [ ] Training recommendation engine
- [ ] Performance benchmarking
- [ ] A/B testing for rating algorithms

## Troubleshooting

### Common Issues

**Issue**: Rating created but agent rating not updated
**Solution**: Check Redis connectivity, verify agent_id exists

**Issue**: Skill matching returns no agents
**Solution**: Check required skill names (case-sensitive), verify agents have skills registered

**Issue**: KARMA integration failing
**Solution**: Verify KARMA service is running, check logs for integration errors

### Debug Mode

Enable debug logging:
```python
from loguru import logger

logger.add("mission_rating_debug.log", level="DEBUG")
```

## Contributing

When modifying the rating system:

1. Update algorithm version if formula changes
2. Add tests for new features
3. Document breaking changes
4. Update this README
5. Run full test suite: `pytest backend/tests/test_mission_rating.py -v`

## License

Part of BRAiN framework - see main LICENSE file.

---

**Last Updated**: 2024-12-21
**Maintainer**: BRAiN Core Team
