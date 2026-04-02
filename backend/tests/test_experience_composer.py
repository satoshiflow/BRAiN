from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth_deps import Principal, PrincipalType, require_auth
from app.core.database import get_db
from app.modules.experience_composer.router import router as experience_composer_router
from app.modules.experience_composer.schemas import (
    ExperienceContext,
    ExperienceRenderRequest,
    ExperienceSubject,
    ExperienceType,
    IntentType,
)
from app.modules.experience_composer.service import ExperienceComposerService


def build_principal() -> Principal:
    return Principal(
        principal_id="operator-1",
        principal_type=PrincipalType.HUMAN,
        email="operator@example.com",
        name="Operator",
        roles=["operator", "admin"],
        scopes=["read", "write"],
        tenant_id="tenant-a",
    )


@pytest.mark.asyncio
async def test_service_renders_landingpage_payload_from_knowledge_items() -> None:
    item_id = uuid4()

    class FakeKnowledgeService:
        async def get_item(self, db, principal, item_uuid):  # noqa: ANN001
            _ = (db, principal, item_uuid)
            return None

        async def semantic_search(self, db, principal, query, limit=4):  # noqa: ANN001
            _ = (db, principal, limit)
            assert query == "comfrey joint support"
            return [
                {
                    "id": item_id,
                    "title": "Beinwell",
                    "content": "Beinwell ist traditionell fuer aeussere Anwendungen rund um Gelenke und Belastung bekannt.",
                    "type": "plant_profile",
                    "tags": ["phyto", "joint"],
                }
            ]

    service = ExperienceComposerService(knowledge_service=FakeKnowledgeService())
    request = ExperienceRenderRequest(
        intent=IntentType.EXPLAIN,
        experience_type=ExperienceType.LANDINGPAGE,
        subject=ExperienceSubject(type="topic", query="comfrey joint support"),
        context=ExperienceContext(device="web", locale="de-DE", user_skill="beginner"),
    )

    output = await service.render(db=object(), principal=build_principal(), payload=request)

    assert output.type.value == "ui"
    assert output.target.value == "web"
    assert output.payload["experience_type"] == "landingpage"
    assert output.payload["data"]["summary"]["title"] == "Beinwell"
    assert output.payload["sources"][0]["id"] == str(item_id)
    assert any(section["component"] == "hero_card" for section in output.payload["sections"])
    assert output.payload["safety"]["warnings"]


@pytest.mark.asyncio
async def test_service_renders_chat_answer_when_requested() -> None:
    class FakeKnowledgeService:
        async def get_item(self, db, principal, item_uuid):  # noqa: ANN001
            _ = (db, principal, item_uuid)
            return None

        async def semantic_search(self, db, principal, query, limit=4):  # noqa: ANN001
            _ = (db, principal, query, limit)
            return []

    service = ExperienceComposerService(knowledge_service=FakeKnowledgeService())
    request = ExperienceRenderRequest(
        intent=IntentType.SUMMARIZE,
        experience_type=ExperienceType.CHAT_ANSWER,
        subject=ExperienceSubject(type="topic", query="Kurzinfo zu Phyto Uckermark"),
    )

    output = await service.render(db=object(), principal=build_principal(), payload=request)

    assert output.type.value == "answer"
    assert output.target.value == "chat"
    assert "Phyto Uckermark" in output.payload["text"]


def test_render_route_returns_output_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    app = FastAPI()
    app.include_router(experience_composer_router)

    async def _db_override():
        yield object()

    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = build_principal
    client = TestClient(app)

    route_module = __import__("app.modules.experience_composer.router", fromlist=["router"])

    class FakeService:
        async def render(self, db, principal, payload):  # noqa: ANN001
            _ = (db, principal)
            assert payload.experience_type.value == "landingpage"
            return {
                "schema_version": "1.0",
                "type": "ui",
                "target": "web",
                "payload": {
                    "schema_version": "1.0",
                    "experience_type": "landingpage",
                    "variant": "landingpage",
                    "context": {},
                    "data": {},
                    "sources": [],
                    "sections": [],
                    "safety": {"mode": "strict", "warnings": []},
                    "cache": {"ttl_seconds": 1800, "persist": False},
                },
                "metadata": {},
            }

    monkeypatch.setattr(route_module, "get_experience_composer_service", lambda: FakeService())

    response = client.post(
        "/api/experiences/render",
        json={
            "intent": "explain",
            "experience_type": "landingpage",
            "subject": {"type": "topic", "query": "Realtime web experiences"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["output"]["type"] == "ui"
    assert body["output"]["target"] == "web"
