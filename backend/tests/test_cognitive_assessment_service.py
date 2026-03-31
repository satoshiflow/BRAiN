from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.auth_deps import Principal, PrincipalType
from app.modules.cognitive_assessment.schemas import CognitiveAssessmentRequest
from app.modules.cognitive_assessment.service import CognitiveAssessmentService


def _principal() -> Principal:
    return Principal(
        principal_id="cognitive-admin",
        principal_type=PrincipalType.HUMAN,
        email="admin@example.com",
        name="Admin",
        roles=["admin"],
        scopes=["read", "write"],
        tenant_id="tenant-a",
    )


class _FakeResult:
    def __init__(self, row):
        self._row = row

    def mappings(self):
        return self

    def one(self):
        return self._row


class _FakeDb:
    def __init__(self):
        self.last_insert = None

    async def execute(self, stmt, params=None):
        _ = stmt
        if params and "normalized_intent" in params:
            self.last_insert = params
            return _FakeResult(
                {
                    "id": uuid4(),
                    "tenant_id": params.get("tenant_id"),
                    "mission_id": params.get("mission_id"),
                    "created_at": datetime.now(timezone.utc),
                }
            )
        return _FakeResult(
            {
                "id": uuid4(),
                "assessment_id": params.get("assessment_id"),
                "skill_run_id": params.get("skill_run_id"),
                "evaluation_result_id": params.get("evaluation_result_id"),
                "experience_record_id": params.get("experience_record_id"),
                "outcome_state": params.get("outcome_state"),
                "overall_score": params.get("overall_score"),
                "success": params.get("success"),
                "metadata": params.get("metadata") and {},
                "created_at": datetime.now(timezone.utc),
            }
        )

    async def commit(self):
        return None


@pytest.mark.asyncio
async def test_assess_builds_perception_and_candidates(monkeypatch) -> None:
    service = CognitiveAssessmentService()
    module = __import__("app.modules.cognitive_assessment.service", fromlist=["service"])

    async def _memory(principal, normalized_intent, mission_id):
        _ = (principal, normalized_intent, mission_id)
        from app.modules.cognitive_assessment.schemas import AssociationCase

        return [
            AssociationCase(
                source_type="memory",
                source_id="mem-1",
                title="incident",
                score=0.8,
                summary="similar outage incident",
                metadata={},
            )
        ]

    async def _knowledge(db, principal, normalized_intent):
        _ = (db, principal, normalized_intent)
        return []

    class FakeRegistryService:
        async def list_definitions(self, db, tenant_id, include_system, status, sort_by):
            _ = (db, tenant_id, include_system, status, sort_by)
            return [
                SimpleNamespace(
                    skill_key="knowledge.search",
                    version=1,
                    tenant_id=None,
                    purpose="Search outage incident knowledge",
                    description="incident search",
                    required_capabilities=[{"capability_key": "knowledge.query"}],
                    optional_capabilities=[],
                    risk_tier="low",
                    value_score=0.6,
                )
            ]

    monkeypatch.setattr(service, "_associate_memory", _memory)
    monkeypatch.setattr(service, "_associate_knowledge", _knowledge)
    monkeypatch.setattr(module, "get_skill_registry_service", lambda: FakeRegistryService())

    response = await service.assess(
        _FakeDb(),
        CognitiveAssessmentRequest(intent_text="Search outage incidents in knowledge"),
        _principal(),
    )

    assert response.perception.intent_modes[0] == "lookup"
    assert response.association.total_cases == 1
    assert response.recommended_skill_candidates[0].skill_key == "knowledge.search"
    assert response.evaluation.confidence > 0


@pytest.mark.asyncio
async def test_write_learning_feedback_returns_record() -> None:
    service = CognitiveAssessmentService()
    db = _FakeDb()

    response = await service.write_learning_feedback(
        db,
        assessment_id=uuid4(),
        skill_run_id=uuid4(),
        outcome_state="succeeded",
        overall_score=0.92,
        success=True,
        metadata={"x": 1},
    )

    assert response.success is True
    assert response.outcome_state == "succeeded"
