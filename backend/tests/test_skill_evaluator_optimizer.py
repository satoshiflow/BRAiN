from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import importlib
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.auth_deps import Principal, PrincipalType, require_auth
from app.core.database import get_db
from app.modules.skill_evaluator.router import router as skill_evaluator_router
from app.modules.skill_evaluator.service import SkillEvaluatorService
from app.modules.skill_optimizer.router import router as skill_optimizer_router
from app.modules.skill_optimizer.schemas import OptimizerRecommendationStatus
from app.modules.skill_optimizer.service import SkillOptimizerService


def build_principal() -> Principal:
    return Principal(
        principal_id="operator-123",
        principal_type=PrincipalType.HUMAN,
        email="operator@example.com",
        name="Operator",
        roles=["operator", "admin"],
        scopes=["write"],
        tenant_id="tenant-a",
    )


@contextmanager
def override_auth_principal(client: TestClient, principal: Principal):
    client.app.dependency_overrides[require_auth] = lambda: principal
    try:
        yield
    finally:
        client.app.dependency_overrides.pop(require_auth, None)


@contextmanager
def override_auth_unauthorized(client: TestClient):
    async def _unauthorized():
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})

    client.app.dependency_overrides[require_auth] = _unauthorized
    try:
        yield
    finally:
        client.app.dependency_overrides.pop(require_auth, None)


class FakeRun:
    def __init__(self, failed: bool = False) -> None:
        self.id = uuid4()
        self.tenant_id = "tenant-a"
        self.skill_key = "demo.skill"
        self.skill_version = 2
        self.output_payload = {"_capability_results": [{"capability_key": "text.generate"}]}
        self.failure_code = "CAP-FAIL" if failed else None
        self.state = "failed" if failed else "succeeded"
        self.policy_decision = {"allowed": True}
        self.cost_actual = 2.0 if failed else 1.0
        self.cost_estimate = 1.0
        self.provider_selection_snapshot = {"bindings": [{"provider_binding_id": "binding.text.generate.ollama.v1"}]}
        self.correlation_id = "corr-123"
        self.retry_count = 0


def test_skill_evaluator_builds_failed_summary() -> None:
    service = SkillEvaluatorService()
    payload = service._build_evaluation(FakeRun(failed=True))
    assert payload["overall_score"] == 0.0
    assert payload["passed"] is False
    assert payload["findings"]["issues_detected"] == ["CAP-FAIL"]
    assert payload["error_classification"] == "execution_error"
    assert payload["criteria_snapshot"]["policy_snapshot_hash"]


@pytest.mark.asyncio
async def test_skill_optimizer_generates_failure_recommendation() -> None:
    service = SkillOptimizerService()
    emitted_events: list[str] = []

    class FakeScalarResult:
        def __init__(self, items):
            self._items = items

        def all(self):
            return self._items

    class FakeResult:
        def __init__(self, items):
            self._items = items

        def scalars(self):
            return FakeScalarResult(self._items)

    class FakeDb:
        def __init__(self):
            self.added = []
            self.calls = 0

        async def execute(self, query):
            self.calls += 1
            if self.calls == 1:
                return FakeResult([
                    type("Run", (), {"id": uuid4(), "state": "failed", "cost_actual": 2.0, "cost_estimate": 1.0, "skill_version": 2, "created_at": datetime.now(timezone.utc)})(),
                    type("Run", (), {"id": uuid4(), "state": "succeeded", "cost_actual": 1.5, "cost_estimate": 1.0, "skill_version": 2, "created_at": datetime.now(timezone.utc)})(),
                ])
            return FakeResult([
                type("Evaluation", (), {"id": uuid4(), "overall_score": 0.0, "passed": False, "created_at": datetime.now(timezone.utc)})(),
                type("Evaluation", (), {"id": uuid4(), "overall_score": 1.0, "passed": True, "created_at": datetime.now(timezone.utc)})(),
            ])

        def add(self, item):
            self.added.append(item)

        async def commit(self):
            return None

        async def refresh(self, item):
            return None

    db = FakeDb()
    async def _emit_event(_db, recommendation):  # noqa: ANN001
        emitted_events.append(recommendation.recommendation_type)

    service._emit_recommendation_event = _emit_event  # type: ignore[method-assign]
    recs = await service.generate_for_skill(db, "tenant-a", "demo.skill")
    assert len(recs) >= 1
    assert any(rec.recommendation_type == "review_capability_sequence" for rec in recs)
    assert emitted_events


