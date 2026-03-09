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
from app.modules.discovery_layer.router import router as discovery_router


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


def test_discovery_analyze_and_queue_review(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(discovery_router)

    async def _db_override():
        yield None

    principal = build_principal("admin", "SYSTEM_ADMIN")
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    client = TestClient(app)

    route_module = __import__("app.modules.discovery_layer.router", fromlist=["router"])
    run_id = uuid4()
    proposal_id = uuid4()
    now = datetime.now(timezone.utc)
    skill_gap = SimpleNamespace(
        id=uuid4(),
        tenant_id="tenant-a",
        skill_run_id=run_id,
        pattern_id=uuid4(),
        gap_type="skill",
        summary="gap",
        severity="medium",
        confidence=0.7,
        evidence={},
        created_at=now,
    )
    capability_gap = SimpleNamespace(
        id=uuid4(),
        tenant_id="tenant-a",
        skill_run_id=run_id,
        pattern_id=skill_gap.pattern_id,
        capability_key="builder.webgenesis.generate",
        summary="cap gap",
        severity="medium",
        confidence=0.6,
        evidence={},
        created_at=now,
    )
    proposal = SimpleNamespace(
        id=proposal_id,
        tenant_id="tenant-a",
        skill_run_id=run_id,
        pattern_id=skill_gap.pattern_id,
        skill_gap_id=skill_gap.id,
        capability_gap_id=capability_gap.id,
        target_skill_key="builder.webgenesis.generate",
        status="draft",
        proposal_summary="proposal",
        proposal_evidence={},
        dedup_key=f"{run_id}:builder.webgenesis.generate",
        evidence_score=0.82,
        priority_score=0.8,
        created_at=now,
        updated_at=now,
    )

    class FakeService:
        async def analyze_skill_run(self, db, skill_run_id, principal):
            assert skill_run_id == run_id
            return (
                skill_gap,
                capability_gap,
                proposal,
                {
                    "evidence_sources": ["consolidation", "knowledge", "observer"],
                    "observer_signal_count": 3,
                    "knowledge_item_count": 2,
                    "thresholds": {
                        "min_pattern_confidence": 0.55,
                        "min_recurrence_support": 0.45,
                        "min_observer_signals": 1,
                        "min_knowledge_items": 1,
                    },
                    "evidence_score": 0.82,
                },
            )

        async def get_proposal_by_id(self, db, proposal_id_param, tenant_id):
            assert proposal_id_param == proposal_id
            assert tenant_id == "tenant-a"
            return proposal

        async def queue_for_review(self, db, proposal_id_param, principal):
            assert proposal_id_param == proposal_id
            queued = SimpleNamespace(**{**proposal.__dict__, "status": "review_queued"})
            return queued, str(uuid4())

    monkeypatch.setattr(
        route_module, "get_discovery_layer_service", lambda: FakeService()
    )

    analyze_response = client.post(f"/api/discovery/skill-runs/{run_id}/analyze")
    assert analyze_response.status_code == 201
    assert analyze_response.json()["proposal"]["id"] == str(proposal_id)
    assert analyze_response.json()["evidence"]["observer_signal_count"] == 3

    get_response = client.get(f"/api/discovery/proposals/{proposal_id}")
    assert get_response.status_code == 200

    queue_response = client.post(f"/api/discovery/proposals/{proposal_id}/queue-review")
    assert queue_response.status_code == 200
    assert queue_response.json()["proposal"]["status"] == "review_queued"


def test_discovery_write_blocked_when_retired(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(discovery_router)
    fake_db = object()

    async def _db_override():
        yield fake_db

    principal = build_principal("admin", "SYSTEM_ADMIN")
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    client = TestClient(app)

    route_module = __import__("app.modules.discovery_layer.router", fromlist=["router"])

    class FakeLifecycleService:
        async def get_module(self, db, module_id):
            assert db is fake_db
            assert module_id == "discovery_layer"
            return SimpleNamespace(lifecycle_status="retired")

    monkeypatch.setattr(
        route_module, "get_module_lifecycle_service", lambda: FakeLifecycleService()
    )

    response = client.post(f"/api/discovery/skill-runs/{uuid4()}/analyze")
    assert response.status_code == 409


def test_discovery_queue_review_blocked_when_evolution_retired(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(discovery_router)
    fake_db = object()

    async def _db_override():
        yield fake_db

    principal = build_principal("admin", "SYSTEM_ADMIN")
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    client = TestClient(app)

    route_module = __import__("app.modules.discovery_layer.router", fromlist=["router"])

    class FakeLifecycleService:
        async def get_module(self, db, module_id):
            assert db is fake_db
            if module_id == "discovery_layer":
                return SimpleNamespace(lifecycle_status="stable")
            if module_id == "evolution_control":
                return SimpleNamespace(lifecycle_status="retired")
            return None

    monkeypatch.setattr(
        route_module, "get_module_lifecycle_service", lambda: FakeLifecycleService()
    )

    response = client.post(f"/api/discovery/proposals/{uuid4()}/queue-review")
    assert response.status_code == 409


def test_discovery_requires_tenant_context() -> None:
    app = FastAPI()
    app.include_router(discovery_router)

    async def _db_override():
        yield None

    principal = build_principal("admin", "SYSTEM_ADMIN", tenant_id=None)
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    client = TestClient(app)

    response = client.post(f"/api/discovery/skill-runs/{uuid4()}/analyze")
    assert response.status_code == 403


def test_discovery_queue_review_returns_conflict_for_non_reviewable(
    monkeypatch,
) -> None:
    app = FastAPI()
    app.include_router(discovery_router)

    async def _db_override():
        yield None

    principal = build_principal("admin", "SYSTEM_ADMIN")
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    client = TestClient(app)

    route_module = __import__("app.modules.discovery_layer.router", fromlist=["router"])

    class FakeService:
        async def queue_for_review(self, db, proposal_id, principal):
            raise ValueError("Evolution proposal is not reviewable")

    monkeypatch.setattr(
        route_module, "get_discovery_layer_service", lambda: FakeService()
    )

    response = client.post(f"/api/discovery/proposals/{uuid4()}/queue-review")
    assert response.status_code == 409


def test_discovery_list_proposals(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(discovery_router)

    async def _db_override():
        yield None

    principal = build_principal("admin", "SYSTEM_ADMIN")
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    client = TestClient(app)

    route_module = __import__("app.modules.discovery_layer.router", fromlist=["router"])
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
        evidence_score=0.77,
        priority_score=0.8,
        created_at=now,
        updated_at=now,
    )

    class FakeService:
        async def list_proposals(self, db, tenant_id, *, status_filter=None, limit=50):
            assert tenant_id == "tenant-a"
            assert status_filter == "draft"
            assert limit == 20
            return [proposal]

    monkeypatch.setattr(
        route_module, "get_discovery_layer_service", lambda: FakeService()
    )

    response = client.get("/api/discovery/proposals?status_filter=draft&limit=20")
    assert response.status_code == 200
    assert len(response.json()["proposals"]) == 1
    assert response.json()["proposals"][0]["priority_score"] == 0.8
