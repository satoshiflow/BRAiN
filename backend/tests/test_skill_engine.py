from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import importlib
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.auth_deps import Principal, PrincipalType, require_auth
from app.core.capabilities.schemas import CapabilityExecutionResponse, CapabilityExecutionSuccess
from app.core.database import get_db
from app.modules.skill_engine.router import router as skill_engine_router
from app.modules.skill_engine.service import SkillEngineService


class FakeSkillDefinition:
    def __init__(self) -> None:
        self.skill_key = "demo.skill"
        self.version = 2
        self.quality_profile = "standard"
        self.risk_tier = "medium"


def build_principal() -> Principal:
    return Principal(
        principal_id="operator-123",
        principal_type=PrincipalType.HUMAN,
        email="operator@example.com",
        name="Operator",
        roles=["operator"],
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


def test_build_plan_snapshot_contains_capability_nodes() -> None:
    snapshot = SkillEngineService.build_plan_snapshot(
        FakeSkillDefinition(),
        [
            {"capability_key": "text.generate", "capability_version": 1, "provider_binding_id": "binding.text.generate.ollama.v1"},
            {"capability_key": "connectors.health.check", "capability_version": 1, "provider_binding_id": "binding.connectors.health.default.v1"},
        ],
    )
    assert snapshot["skill_key"] == "demo.skill"
    assert len(snapshot["nodes"]) == 2
    assert snapshot["nodes"][1]["depends_on"] == [snapshot["nodes"][0]["node_id"]]


def test_summarize_evaluation_marks_failures() -> None:
    success = CapabilityExecutionResponse(
        capability_key="text.generate",
        capability_version=1,
        provider_binding_id="binding.text.generate.ollama.v1",
        result=CapabilityExecutionSuccess(output={"text": "ok"}, latency_ms=1.0),
    )
    failure = CapabilityExecutionResponse.model_validate(
        {
            "capability_key": "connectors.health.check",
            "capability_version": 1,
            "provider_binding_id": "binding.connectors.health.default.v1",
            "result": {
                "status": "failed",
                "error_code": "CAP-FAIL",
                "retryable": False,
                "provider_unavailable": False,
                "provider_content_blocked": False,
                "timeout": False,
                "sanitized_message": "nope",
            },
        }
    )
    summary = SkillEngineService.summarize_evaluation([success, failure])
    assert summary["overall_score"] == 0.0
    assert summary["issues_detected"] == ["CAP-FAIL"]


@pytest.fixture
def skill_engine_app() -> FastAPI:
    app = FastAPI()
    app.include_router(skill_engine_router)

    async def _db_override():
        yield None

    app.dependency_overrides[get_db] = _db_override
    return app


@pytest.fixture
def skill_engine_client(skill_engine_app: FastAPI) -> TestClient:
    return TestClient(skill_engine_app)


def test_skill_engine_routes_require_authentication(skill_engine_client: TestClient) -> None:
    with override_auth_unauthorized(skill_engine_client):
        response = skill_engine_client.get("/api/skill-runs")
    assert response.status_code == 401


def test_skill_engine_execute_route_uses_service(skill_engine_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    principal = build_principal()
    run_id = uuid4()
    skill_engine_router_module = importlib.import_module("app.modules.skill_engine.router")

    class FakeService:
        async def execute_run(self, db, run_id_arg, principal_arg):
            return {
                "skill_run": {
                    "id": run_id_arg,
                    "tenant_id": principal_arg.tenant_id,
                    "skill_key": "demo.skill",
                    "skill_version": 1,
                    "state": "succeeded",
                    "input_payload": {},
                    "plan_snapshot": {},
                    "provider_selection_snapshot": {},
                    "requested_by": principal_arg.principal_id,
                    "requested_by_type": principal_arg.principal_type.value,
                    "trigger_type": "api",
                    "policy_decision": {"allowed": True},
                    "risk_tier": "medium",
                    "correlation_id": "corr-1",
                    "causation_id": None,
                    "idempotency_key": "idem-1",
                    "mission_id": None,
                    "created_at": datetime.now(timezone.utc),
                    "started_at": datetime.now(timezone.utc),
                    "finished_at": datetime.now(timezone.utc),
                    "deadline_at": None,
                    "retry_count": 0,
                    "cost_estimate": 0.0,
                    "cost_actual": 0.0,
                    "output_payload": {"text.generate": {"text": "ok"}},
                    "evaluation_summary": {"overall_score": 1.0},
                    "failure_code": None,
                    "failure_reason_sanitized": None,
                },
                "capability_results": [],
            }

    monkeypatch.setattr(skill_engine_router_module, "get_skill_engine_service", lambda: FakeService())
    with override_auth_principal(skill_engine_client, principal):
        response = skill_engine_client.post(f"/api/skill-runs/{run_id}/execute")
    assert response.status_code == 200
    assert response.json()["skill_run"]["state"] == "succeeded"
