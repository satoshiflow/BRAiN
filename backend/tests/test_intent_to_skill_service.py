from __future__ import annotations

from types import SimpleNamespace

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

    monkeypatch.setattr(module, "get_skill_registry_service", lambda: FakeRegistryService())
    monkeypatch.setattr(module, "get_skill_engine_service", lambda: FakeSkillEngine())

    response = await service.execute_intent(
        db=None,
        payload=IntentExecuteRequest(intent_text="Search knowledge about outage incidents"),
        principal=_principal(),
    )

    assert response.resolution_type.value == "matched_skill"
    assert response.matched_skill_key == "knowledge.search"
    assert response.confidence >= 0.2


@pytest.mark.asyncio
async def test_execute_intent_returns_draft_for_low_confidence(monkeypatch) -> None:
    service = IntentToSkillService()
    module = __import__("app.modules.intent_to_skill.service", fromlist=["service"])

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

    monkeypatch.setattr(module, "get_skill_registry_service", lambda: FakeRegistryService())
    monkeypatch.setattr(module, "get_skill_engine_service", lambda: FakeSkillEngine())

    response = await service.execute_intent(
        db=None,
        payload=IntentExecuteRequest(intent_text="Build advanced robotic warehouse optimizer"),
        principal=_principal(),
    )

    assert response.resolution_type.value == "draft_required"
    assert response.draft_suggestion is not None
