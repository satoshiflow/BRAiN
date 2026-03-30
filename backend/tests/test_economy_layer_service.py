from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.auth_deps import Principal, PrincipalType
from app.modules.economy_layer.service import EconomyLayerService


class FakeDb:
    def __init__(self) -> None:
        self.items = []

    def add(self, item) -> None:
        self.items.append(item)

    async def execute(self, query):
        raise RuntimeError("not used in this test")

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None

    async def refresh(self, item) -> None:
        return None


def _principal() -> Principal:
    return Principal(
        principal_id="admin-1",
        principal_type=PrincipalType.HUMAN,
        email="admin@example.com",
        name="Admin",
        roles=["admin"],
        scopes=["read", "write"],
        tenant_id="tenant-a",
    )


@pytest.mark.asyncio
async def test_analyze_proposal_updates_priority_and_metadata(monkeypatch) -> None:
    service = EconomyLayerService()
    now = datetime.now(timezone.utc)
    proposal = SimpleNamespace(
        id=uuid4(),
        tenant_id="tenant-a",
        skill_run_id=uuid4(),
        pattern_id=uuid4(),
        proposal_evidence={"observer_signal_count": 3, "knowledge_item_count": 2},
        evidence_score=0.8,
        priority_score=0.6,
        updated_at=now,
    )
    evolution_proposal = SimpleNamespace(
        id=uuid4(), proposal_metadata={}, updated_at=now
    )

    module = __import__(
        "app.modules.economy_layer.service", fromlist=["get_discovery_layer_service"]
    )

    class FakeDiscoveryService:
        async def get_proposal_by_id(self, db, proposal_id, tenant_id):
            return proposal

    class FakeEvolutionService:
        async def get_by_pattern_id(self, db, pattern_id, tenant_id):
            return evolution_proposal

    monkeypatch.setattr(
        module, "get_discovery_layer_service", lambda: FakeDiscoveryService()
    )
    monkeypatch.setattr(
        module, "get_evolution_control_service", lambda: FakeEvolutionService()
    )

    async def _no_existing(db, proposal_id, tenant_id):
        return None

    service.get_assessment_by_proposal_id = _no_existing  # type: ignore[method-assign]

    assessment, updated_proposal = await service.analyze_proposal(
        FakeDb(), proposal.id, _principal()
    )

    assert assessment.weighted_score > 0
    assert updated_proposal.priority_score > 0.6
    assert "economy_assessment_id" in updated_proposal.proposal_evidence
    assert (
        evolution_proposal.proposal_metadata.get("economy_weighted_score")
        == assessment.weighted_score
    )


@pytest.mark.asyncio
async def test_queue_for_review_requires_assessment(monkeypatch) -> None:
    service = EconomyLayerService()

    async def _missing(db, assessment_id, tenant_id):
        return None

    service.get_assessment_by_id = _missing  # type: ignore[method-assign]

    with pytest.raises(ValueError, match="Economy assessment not found"):
        await service.queue_for_review(FakeDb(), uuid4(), _principal())


def test_calculate_skill_value_prefers_explicit_score() -> None:
    service = EconomyLayerService()

    value = service.calculate_skill_value(
        risk_tier="high",
        value_score=0.82,
        effort_saved_hours=5.0,
        complexity_level="medium",
        quality_impact=0.2,
    )

    assert value["value_score"] == 0.82
    assert value["source"] == "explicit"
    assert value["breakdown"]["computed_score"] <= 1.0


def test_calculate_skill_value_derives_when_no_explicit_score() -> None:
    service = EconomyLayerService()

    value = service.calculate_skill_value(
        risk_tier="critical",
        value_score=0.0,
        effort_saved_hours=32.0,
        complexity_level="high",
        quality_impact=0.8,
    )

    assert value["source"] == "derived"
    assert value["value_score"] > 0.0
    assert value["breakdown"]["risk_weight"] == 1.1


@pytest.mark.asyncio
async def test_ingest_skill_run_feedback_updates_skill_value(monkeypatch) -> None:
    service = EconomyLayerService()

    definition = SimpleNamespace(
        risk_tier="medium",
        value_score=0.0,
        effort_saved_hours=2.0,
        complexity_level="low",
        quality_impact=0.1,
        updated_at=datetime.now(timezone.utc),
    )
    run = SimpleNamespace(
        id=uuid4(),
        tenant_id="tenant-a",
        skill_key="demo.skill",
        skill_version=2,
        risk_tier="medium",
    )
    evaluation = SimpleNamespace(
        overall_score=0.9,
        metrics_summary={"capability_count": 6, "latency_ms": 2400.0},
    )

    async def _resolve(db, run_arg):
        _ = (db, run_arg)
        return definition

    service._resolve_skill_definition_for_run = _resolve  # type: ignore[method-assign]

    payload = await service.ingest_skill_run_feedback(FakeDb(), run, evaluation)

    assert payload is not None
    assert payload["source"] == "skill_run_feedback"
    assert definition.value_score > 0.0
    assert definition.effort_saved_hours > 2.0
    assert definition.complexity_level in {"high", "critical"}


@pytest.mark.asyncio
async def test_get_marketplace_ranking_orders_by_market_score() -> None:
    service = EconomyLayerService()

    async def _analytics(db, *, tenant_id, window_days, limit):
        _ = (db, tenant_id, window_days, limit)
        return {
            "summary": {
                "total_skills": 2,
                "total_runs": 15,
                "avg_value_score": 0.7,
                "avg_success_rate": 0.75,
                "window_days": 30,
            },
            "items": [
                {
                    "skill_key": "skill.a",
                    "latest_version": 2,
                    "value_score": 0.8,
                    "success_rate": 0.8,
                    "avg_overall_score": 0.7,
                    "total_runs": 10,
                    "succeeded_runs": 8,
                    "failed_runs": 2,
                    "trend_delta": 0.1,
                    "last_run_at": datetime.now(timezone.utc),
                },
                {
                    "skill_key": "skill.b",
                    "latest_version": 1,
                    "value_score": 0.6,
                    "success_rate": 0.7,
                    "avg_overall_score": 0.65,
                    "total_runs": 5,
                    "succeeded_runs": 4,
                    "failed_runs": 1,
                    "trend_delta": -0.05,
                    "last_run_at": datetime.now(timezone.utc),
                },
            ],
        }

    service.get_skill_lifecycle_analytics = _analytics  # type: ignore[method-assign]
    ranking = await service.get_marketplace_ranking(
        FakeDb(),
        tenant_id="tenant-a",
        window_days=30,
        limit=10,
    )

    assert ranking["items"][0]["rank"] == 1
    assert ranking["items"][0]["skill_key"] == "skill.a"
    assert ranking["items"][0]["market_score"] >= ranking["items"][1]["market_score"]
