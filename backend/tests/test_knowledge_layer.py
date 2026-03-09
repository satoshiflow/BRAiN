from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth_deps import Principal, PrincipalType, get_current_principal, require_auth
from app.core.database import get_db
from app.modules.knowledge_layer.router import router as knowledge_layer_router


def build_principal(*roles: str) -> Principal:
    return Principal(
        principal_id="operator-1",
        principal_type=PrincipalType.HUMAN,
        email="operator@example.com",
        name="Operator",
        roles=list(roles),
        scopes=["read", "write"],
        tenant_id="tenant-a",
    )


def test_knowledge_layer_search_and_run_lesson_ingest(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(knowledge_layer_router)

    async def _db_override():
        yield None

    app.dependency_overrides[get_db] = _db_override
    principal = build_principal("operator", "admin")
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    client = TestClient(app)

    router_module = __import__("app.modules.knowledge_layer.router", fromlist=["router"])
    run_id = uuid4()
    item_id = uuid4()
    knowledge_item = SimpleNamespace(
        id=item_id,
        tenant_id="tenant-a",
        type="run_lesson",
        title="Run lesson: builder.webgenesis.generate",
        source="skill_run",
        version=1,
        owner="operator-1",
        module="skill_engine",
        tags=["builder.webgenesis.generate", "succeeded"],
        content="SkillRun lesson",
        provenance_refs=[{"type": "skill_run", "id": str(run_id)}],
        valid_until=None,
        superseded_by_id=None,
        created_at="2026-03-08T00:00:00Z",
    )

    class FakeService:
        async def search(self, db, tenant_id, payload):
            assert tenant_id == "tenant-a"
            assert payload.query == "lesson"
            return [knowledge_item]

        async def ingest_run_lesson(self, db, skill_run_id, principal):
            assert skill_run_id == run_id
            assert principal.tenant_id == "tenant-a"
            return knowledge_item

    monkeypatch.setattr(router_module, "get_knowledge_layer_service", lambda: FakeService())

    response = client.get("/api/knowledge-items", params={"query": "lesson"})
    assert response.status_code == 200
    assert response.json()["total"] == 1

    ingest_response = client.post(f"/api/knowledge-items/run-lessons/{run_id}")
    assert ingest_response.status_code == 201
    assert ingest_response.json()["knowledge_item"]["id"] == str(item_id)


def test_knowledge_layer_ingest_returns_not_found(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(knowledge_layer_router)

    async def _db_override():
        yield None

    app.dependency_overrides[get_db] = _db_override
    principal = build_principal("operator", "admin")
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    client = TestClient(app)

    router_module = __import__("app.modules.knowledge_layer.router", fromlist=["router"])

    class FakeService:
        async def ingest_run_lesson(self, db, skill_run_id, principal):
            raise ValueError("Skill run not found")

    monkeypatch.setattr(router_module, "get_knowledge_layer_service", lambda: FakeService())

    response = client.post(f"/api/knowledge-items/run-lessons/{uuid4()}")
    assert response.status_code == 404


def test_knowledge_layer_write_blocked_when_retired(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(knowledge_layer_router)

    fake_db = object()

    async def _db_override():
        yield fake_db

    principal = build_principal("operator", "admin")
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    client = TestClient(app)

    router_module = __import__("app.modules.knowledge_layer.router", fromlist=["router"])

    class FakeLifecycleService:
        async def get_module(self, db, module_id):
            assert db is fake_db
            assert module_id == "knowledge_layer"
            return SimpleNamespace(lifecycle_status="retired")

    monkeypatch.setattr(router_module, "get_module_lifecycle_service", lambda: FakeLifecycleService())

    response = client.post(
        "/api/knowledge-items",
        json={
            "type": "run_lesson",
            "title": "blocked",
            "source": "skill_run",
            "owner": "operator-1",
            "module": "skill_engine",
            "content": "blocked write",
        },
    )
    assert response.status_code == 409