@pytest.mark.asyncio
async def test_skill_optimizer_emits_event_per_recommendation() -> None:
    service = SkillOptimizerService()
    emitted_events: list[str] = []

    class FakeScalarResult:
        def __init__(self, items):
            self._items = items

        def all(self):
            return self._items

    class FakeResult:
        def __init__(self, items):
            self._items = items

        def scalars(self):
            return FakeScalarResult(self._items)

    class FakeDb:
        def __init__(self):
            self.added = []
            self.calls = 0

        async def execute(self, query):
            self.calls += 1
            if self.calls == 1:
                return FakeResult([
                    type("Run", (), {"id": uuid4(), "state": "failed", "cost_actual": 2.0, "cost_estimate": 1.0, "skill_version": 2, "created_at": datetime.now(timezone.utc)})(),
                    type("Run", (), {"id": uuid4(), "state": "failed", "cost_actual": 3.0, "cost_estimate": 1.0, "skill_version": 2, "created_at": datetime.now(timezone.utc)})(),
                ])
            return FakeResult([
                type("Evaluation", (), {"id": uuid4(), "overall_score": 0.0, "passed": False, "created_at": datetime.now(timezone.utc)})(),
                type("Evaluation", (), {"id": uuid4(), "overall_score": 0.0, "passed": False, "created_at": datetime.now(timezone.utc)})(),
            ])

        def add(self, item):
            self.added.append(item)

        async def commit(self):
            return None

        async def refresh(self, item):
            return None

    async def _emit_event(_db, recommendation):  # noqa: ANN001
        emitted_events.append(recommendation.recommendation_type)

    service._emit_recommendation_event = _emit_event  # type: ignore[method-assign]
    db = FakeDb()
    recs = await service.generate_for_skill(db, "tenant-a", "demo.skill")

    assert recs
    assert len(emitted_events) == len(recs)


@pytest.fixture
def evaluation_optimizer_app() -> FastAPI:
    app = FastAPI()
    app.include_router(skill_evaluator_router)
    app.include_router(skill_optimizer_router)

    async def _db_override():
        yield None

    app.dependency_overrides[get_db] = _db_override
    return app


@pytest.fixture
def evaluation_optimizer_client(evaluation_optimizer_app: FastAPI) -> TestClient:
    return TestClient(evaluation_optimizer_app)


def test_optimizer_routes_require_authentication(evaluation_optimizer_client: TestClient) -> None:
    with override_auth_unauthorized(evaluation_optimizer_client):
        response = evaluation_optimizer_client.get("/api/optimizer/recommendations", params={"skill_key": "demo.skill"})
    assert response.status_code == 401


