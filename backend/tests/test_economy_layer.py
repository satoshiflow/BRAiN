from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth_deps import (
    Principal,
    PrincipalType,
    get_current_principal,
    require_auth,
)
from app.core.database import get_db
from app.modules.economy_layer.router import router as economy_router


def build_principal(*roles: str, tenant_id: str | None = "tenant-a") -> Principal:
    return Principal(
        principal_id="admin-1",
        principal_type=PrincipalType.HUMAN,
        email="admin@example.com",
        name="Admin",
        roles=list(roles),
        scopes=["read", "write"],
        tenant_id=tenant_id,
    )


def test_economy_analyze_get_queue(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(economy_router)

    async def _db_override():
        yield None

    principal = build_principal("admin", "SYSTEM_ADMIN")
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    client = TestClient(app)

    route_module = __import__("app.modules.economy_layer.router", fromlist=["router"])
    now = datetime.now(timezone.utc)
    proposal = SimpleNamespace(
        id=uuid4(),
        tenant_id="tenant-a",
        skill_run_id=uuid4(),
        pattern_id=uuid4(),
        skill_gap_id=uuid4(),
        capability_gap_id=uuid4(),
        target_skill_key="builder.webgenesis.generate",
        status="draft",
        proposal_summary="proposal",
        proposal_evidence={},
        dedup_key="run-a:builder.webgenesis.generate",
        evidence_score=0.75,
        priority_score=0.82,
        created_at=now,
        updated_at=now,
    )
    assessment = SimpleNamespace(
        id=uuid4(),
        tenant_id="tenant-a",
        discovery_proposal_id=proposal.id,
        skill_run_id=proposal.skill_run_id,
        status="draft",
        confidence_score=0.75,
        frequency_score=0.5,
        impact_score=0.78,
        cost_score=0.4,
        weighted_score=0.7,
        score_breakdown={"dimensions": {}},
        created_at=now,
        updated_at=now,
    )

    class FakeService:
        async def analyze_proposal(self, db, proposal_id, principal):
            assert proposal_id == proposal.id
            return assessment, proposal

        async def get_assessment_by_id(self, db, assessment_id, tenant_id):
            assert assessment_id == assessment.id
            assert tenant_id == "tenant-a"
            return assessment

        async def queue_for_review(self, db, assessment_id, principal):
            assert assessment_id == assessment.id
            return SimpleNamespace(**{**assessment.__dict__, "status": "review_queued"})

    monkeypatch.setattr(
        route_module, "get_economy_layer_service", lambda: FakeService()
    )

    analyze_response = client.post(f"/api/economy/proposals/{proposal.id}/analyze")
    assert analyze_response.status_code == 201
    assert analyze_response.json()["assessment"]["id"] == str(assessment.id)

    get_response = client.get(f"/api/economy/assessments/{assessment.id}")
    assert get_response.status_code == 200

    queue_response = client.post(
        f"/api/economy/assessments/{assessment.id}/queue-review"
    )
    assert queue_response.status_code == 200
    assert queue_response.json()["assessment"]["status"] == "review_queued"


def test_economy_requires_tenant_context() -> None:
    app = FastAPI()
    app.include_router(economy_router)

    async def _db_override():
        yield None

    principal = build_principal("admin", "SYSTEM_ADMIN", tenant_id=None)
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    client = TestClient(app)

    response = client.get(f"/api/economy/assessments/{uuid4()}")
    assert response.status_code == 403
