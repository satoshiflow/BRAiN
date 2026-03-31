from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.auth_deps import Principal, PrincipalType
from app.modules.intent_to_skill.schemas import IntentExecuteRequest
from app.modules.intent_to_skill.service import IntentToSkillService


def _principal() -> Principal:
    return Principal(
        principal_id="intent-admin",
        principal_type=PrincipalType.HUMAN,
        email="admin@example.com",
        name="Admin",
        roles=["admin"],
        scopes=["read", "write"],
        tenant_id="tenant-a",
    )


@pytest.mark.asyncio
async def test_execute_intent_matches_existing_skill(monkeypatch) -> None:
    service = IntentToSkillService()
    module = __import__("app.modules.intent_to_skill.service", fromlist=["service"])

    assessment_id = uuid4()
    cognitive_assessment = {
        "assessment_id": assessment_id,
        "tenant_id": "tenant-a",
        "mission_id": None,
        "perception": {
            "normalized_intent": "Search knowledge about outage incidents",
            "intent_keywords": ["search", "knowledge", "outage", "incidents"],
            "intent_modes": ["lookup"],
            "risk_hints": [],
            "impact_hints": ["service_stability"],
            "novelty_hints": [],
        },
        "association": {"memory_cases": [], "knowledge_cases": [], "total_cases": 0},
        "evaluation": {
            "confidence": 0.7,
            "novelty_score": 0.3,
            "impact_score": 0.5,
            "governance_hints": ["novel_request_check"],
            "risk_hints": [],
        },
        "result": {
            "result_version": "v1",
            "confidence": 0.7,
            "risk": [],
            "impact": 0.5,
            "novelty": 0.3,
            "governance_flags": ["novel_request_check"],
            "routing_hint": None,
        },
        "recommended_skill_candidates": [
            {"skill_key": "knowledge.search", "version": 1, "score": 0.74, "reason": "match"}
        ],
        "created_at": "2026-03-31T00:00:00Z",
    }

    definitions = [
        SimpleNamespace(
            skill_key="knowledge.search",
            version=1,
            tenant_id=None,
            purpose="Search knowledge entries by semantic and keyword query",
            required_capabilities=[{"capability_key": "knowledge.query"}],
            optional_capabilities=[],
            risk_tier="low",
            value_score=0.6,
        )
    ]

    class FakeRegistryService:
        async def list_definitions(self, db, tenant_id, include_system, status, sort_by):
            _ = (db, tenant_id, include_system, status, sort_by)
            return definitions

    class FakeSkillEngine:
        async def create_run(self, db, payload, principal):
            _ = (db, payload, principal)
            return SimpleNamespace(id="run-1")

        async def execute_run(self, db, run_id, principal):
            _ = (db, run_id, principal)
            return SimpleNamespace(skill_run=None)

    class FakeCognitiveService:
        async def assess(self, db, payload, principal):
            _ = (db, payload, principal)
            return cognitive_assessment

        async def write_learning_feedback(self, **kwargs):
            _ = kwargs
            return None

    monkeypatch.setattr(module, "get_skill_registry_service", lambda: FakeRegistryService())
    monkeypatch.setattr(module, "get_skill_engine_service", lambda: FakeSkillEngine())
    monkeypatch.setattr(module, "get_cognitive_assessment_service", lambda: FakeCognitiveService())

    response = await service.execute_intent(
        db=None,
        payload=IntentExecuteRequest(intent_text="Search knowledge about outage incidents"),
        principal=_principal(),
    )

    assert response.resolution_type.value == "matched_skill"
    assert response.matched_skill_key == "knowledge.search"
    assert response.confidence >= 0.2
    assert response.cognitive_assessment is not None
    assert response.cognitive_assessment.assessment_id == assessment_id


@pytest.mark.asyncio
async def test_execute_intent_returns_draft_for_low_confidence(monkeypatch) -> None:
    service = IntentToSkillService()
    module = __import__("app.modules.intent_to_skill.service", fromlist=["service"])

    assessment_id = uuid4()
    cognitive_assessment = {
        "assessment_id": assessment_id,
        "tenant_id": "tenant-a",
        "mission_id": None,
        "perception": {
            "normalized_intent": "Build advanced robotic warehouse optimizer",
            "intent_keywords": ["build", "advanced", "robotic", "warehouse", "optimizer"],
            "intent_modes": ["creation"],
            "risk_hints": [],
            "impact_hints": [],
            "novelty_hints": ["potentially_novel_request"],
        },
        "association": {"memory_cases": [], "knowledge_cases": [], "total_cases": 0},
        "evaluation": {
            "confidence": 0.1,
            "novelty_score": 0.9,
            "impact_score": 0.2,
            "governance_hints": ["low_confidence_resolution"],
            "risk_hints": [],
        },
        "result": {
            "result_version": "v1",
            "confidence": 0.1,
            "risk": [],
            "impact": 0.2,
            "novelty": 0.9,
            "governance_flags": ["low_confidence_resolution"],
            "routing_hint": None,
        },
        "recommended_skill_candidates": [],
        "created_at": "2026-03-31T00:00:00Z",
    }

    class FakeRegistryService:
        async def list_definitions(self, db, tenant_id, include_system, status, sort_by):
            _ = (db, tenant_id, include_system, status, sort_by)
            return []

    class FakeSkillEngine:
        async def create_run(self, db, payload, principal):
            _ = (db, payload, principal)
            raise AssertionError("create_run should not be called")

        async def execute_run(self, db, run_id, principal):
            _ = (db, run_id, principal)
            raise AssertionError("execute_run should not be called")

    class FakeCognitiveService:
        async def assess(self, db, payload, principal):
            _ = (db, payload, principal)
            return cognitive_assessment

        async def write_learning_feedback(self, **kwargs):
            _ = kwargs
            raise AssertionError("write_learning_feedback should not be called")

    monkeypatch.setattr(module, "get_skill_registry_service", lambda: FakeRegistryService())
    monkeypatch.setattr(module, "get_skill_engine_service", lambda: FakeSkillEngine())
    monkeypatch.setattr(module, "get_cognitive_assessment_service", lambda: FakeCognitiveService())

    response = await service.execute_intent(
        db=None,
        payload=IntentExecuteRequest(intent_text="Build advanced robotic warehouse optimizer"),
        principal=_principal(),
    )

    assert response.resolution_type.value == "draft_required"
    assert response.draft_suggestion is not None
    assert response.cognitive_assessment is not None
    assert response.cognitive_assessment.assessment_id == assessment_id
