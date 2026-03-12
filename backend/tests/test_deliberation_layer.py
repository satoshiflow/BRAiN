from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth_deps import Principal, PrincipalType, get_current_principal, require_auth
from app.core.database import get_db
from app.modules.deliberation_layer.router import router as deliberation_router


def build_principal(*roles: str, tenant_id: str | None = "tenant-a") -> Principal:
    return Principal(
        principal_id="operator-1",
        principal_type=PrincipalType.HUMAN,
        email="operator@example.com",
        name="Operator",
        roles=list(roles),
        scopes=["read", "write"],
        tenant_id=tenant_id,
    )


def test_deliberation_create_and_read(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(deliberation_router)

    async def _db_override():
        yield None

    principal = build_principal("operator", "admin")
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    client = TestClient(app)

    route_module = __import__("app.modules.deliberation_layer.router", fromlist=["router"])
    mission_id = "mission-1"
    now = datetime.now(timezone.utc)
    summary = SimpleNamespace(
        id=uuid4(),
        tenant_id="tenant-a",
        mission_id=mission_id,
        alternatives=["path-a", "path-b"],
        rationale_summary="Short rationale summary",
        uncertainty=0.3,
        open_tensions=["cost-vs-speed"],
        evidence={"source": "observer"},
        created_by="operator-1",
        created_at=now,
    )
    tension = SimpleNamespace(
        id=uuid4(),
        tenant_id="tenant-a",
        mission_id=mission_id,
        hypothesis="Hypothesis",
        perspective="Perspective",
        tension="Main tension",
        status="open",
        evidence={"source": "insight"},
        created_by="operator-1",
        created_at=now,
        updated_at=now,
    )

    class FakeService:
        async def create_summary(self, db, mission_id_param, payload, principal):
            assert mission_id_param == mission_id
            return summary

        async def get_latest_summary(self, db, mission_id_param, tenant_id):
            assert mission_id_param == mission_id
            assert tenant_id == "tenant-a"
            return summary

        async def create_tension(self, db, mission_id_param, payload, principal):
            assert mission_id_param == mission_id
            return tension

        async def list_tensions(self, db, mission_id_param, tenant_id):
            assert mission_id_param == mission_id
            assert tenant_id == "tenant-a"
            return [tension]

    monkeypatch.setattr(route_module, "get_deliberation_layer_service", lambda: FakeService())

    create_summary_response = client.post(
        f"/api/deliberation/missions/{mission_id}/summaries",
        json={
            "alternatives": ["path-a", "path-b"],
            "rationale_summary": "Short rationale summary",
            "uncertainty": 0.3,
            "open_tensions": ["cost-vs-speed"],
            "evidence": {"source": "observer"},
        },
    )
    assert create_summary_response.status_code == 201

    latest_summary_response = client.get(f"/api/deliberation/missions/{mission_id}/summaries/latest")
    assert latest_summary_response.status_code == 200

    create_tension_response = client.post(
        f"/api/deliberation/missions/{mission_id}/tensions",
        json={
            "hypothesis": "Hypothesis",
            "perspective": "Perspective",
            "tension": "Main tension",
            "evidence": {"source": "insight"},
        },
    )
    assert create_tension_response.status_code == 201

    list_tensions_response = client.get(f"/api/deliberation/missions/{mission_id}/tensions")
    assert list_tensions_response.status_code == 200
    assert list_tensions_response.json()["total"] == 1


def test_deliberation_write_blocked_when_retired(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(deliberation_router)
    fake_db = object()

    async def _db_override():
        yield fake_db

    principal = build_principal("operator", "admin")
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    client = TestClient(app)

    route_module = __import__("app.modules.deliberation_layer.router", fromlist=["router"])

    class FakeLifecycleService:
        async def get_module(self, db, module_id):
            assert db is fake_db
            assert module_id == "deliberation_layer"
            return SimpleNamespace(lifecycle_status="retired")

    monkeypatch.setattr(route_module, "get_module_lifecycle_service", lambda: FakeLifecycleService())

    response = client.post(
        "/api/deliberation/missions/m-1/summaries",
        json={"rationale_summary": "x", "uncertainty": 0.1},
    )
    assert response.status_code == 409


def test_deliberation_payload_forbids_extra_fields() -> None:
    app = FastAPI()
    app.include_router(deliberation_router)

    async def _db_override():
        yield None

    principal = build_principal("operator", "admin")
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    client = TestClient(app)

    response = client.post(
        "/api/deliberation/missions/m-1/summaries",
        json={
            "rationale_summary": "x",
            "uncertainty": 0.1,
            "raw_chain_of_thought": "forbidden",
        },
    )
    assert response.status_code == 422


def test_deliberation_payload_rejects_nested_reasoning_keys() -> None:
    app = FastAPI()
    app.include_router(deliberation_router)

    async def _db_override():
        yield None

    principal = build_principal("operator", "admin")
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    client = TestClient(app)

    response = client.post(
        "/api/deliberation/missions/m-1/summaries",
        json={
            "rationale_summary": "x",
            "uncertainty": 0.1,
            "evidence": {"safe": True, "nested": {"raw_chain_of_thought": "forbidden"}},
        },
    )
    assert response.status_code == 422


def test_deliberation_payload_rejects_unbounded_evidence_map() -> None:
    app = FastAPI()
    app.include_router(deliberation_router)

    async def _db_override():
        yield None

    principal = build_principal("operator", "admin")
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    client = TestClient(app)

    evidence = {f"k{i}": i for i in range(25)}
    response = client.post(
        "/api/deliberation/missions/m-1/summaries",
        json={
            "rationale_summary": "x",
            "uncertainty": 0.1,
            "evidence": evidence,
        },
    )
    assert response.status_code == 422
