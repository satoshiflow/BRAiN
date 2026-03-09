from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth_deps import Principal, PrincipalType, require_auth
from app.core.database import get_db
from app.modules.learning.router import router as learning_router
from app.modules.learning.schemas import MetricType
from app.modules.memory.router import router as memory_router


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


def test_memory_ingest_skill_run_route(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(memory_router)

    async def _db_override():
        yield None

    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: build_principal("operator", "admin")
    client = TestClient(app)

    router_module = __import__("app.modules.memory.router", fromlist=["router"])
    run_id = uuid4()

    class FakeSkillEngineService:
        async def get_run(self, db, skill_run_id, tenant_id):
            return SimpleNamespace(
                id=run_id,
                skill_key="builder.course_factory.generate",
                skill_version=1,
                state="succeeded",
                requested_by="agent-1",
                mission_id="mission-1",
                evaluation_summary={"score": 0.92},
                failure_code=None,
                correlation_id="corr-1",
            )

    class FakeMemoryService:
        async def store_memory(self, request):
            assert request.skill_run_id == str(run_id)
            return {
                "memory_id": "mem-1",
                "layer": "episodic",
                "memory_type": "mission_outcome",
                "content": request.content,
                "agent_id": request.agent_id,
                "session_id": None,
                "mission_id": request.mission_id,
                "skill_run_id": request.skill_run_id,
                "importance": request.importance,
                "tags": request.tags,
                "metadata": request.model_dump().get("metadata", {}),
                "created_at": 0.0,
                "last_accessed": 0.0,
                "access_count": 0,
                "compressed": False,
                "source_memory_ids": [],
            }

    monkeypatch.setattr(router_module, "get_skill_engine_service", lambda: FakeSkillEngineService())
    monkeypatch.setattr(router_module, "get_memory_service", lambda: FakeMemoryService())

    response = client.post(f"/api/memory/skill-runs/{run_id}/ingest")
    assert response.status_code == 201
    assert response.json()["memory"]["skill_run_id"] == str(run_id)


def test_learning_ingest_skill_run_route(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(learning_router)

    async def _db_override():
        yield None

    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: build_principal("operator", "admin")
    client = TestClient(app)

    router_module = __import__("app.modules.learning.router", fromlist=["router"])
    run_id = uuid4()

    class FakeSkillEngineService:
        async def get_run(self, db, skill_run_id, tenant_id):
            return SimpleNamespace(
                id=run_id,
                requested_by="agent-1",
                state="succeeded",
                skill_key="builder.webgenesis.deploy",
                correlation_id="corr-99",
                cost_actual=12.5,
            )

    class FakeLearningService:
        async def record_metric(self, db, entry):
            return entry

    monkeypatch.setattr(router_module, "get_skill_engine_service", lambda: FakeSkillEngineService())
    monkeypatch.setattr(router_module, "get_learning_service", lambda: FakeLearningService())

    response = client.post(f"/api/learning/metrics/skill-runs/{run_id}/ingest")
    assert response.status_code == 201
    body = response.json()
    assert body["skill_run_id"] == str(run_id)
    assert {metric["metric_type"] for metric in body["metrics"]} == {
        MetricType.SUCCESS_RATE.value,
        MetricType.COST.value,
    }


def test_memory_ingest_blocked_when_module_retired(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(memory_router)

    fake_db = object()

    async def _db_override():
        yield fake_db

    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: build_principal("operator", "admin")
    client = TestClient(app)

    router_module = __import__("app.modules.memory.router", fromlist=["router"])

    class FakeLifecycleService:
        async def get_module(self, db, module_id):
            assert db is fake_db
            assert module_id == "memory"
            return SimpleNamespace(lifecycle_status="retired")

    monkeypatch.setattr(router_module, "get_module_lifecycle_service", lambda: FakeLifecycleService())

    response = client.post(f"/api/memory/skill-runs/{uuid4()}/ingest")
    assert response.status_code == 409


def test_learning_ingest_blocked_when_module_deprecated(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(learning_router)

    fake_db = object()

    async def _db_override():
        yield fake_db

    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: build_principal("operator", "admin")
    client = TestClient(app)

    router_module = __import__("app.modules.learning.router", fromlist=["router"])

    class FakeLifecycleService:
        async def get_module(self, db, module_id):
            assert db is fake_db
            assert module_id == "learning"
            return SimpleNamespace(lifecycle_status="deprecated")

    monkeypatch.setattr(router_module, "get_module_lifecycle_service", lambda: FakeLifecycleService())

    response = client.post(f"/api/learning/metrics/skill-runs/{uuid4()}/ingest")
    assert response.status_code == 409