def test_optimizer_generate_route_uses_service(evaluation_optimizer_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    principal = build_principal()
    router_module = importlib.import_module("app.modules.skill_optimizer.router")

    class FakeService:
        async def generate_for_skill(self, db, tenant_id, skill_key):
            return [
                {
                    "id": uuid4(),
                    "tenant_id": tenant_id,
                    "skill_key": skill_key,
                    "skill_version": 2,
                    "recommendation_type": "review_capability_sequence",
                    "confidence": 0.5,
                    "status": "open",
                    "rationale": "review it",
                    "evidence": {"recent_failures": 1},
                    "source_snapshot": {"run_ids": [], "evaluation_ids": [], "average_score": 0.5},
                    "created_at": datetime.now(timezone.utc),
                    "created_by": "skill_optimizer",
                }
            ]

    monkeypatch.setattr(router_module, "get_skill_optimizer_service", lambda: FakeService())
    with override_auth_principal(evaluation_optimizer_client, principal):
        response = evaluation_optimizer_client.post("/api/optimizer/recommendations", params={"skill_key": "demo.skill"})
    assert response.status_code == 200
    assert response.json()["items"][0]["recommendation_type"] == "review_capability_sequence"


def test_optimizer_status_update_route_uses_service(
    evaluation_optimizer_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    principal = build_principal()
    recommendation_id = uuid4()
    router_module = importlib.import_module("app.modules.skill_optimizer.router")

    class FakeService:
        async def update_status(self, db, recommendation_id, tenant_id, status, actor_id, reason):  # noqa: ANN001
            assert tenant_id == principal.tenant_id
            assert status.value == "accepted"
            return {
                "id": recommendation_id,
                "tenant_id": tenant_id,
                "skill_key": "demo.skill",
                "skill_version": 2,
                "recommendation_type": "review_capability_sequence",
                "confidence": 0.9,
                "status": "accepted",
                "rationale": "ok",
                "evidence": {},
                "source_snapshot": {},
                "created_at": datetime.now(timezone.utc),
                "created_by": actor_id,
            }

    monkeypatch.setattr(router_module, "get_skill_optimizer_service", lambda: FakeService())
    with override_auth_principal(evaluation_optimizer_client, principal):
        response = evaluation_optimizer_client.patch(
            f"/api/optimizer/recommendations/{recommendation_id}/status",
            json={"status": "accepted", "reason": "approved by operator"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"


@pytest.mark.asyncio
async def test_optimizer_status_update_emits_transition_event() -> None:
    service = SkillOptimizerService()
    recommendation_id = uuid4()
    emitted_events: list[tuple[str, str, str]] = []

    class FakeDb:
        def __init__(self) -> None:
            self.recommendation = SimpleNamespace(
                id=recommendation_id,
                tenant_id="tenant-a",
                skill_key="demo.skill",
                skill_version=2,
                recommendation_type="review_capability_sequence",
                confidence=0.8,
                status="open",
                rationale="review",
                evidence={},
                source_snapshot={},
                created_at=datetime.now(timezone.utc),
                created_by="skill_optimizer",
            )

        async def execute(self, query):  # noqa: ANN001
            class _Result:
                def __init__(self, item):
                    self.item = item

                def scalar_one_or_none(self):
                    return self.item

            return _Result(self.recommendation)

        async def commit(self):
            return None

        async def refresh(self, _item):
            return None

    async def _emit_status_transition_event(  # noqa: ANN001
        db,
        recommendation,
        previous_status,
        actor_id,
        reason,
    ):
        emitted_events.append((previous_status, recommendation.status, actor_id))

    service._emit_status_transition_event = _emit_status_transition_event  # type: ignore[method-assign]
    db = FakeDb()

    updated = await service.update_status(
        db,
        recommendation_id=recommendation_id,
        tenant_id="tenant-a",
        status=OptimizerRecommendationStatus.ACCEPTED,
        actor_id="operator-123",
        reason="approved",
    )

    assert updated is not None
    assert updated.status == "accepted"
    assert emitted_events == [("open", "accepted", "operator-123")]


def test_evaluation_get_route_uses_service(evaluation_optimizer_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    principal = build_principal()
    evaluation_id = uuid4()
    run_id = uuid4()
    router_module = importlib.import_module("app.modules.skill_evaluator.router")

    class FakeService:
        async def get_evaluation(self, db, evaluation_id_arg, tenant_id):
            assert evaluation_id_arg == evaluation_id
            return {
                "id": evaluation_id_arg,
                "tenant_id": tenant_id,
                "skill_run_id": run_id,
                "skill_key": "demo.skill",
                "skill_version": 2,
                "evaluator_type": "rule",
                "status": "completed",
                "overall_score": 1.0,
                "dimension_scores": {"success": 1.0},
                "passed": True,
                "criteria_snapshot": {"dimension_keys": ["success"]},
                "findings": {},
                "recommendations": {},
                "metrics_summary": {"success": True},
                "provider_selection_snapshot": {"bindings": []},
                "error_classification": None,
                "policy_compliance": "compliant",
                "policy_violations": [],
                "correlation_id": "corr-1",
                "evaluation_revision": 1,
                "created_at": datetime.now(timezone.utc),
                "completed_at": datetime.now(timezone.utc),
                "created_by": "skill_evaluator",
            }

    monkeypatch.setattr(router_module, "get_skill_evaluator_service", lambda: FakeService())
    with override_auth_principal(evaluation_optimizer_client, principal):
        response = evaluation_optimizer_client.get(f"/api/evaluation-results/{evaluation_id}")
    assert response.status_code == 200
    assert response.json()["skill_key"] == "demo.skill"
