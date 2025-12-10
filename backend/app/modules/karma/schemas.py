from datetime import datetime
from pydantic import BaseModel


class KarmaMetrics(BaseModel):
    success_rate: float
    avg_latency_ms: float
    policy_violations: int
    user_rating_avg: float
    credit_consumption_per_task: float


class KarmaScore(BaseModel):
    agent_id: str
    score: float
    computed_at: datetime
    details: KarmaMetrics