from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth_deps import Principal, PrincipalType, get_current_principal, require_auth
from app.core.database import get_db
from app.modules.cognitive_assessment.router import router as cognitive_router


def _principal() -> Principal:
    return Principal(
        principal_id="router-user",
        principal_type=PrincipalType.HUMAN,
        email="router@example.com",
        name="Router User",
        roles=["admin"],
        scopes=["read", "write"],
        tenant_id="tenant-a",
    )


def test_cognitive_assessment_router_assess(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(cognitive_router)

    async def _db_override():
        yield None

    principal = _principal()
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal

    route_module = __import__("app.modules.cognitive_assessment.router", fromlist=["router"])

    class FakeService:
        async def assess(self, db, payload, principal_arg):
            _ = (db, payload, principal_arg)
            return {
                "assessment_id": str(uuid4()),
                "tenant_id": "tenant-a",
                "mission_id": None,
                "perception": {
                    "normalized_intent": "search incidents",
                    "intent_keywords": ["search", "incidents"],
                    "intent_modes": ["lookup"],
                    "risk_hints": [],
                    "impact_hints": [],
                    "novelty_hints": [],
                },
                "association": {"memory_cases": [], "knowledge_cases": [], "total_cases": 0},
                "evaluation": {
                    "confidence": 0.6,
                    "novelty_score": 0.4,
                    "impact_score": 0.5,
                    "governance_hints": [],
                    "risk_hints": [],
                },
                "result": {
                    "result_version": "v1",
                    "confidence": 0.6,
                    "risk": [],
                    "impact": 0.5,
                    "novelty": 0.4,
                    "governance_flags": [],
                    "routing_hint": None,
                },
                "recommended_skill_candidates": [],
                "created_at": datetime.now(timezone.utc),
            }

    monkeypatch.setattr(route_module, "get_cognitive_assessment_service", lambda: FakeService())

    client = TestClient(app)
    response = client.post("/api/cognitive-assessment/assess", json={"intent_text": "search incidents"})

    assert response.status_code == 201
    assert response.json()["evaluation"]["confidence"] == 0.6
